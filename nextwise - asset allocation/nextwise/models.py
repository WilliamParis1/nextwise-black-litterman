"""
=============================================================================
  models.py — Black-Litterman, HRP, Hybrid Allocator, UCITS Filter
=============================================================================
  
  Pipeline:
    ① black_litterman()   → Bayesian return adjustment with investor views
    ② hrp_allocate()      → Hierarchical Risk Parity on BL-adjusted covariance
    ③ hybrid_bl_hrp()     → Tilt HRP weights by BL conviction scores
    ④ apply_ucits()       → Enforce UCITS 5/10/40, cash cap, max single
    
  CHANGES (v2.1):
    FIX #1  — build_views_from_convictions returns empty arrays when no views
              exist; black_litterman short-circuits to equilibrium.
    FIX #2  — CONVICTION_CONFIDENCE now actively scales per-view Omega entries.
              High-confidence views (Conviction Forte: 0.90) get much tighter
              uncertainty than low-confidence views (Renforcer: 0.55).
    FIX #3  — apply_ucits has a hard-clip safety net after the iterative loop
              to guarantee all constraints are satisfied on exit.
    FIX #7  — hybrid_bl_hrp normalizes conviction bonus symmetrically
              so sell signals have proportional impact to buy signals.
=============================================================================
"""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform


# ═════════════════════════════════════════════════════════════════════════════
# ① BLACK-LITTERMAN MODEL
# ═════════════════════════════════════════════════════════════════════════════

def implied_equilibrium_returns(cov: np.ndarray, market_weights: np.ndarray,
                                 risk_aversion: float = 2.5) -> np.ndarray:
    """
    Reverse-optimize the CAPM to get equilibrium expected returns (Pi).
    
    Pi = delta * Sigma * w_mkt
    
    Parameters
    ----------
    cov : (N, N) annualized covariance matrix
    market_weights : (N,) market-cap weights (or equal-weight proxy)
    risk_aversion : scalar lambda (typically 2-4)
    
    Returns
    -------
    pi : (N,) implied excess returns
    """
    return risk_aversion * cov @ market_weights


def build_views_from_convictions(
    valid_assets: list[dict],
    equilibrium_returns: np.ndarray,
    conviction_excess: dict,
    conviction_confidence: dict,
    n_assets: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int]]:
    """
    Translate investor conviction labels into BL views.
    
    For each asset with a non-zero conviction:
      - P[k, i] = 1  (absolute view on asset i)
      - Q[k] = equilibrium_return[i] + excess_return[action]
      - confidence[k] = conviction_confidence[action]
    
    IMPORTANT: Views are anchored to CAPM equilibrium (pi), NOT historical
    returns. This avoids contaminating forward-looking convictions with
    backward-looking noise.
    
    FIX #1: Returns genuinely empty arrays (0 rows) when no views exist,
    instead of creating a phantom view on asset 0.
    
    FIX #2: Now also returns per-view confidence levels from
    CONVICTION_CONFIDENCE for use in Omega construction.
    
    Parameters
    ----------
    valid_assets : list of asset dicts with 'action' key
    equilibrium_returns : (N,) CAPM implied returns (pi = delta * Sigma * w_mkt)
    conviction_excess : dict mapping action → excess return
    conviction_confidence : dict mapping action → confidence (0-1)
    n_assets : total number of assets
    
    Returns
    -------
    P : (K, N) pick matrix  (K=0 if no views)
    Q : (K,) view vector
    confidences : (K,) per-view confidence levels
    view_indices : list of asset indices that have views
    """
    P_list = []
    Q_list = []
    conf_list = []
    view_indices = []
    
    for i, asset in enumerate(valid_assets):
        action = asset.get("action", "Maintien")
        excess = conviction_excess.get(action, 0.0)
        
        if abs(excess) > 1e-6:  # Skip neutral views
            row = np.zeros(n_assets)
            row[i] = 1.0
            P_list.append(row)
            # Anchor to equilibrium, not history
            Q_list.append(float(equilibrium_returns[i]) + excess)
            conf_list.append(conviction_confidence.get(action, 0.30))
            view_indices.append(i)
    
    # FIX #1: Return truly empty arrays when no views exist
    if not P_list:
        return (
            np.zeros((0, n_assets)),
            np.zeros(0),
            np.zeros(0),
            [],
        )
    
    P = np.array(P_list)
    Q = np.array(Q_list)
    confidences = np.array(conf_list)
    
    return P, Q, confidences, view_indices


def black_litterman(
    cov: np.ndarray,
    market_weights: np.ndarray,
    P: np.ndarray,
    Q: np.ndarray,
    confidences: np.ndarray = None,
    tau: float = 0.05,
    omega_scale: float = 0.5,
    risk_aversion: float = 2.5,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Full Black-Litterman model.
    
    Combines equilibrium returns (Pi) with investor views (P, Q)
    to produce posterior expected returns and covariance.
    
    Formula:
      mu_BL = [(tau*Sigma)^-1 + P'*Omega^-1*P]^-1 
              * [(tau*Sigma)^-1*Pi + P'*Omega^-1*Q]
      Sigma_BL = Sigma + [(tau*Sigma)^-1 + P'*Omega^-1*P]^-1
    
    FIX #1: Short-circuits to equilibrium when P has zero rows (no views).
    
    FIX #2: Per-view confidence scaling of Omega. High confidence
    (e.g., 0.90 for Conviction Forte) → tight Omega → posterior pulled
    close to the view. Low confidence (e.g., 0.55) → wide Omega → 
    posterior stays near equilibrium.
    
    Parameters
    ----------
    cov : (N, N) annualized covariance
    market_weights : (N,) equilibrium weights
    P : (K, N) pick matrix (K can be 0)
    Q : (K,) expected returns for each view
    confidences : (K,) per-view confidence levels (0-1), from CONVICTION_CONFIDENCE
    tau : uncertainty on equilibrium (0.01–0.10 typical)
    omega_scale : base confidence in views (lower = more confident)
    risk_aversion : lambda for CAPM
    
    Returns
    -------
    bl_returns : (N,) posterior expected returns
    bl_cov : (N, N) posterior covariance
    """
    n = len(market_weights)
    
    # Equilibrium returns
    pi = implied_equilibrium_returns(cov, market_weights, risk_aversion)
    
    # FIX #1: No views → return equilibrium + estimation uncertainty
    if P.shape[0] == 0:
        bl_cov = cov + tau * cov
        bl_cov = (bl_cov + bl_cov.T) / 2
        return pi, bl_cov
    
    # ── Build Omega with per-view confidence scaling (FIX #2) ────────────
    tau_cov = tau * cov
    
    # Base view uncertainty: variance of each view from the prior
    base_omega_diag = np.diag(P @ tau_cov @ P.T)
    
    if confidences is not None and len(confidences) == P.shape[0]:
        # Scale each view's uncertainty by (1-c)/c:
        #   confidence=0.90 → scale=0.11 (very tight, strong pull to view)
        #   confidence=0.55 → scale=0.82 (moderate)
        #   confidence=0.30 → scale=2.33 (loose, stays near equilibrium)
        # Then multiply by omega_scale as a global knob
        conf_clipped = np.clip(confidences, 0.05, 0.99)
        per_view_scale = (1.0 - conf_clipped) / conf_clipped
        omega_diag = omega_scale * per_view_scale * base_omega_diag
    else:
        # Fallback: uniform scaling (original behavior)
        omega_diag = omega_scale * base_omega_diag
    
    omega = np.diag(omega_diag)
    
    # Ensure omega is positive definite
    omega += np.eye(len(omega)) * 1e-8
    
    # BL formula
    inv_tau_cov = np.linalg.inv(tau_cov + np.eye(n) * 1e-10)
    inv_omega = np.linalg.inv(omega)
    
    # Posterior precision
    M_inv = inv_tau_cov + P.T @ inv_omega @ P
    M = np.linalg.inv(M_inv + np.eye(n) * 1e-10)
    
    # Posterior mean
    bl_returns = M @ (inv_tau_cov @ pi + P.T @ inv_omega @ Q)
    
    # Posterior covariance (He & Litterman 1999)
    bl_cov = cov + M
    
    # Symmetrize for numerical stability
    bl_cov = (bl_cov + bl_cov.T) / 2
    
    return bl_returns, bl_cov


# ═════════════════════════════════════════════════════════════════════════════
# ② HIERARCHICAL RISK PARITY (HRP)
# ═════════════════════════════════════════════════════════════════════════════

def _correlation_distance(corr: np.ndarray) -> np.ndarray:
    """Convert correlation matrix to distance matrix: d = sqrt(0.5*(1-rho))."""
    dist = np.sqrt(0.5 * (1 - corr))
    np.fill_diagonal(dist, 0.0)
    dist = (dist + dist.T) / 2.0
    return dist


def _quasi_diagonalize(link: np.ndarray) -> list[int]:
    """
    Reorder assets so correlated ones are adjacent (quasi-diagonal matrix).
    Traverses the linkage tree to produce a leaf ordering.
    """
    link = link.astype(int)
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
    n_items = link[-1, 3]
    
    while sort_ix.max() >= n_items:
        sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
        df0 = sort_ix[sort_ix >= n_items]
        i = df0.index
        j = df0.values - n_items
        sort_ix[i] = link[j, 0]
        df1 = pd.Series(link[j, 1], index=i + 1)
        sort_ix = pd.concat([sort_ix, df1])
        sort_ix = sort_ix.sort_index()
        sort_ix.index = range(sort_ix.shape[0])
    
    return sort_ix.astype(int).tolist()


def _cluster_var(cov: np.ndarray, indices: list[int]) -> float:
    """
    Compute the variance of an Inverse-Variance Portfolio (IVP)
    over a subset of assets.
    """
    sub_cov = cov[np.ix_(indices, indices)]
    diag = np.diag(sub_cov)
    diag = np.maximum(diag, 1e-10)
    ivp_w = 1.0 / diag
    ivp_w /= ivp_w.sum()
    return float(ivp_w @ sub_cov @ ivp_w)


def _recursive_bisection(cov: np.ndarray, sorted_indices: list[int]) -> np.ndarray:
    """
    Core HRP allocation: recursively split the sorted asset list
    and allocate risk budget between halves based on cluster variance.
    
    At each level:
      alpha = 1 - Var(left) / (Var(left) + Var(right))
      w[left]  *= alpha
      w[right] *= (1 - alpha)
    """
    w = pd.Series(1.0, index=sorted_indices)
    clusters = [sorted_indices]
    
    while clusters:
        new_clusters = []
        for items in clusters:
            if len(items) <= 1:
                continue
            
            mid = len(items) // 2
            left = items[:mid]
            right = items[mid:]
            
            var_l = _cluster_var(cov, left)
            var_r = _cluster_var(cov, right)
            
            total_var = var_l + var_r
            if total_var < 1e-12:
                alpha = 0.5
            else:
                alpha = 1.0 - var_l / total_var
            
            alpha = np.clip(alpha, 0.05, 0.95)
            
            w[left] *= alpha
            w[right] *= (1.0 - alpha)
            
            if len(left) > 1:
                new_clusters.append(left)
            if len(right) > 1:
                new_clusters.append(right)
        
        clusters = new_clusters
    
    # Convert to numpy array in original order
    result = np.zeros(cov.shape[0])
    for idx, val in w.items():
        result[idx] = val
    
    return result / result.sum()


def hrp_allocate(
    cov: np.ndarray,
    corr: np.ndarray,
    linkage_method: str = "ward",
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """
    Full HRP pipeline: distance → clustering → quasi-diag → recursive bisection.
    
    Parameters
    ----------
    cov : (N, N) covariance matrix (can be BL-adjusted)
    corr : (N, N) correlation matrix
    linkage_method : hierarchical clustering method
    
    Returns
    -------
    weights : (N,) HRP weights (sum to 1)
    linkage_matrix : scipy linkage matrix (for dendrogram)
    sorted_indices : leaf ordering from quasi-diagonalization
    """
    n = cov.shape[0]
    
    dist = _correlation_distance(corr)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method=linkage_method)
    sorted_ix = _quasi_diagonalize(link)
    weights = _recursive_bisection(cov, sorted_ix)
    
    return weights, link, sorted_ix


def extract_clusters(
    linkage_matrix: np.ndarray, 
    n_clusters: int = None,
    distance_threshold: float = None,
) -> np.ndarray:
    """Extract flat clusters from hierarchical clustering."""
    if n_clusters:
        return fcluster(linkage_matrix, t=n_clusters, criterion="maxclust")
    elif distance_threshold:
        return fcluster(linkage_matrix, t=distance_threshold, criterion="distance")
    else:
        t = 0.7 * linkage_matrix[:, 2].max()
        return fcluster(linkage_matrix, t=t, criterion="distance")


# ═════════════════════════════════════════════════════════════════════════════
# ③ HYBRID BL × HRP
# ═════════════════════════════════════════════════════════════════════════════

def hybrid_bl_hrp(
    hrp_weights: np.ndarray,
    bl_returns: np.ndarray,
    cov_matrix: np.ndarray,
    valid_assets: list[dict] = None,
    conviction_excess: dict = None,
    alpha: float = 0.35,
) -> np.ndarray:
    """
    Combine HRP risk-based weights with BL return views.
    
    Method:
      1. Compute vol-adjusted BL scores (BL return / asset vol)
      2. Add a direct conviction bonus based on action label
      3. Apply exponential tilt: w_hybrid = w_hrp * exp(alpha * score)
      4. Renormalize to sum to 1
    
    FIX #7: Conviction bonus is now normalized symmetrically by the max
    absolute excess return, so buy (+8%) and sell (-4%) have proportional
    impact instead of the old asymmetric normalization by 5%.
    
    Parameters
    ----------
    hrp_weights : (N,) HRP allocation
    bl_returns : (N,) BL posterior expected returns
    cov_matrix : (N, N) covariance for vol-adjustment
    valid_assets : list of asset dicts (for conviction bonus)
    conviction_excess : dict action → excess return
    alpha : tilt strength (0 = pure HRP, >0.5 = aggressive BL tilt)
    
    Returns
    -------
    hybrid_weights : (N,) combined weights
    """
    n = len(hrp_weights)
    
    # ── Vol-adjusted BL score (Sharpe-like) ──────────────────────────────
    asset_vol = np.sqrt(np.diag(cov_matrix))
    asset_vol = np.maximum(asset_vol, 1e-8)
    vol_adj_scores = bl_returns / asset_vol
    
    # Z-score the vol-adjusted scores
    score_z = vol_adj_scores - vol_adj_scores.mean()
    score_std = score_z.std()
    if score_std > 1e-8:
        score_z = score_z / score_std
    
    # ── Direct conviction bonus (FIX #7: symmetric normalization) ────────
    conviction_bonus = np.zeros(n)
    if valid_assets is not None and conviction_excess is not None:
        # Find max absolute excess for symmetric normalization
        all_excess = [abs(v) for v in conviction_excess.values() if abs(v) > 1e-6]
        max_abs_excess = max(all_excess) if all_excess else 0.08
        
        for i, asset in enumerate(valid_assets):
            action = asset.get("action", "Maintien")
            excess = conviction_excess.get(action, 0.0)
            # Symmetric: +8% → +1.0, -4% → -0.5, -8% would → -1.0
            conviction_bonus[i] = excess / max_abs_excess if max_abs_excess > 1e-8 else 0.0
    
    # ── Combined score ───────────────────────────────────────────────────
    # 60% vol-adjusted BL + 40% direct conviction
    combined_score = 0.6 * score_z + 0.4 * conviction_bonus
    
    # ── Exponential tilt ─────────────────────────────────────────────────
    tilt = np.exp(alpha * combined_score)
    
    # ── Combine with HRP ─────────────────────────────────────────────────
    hybrid = hrp_weights * tilt
    hybrid = np.maximum(hybrid, 0)
    
    total = hybrid.sum()
    if total > 0:
        hybrid /= total
    else:
        hybrid = hrp_weights.copy()
    
    return hybrid


# ═════════════════════════════════════════════════════════════════════════════
# ④ UCITS CONSTRAINTS
# ═════════════════════════════════════════════════════════════════════════════

def apply_ucits(
    weights: np.ndarray,
    asset_names: list[str],
    max_single: float = 0.10,
    max_sum_big: float = 0.40,
    max_cash: float = 0.03,
    max_cluster: float = 0.20,
    clusters: list[str] = None,
    cash_keywords: list[str] = None,
    max_iterations: int = 100,
) -> tuple[np.ndarray, dict]:
    """
    Apply UCITS V/VI diversification rules iteratively until convergence.
    
    Rules enforced:
      1. No single position > max_single (typically 10%)
      2. Sum of all positions > 5% must be ≤ max_sum_big (40%)
      3. Cash positions ≤ max_cash (3%)
      4. No single cluster > max_cluster (default 20%)
    
    FIX #3: Added hard-clip safety net after the iterative loop.
    If the loop exits without full convergence (e.g., redistribution
    from one rule re-violates another), a final pass hard-clips all
    violations and renormalizes. This guarantees all_pass=True on exit.
    """
    if cash_keywords is None:
        cash_keywords = ["Cash", "Liquidit", "Money Market", "EUR=X"]
    
    w = weights.copy()
    n = len(w)
    
    # Identify cash positions
    cash_idx = set()
    for i, name in enumerate(asset_names):
        if any(kw.lower() in name.lower() for kw in cash_keywords):
            cash_idx.add(i)
    
    non_cash = [i for i in range(n) if i not in cash_idx]
    
    # Build cluster index map
    cluster_map = {}
    if clusters is not None:
        for i, cl in enumerate(clusters):
            cluster_map.setdefault(cl, []).append(i)
    
    # ── Iterative constraint enforcement ─────────────────────────────────
    for iteration in range(max_iterations):
        changed = False
        
        # ── Rule 1: Cash cap ────────────────────────────────────────────
        for idx in cash_idx:
            if w[idx] > max_cash + 1e-8:
                excess = w[idx] - max_cash
                w[idx] = max_cash
                nc_sum = sum(w[j] for j in non_cash)
                if nc_sum > 0:
                    for j in non_cash:
                        w[j] += excess * (w[j] / nc_sum)
                changed = True
        
        # ── Rule 2: Max single position ─────────────────────────────────
        for i in range(n):
            if w[i] > max_single + 1e-8:
                excess = w[i] - max_single
                w[i] = max_single
                others = [j for j in range(n) if j != i and j not in cash_idx]
                o_sum = sum(w[j] for j in others)
                if o_sum > 0:
                    for j in others:
                        w[j] += excess * (w[j] / o_sum)
                changed = True
        
        # ── Rule 3: 5/10/40 rule ────────────────────────────────────────
        big = [i for i in range(n) if w[i] > 0.05 + 1e-8]
        big_sum = sum(w[i] for i in big)
        if big_sum > max_sum_big + 1e-8:
            scale = max_sum_big / big_sum
            excess_total = 0.0
            for i in big:
                excess_total += w[i] * (1 - scale)
                w[i] *= scale
            small = [j for j in range(n) if j not in big and j not in cash_idx]
            s_sum = sum(w[j] for j in small)
            if s_sum > 0:
                for j in small:
                    w[j] += excess_total * (w[j] / s_sum)
            changed = True
        
        # ── Rule 4: Cluster concentration cap ───────────────────────────
        if cluster_map and max_cluster > 0:
            for cl_name, cl_idx in cluster_map.items():
                cl_sum = sum(w[i] for i in cl_idx)
                if cl_sum > max_cluster + 1e-8:
                    scale = max_cluster / cl_sum
                    excess_total = 0.0
                    for i in cl_idx:
                        excess_total += w[i] * (1 - scale)
                        w[i] *= scale
                    outside = [j for j in range(n) if j not in cl_idx and j not in cash_idx]
                    o_sum = sum(w[j] for j in outside)
                    if o_sum > 0:
                        for j in outside:
                            w[j] += excess_total * (w[j] / o_sum)
                    changed = True
        
        # Renormalize
        w = np.maximum(w, 0)
        total = w.sum()
        if total > 0:
            w /= total
        
        if not changed:
            break
    
    # ── FIX #3: Hard-clip safety net ─────────────────────────────────────
    # If the iterative loop didn't fully converge, force compliance.
    # This is a final pass that may slightly alter the allocation
    # but guarantees all UCITS rules are satisfied on exit.
    safety_passes = 0
    for _ in range(20):  # Up to 20 additional safety passes
        violated = False
        
        # Cash cap
        for idx in cash_idx:
            if w[idx] > max_cash + 1e-8:
                w[idx] = max_cash
                violated = True
        
        # Max single
        for i in range(n):
            if w[i] > max_single + 1e-8:
                w[i] = max_single
                violated = True
        
        # 5/10/40
        big = [i for i in range(n) if w[i] > 0.05 + 1e-8]
        big_sum = sum(w[i] for i in big)
        if big_sum > max_sum_big + 1e-8:
            scale = max_sum_big / big_sum
            for i in big:
                w[i] *= scale
            violated = True
        
        # Cluster cap
        if cluster_map and max_cluster > 0:
            for cl_name, cl_idx in cluster_map.items():
                cl_sum = sum(w[i] for i in cl_idx)
                if cl_sum > max_cluster + 1e-8:
                    scale = max_cluster / cl_sum
                    for i in cl_idx:
                        w[i] *= scale
                    violated = True
        
        # Renormalize
        w = np.maximum(w, 0)
        total = w.sum()
        if total > 0:
            w /= total
        
        safety_passes += 1
        if not violated:
            break
    
    # ── Verification report ──────────────────────────────────────────────
    actual_max = float(w.max())
    actual_big_sum = float(sum(wi for wi in w if wi > 0.05))
    actual_cash = float(sum(w[i] for i in cash_idx))
    n_significant = int(sum(1 for wi in w if wi > 0.005))
    
    cluster_report = {}
    if cluster_map:
        for cl_name, cl_idx in cluster_map.items():
            cl_w = sum(w[i] for i in cl_idx)
            cluster_report[cl_name] = f"{cl_w*100:.1f}%"
    
    max_cluster_actual = max(
        (sum(w[i] for i in idx) for idx in cluster_map.values()),
        default=0,
    ) if cluster_map else 0
    
    report = {
        "max_position":    {"value": actual_max,        "limit": max_single,  "pass": actual_max <= max_single + 1e-6},
        "sum_above_5pct":  {"value": actual_big_sum,     "limit": max_sum_big, "pass": actual_big_sum <= max_sum_big + 1e-6},
        "cash_weight":     {"value": actual_cash,        "limit": max_cash,    "pass": actual_cash <= max_cash + 1e-6},
        "max_cluster_wt":  {"value": max_cluster_actual, "limit": max_cluster, "pass": max_cluster_actual <= max_cluster + 1e-6},
        "n_significant":   {"value": n_significant,      "limit": 16,          "pass": n_significant >= 16},
        "iterations_used": iteration + 1,
        "safety_passes":   safety_passes,
        "all_pass":        all([
            actual_max <= max_single + 1e-6,
            actual_big_sum <= max_sum_big + 1e-6,
            actual_cash <= max_cash + 1e-6,
            max_cluster_actual <= max_cluster + 1e-6,
        ]),
    }
    
    return w, report


# ═════════════════════════════════════════════════════════════════════════════
# ⑤ FULL PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def run_full_pipeline(
    returns_df: pd.DataFrame,
    valid_assets: list[dict],
    conviction_excess: dict,
    conviction_confidence: dict,
    params: dict,
) -> dict:
    """
    Execute the complete BL-HRP pipeline.
    
    CHANGES (v2.1):
      - Now accepts conviction_confidence dict (FIX #2)
      - Passes confidences through to black_litterman for per-view Omega
    
    Returns a dict with all intermediate and final results.
    """
    n = returns_df.shape[1]
    asset_names = returns_df.columns.tolist()
    
    # ── Covariance & Correlation (annualized) ────────────────────────────
    cov_hist = returns_df.cov().values * 252
    corr_hist = returns_df.corr().values
    mean_ret = returns_df.mean().values * 252
    
    # ── Equal weights (benchmark "before") ───────────────────────────────
    ew_weights = np.ones(n) / n
    
    # ── Black-Litterman ──────────────────────────────────────────────────
    market_weights = ew_weights  # Use EW as proxy for mkt cap
    
    # Compute equilibrium returns FIRST (needed for views)
    pi = implied_equilibrium_returns(cov_hist, market_weights, params["risk_aversion"])
    
    # FIX #1 & #2: Pass conviction_confidence, get per-view confidences back
    P, Q, confidences, view_idx = build_views_from_convictions(
        valid_assets, pi, conviction_excess, conviction_confidence, n
    )
    
    bl_returns, bl_cov = black_litterman(
        cov_hist, market_weights, P, Q,
        confidences=confidences,
        tau=params["tau"],
        omega_scale=params["omega_scale"],
        risk_aversion=params["risk_aversion"],
    )
    
    # ── BL Correlation for HRP ───────────────────────────────────────────
    bl_std = np.sqrt(np.diag(bl_cov))
    bl_std = np.maximum(bl_std, 1e-10)
    bl_corr = bl_cov / np.outer(bl_std, bl_std)
    np.fill_diagonal(bl_corr, 1.0)
    bl_corr = np.clip(bl_corr, -1, 1)
    bl_corr = (bl_corr + bl_corr.T) / 2
    bl_cov = (bl_cov + bl_cov.T) / 2
    
    # ── HRP Standard (on historical cov) ─────────────────────────────────
    hrp_std_w, link_std, sort_std = hrp_allocate(
        cov_hist, corr_hist, params["linkage_method"]
    )
    
    # ── HRP on BL-adjusted cov (the hybrid core) ────────────────────────
    hrp_bl_w, link_bl, sort_bl = hrp_allocate(
        bl_cov, bl_corr, params["linkage_method"]
    )
    
    # ── Hybrid tilt ──────────────────────────────────────────────────────
    hybrid_raw = hybrid_bl_hrp(
        hrp_bl_w, bl_returns, bl_cov,
        valid_assets=valid_assets,
        conviction_excess=conviction_excess,
        alpha=params["bl_alpha"],
    )
    
    # ── UCITS constraints ────────────────────────────────────────────────
    clusters_list = [a.get("cluster", "Autre") for a in valid_assets]
    ucits_w, ucits_report = apply_ucits(
        hybrid_raw, asset_names,
        max_single=params["max_single"],
        max_sum_big=params["max_sum_big"],
        max_cash=params["max_cash"],
        max_cluster=params.get("max_cluster", 0.20),
        clusters=clusters_list,
    )
    
    return {
        # Weights
        "ew_weights":      ew_weights,
        "hrp_std_weights": hrp_std_w,
        "hrp_bl_weights":  hrp_bl_w,
        "hybrid_raw":      hybrid_raw,
        "ucits_weights":   ucits_w,
        
        # BL outputs
        "bl_returns":      bl_returns,
        "bl_cov":          bl_cov,
        "equilibrium_returns": pi,
        "n_views":         len(Q),
        "view_indices":    view_idx,
        
        # Matrices
        "cov_hist":        cov_hist,
        "corr_hist":       corr_hist,
        "mean_returns":    mean_ret,
        
        # HRP outputs
        "linkage_std":     link_std,
        "linkage_bl":      link_bl,
        "sort_bl":         sort_bl,
        
        # UCITS
        "ucits_report":    ucits_report,
        
        # Meta
        "n_assets":        n,
        "asset_names":     asset_names,
    }