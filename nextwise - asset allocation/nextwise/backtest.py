"""
=============================================================================
  backtest.py — Backtest Engine & Risk Metrics
=============================================================================
  
  CHANGES (v2.1):
    FIX #6  — Sortino denominator now uses the standard formula:
              sqrt(mean(min(r-MAR, 0)²)) over ALL observations,
              not std() of only the negative subset.
    FIX #12 — Added transaction cost modeling. At each rebalance, turnover
              is computed as sum(|w_new - w_drifted|) and a proportional
              cost is deducted from the portfolio return.
    MINOR   — Improved docstrings and added cost-related output fields.
=============================================================================
"""

import numpy as np
import pandas as pd


# ═════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═════════════════════════════════════════════════════════════════════════════

def run_backtest(
    returns_df: pd.DataFrame,
    weights: np.ndarray,
    name: str = "Portfolio",
    rebalance_freq: int = 63,
    risk_free_rate: float = 0.03,
    benchmark_returns: pd.Series = None,
    transaction_cost: float = 0.001,
) -> dict:
    """
    Run a realistic backtest with periodic rebalancing and transaction costs.
    
    Mechanics:
      - Start with target weights
      - Each day: portfolio return = sum(w_i * r_i)
      - Weights drift with asset returns (realistic buy-and-hold between rebalances)
      - At each rebalance date, reset weights to target
      - Deduct transaction cost proportional to turnover at each rebalance
    
    Parameters
    ----------
    returns_df : (T, N) daily returns
    weights : (N,) target allocation
    name : label for this backtest
    rebalance_freq : days between rebalancing (63 ≈ quarterly)
    risk_free_rate : annualized risk-free rate
    benchmark_returns : optional Series for relative metrics
    transaction_cost : one-way cost per unit of turnover (default 10bps)
                       Total cost per rebalance = turnover × cost
    
    Returns
    -------
    dict with cumulative returns, drawdown, and all metrics
    """
    n_days, n_assets = returns_df.shape
    daily_rf = risk_free_rate / 252
    
    # ── Simulate with weight drift and transaction costs ──────────────────
    port_returns = np.zeros(n_days)
    current_w = weights.copy()
    weight_history = []
    total_turnover = 0.0
    total_cost = 0.0
    n_rebalances = 0
    
    for t in range(n_days):
        daily_r = returns_df.iloc[t].values
        
        # Portfolio return for the day
        port_returns[t] = np.dot(current_w, daily_r)
        
        # Save weight snapshot
        if t % rebalance_freq == 0:
            weight_history.append({"day": t, "date": returns_df.index[t], "weights": current_w.copy()})
        
        # Drift weights
        if t < n_days - 1:
            current_w = current_w * (1 + daily_r)
            w_sum = current_w.sum()
            if w_sum > 0:
                current_w /= w_sum
            else:
                current_w = weights.copy()
            
            # Rebalance check
            if (t + 1) % rebalance_freq == 0:
                # FIX #12: Compute turnover and deduct transaction cost
                turnover = np.sum(np.abs(weights - current_w))
                rebal_cost = turnover * transaction_cost
                
                total_turnover += turnover
                total_cost += rebal_cost
                n_rebalances += 1
                
                # Deduct cost from next day's return
                port_returns[t] -= rebal_cost
                
                # Reset to target
                current_w = weights.copy()
    
    port_returns = pd.Series(port_returns, index=returns_df.index, name=name)
    
    # ── Cumulative returns ───────────────────────────────────────────────
    cum_returns = (1 + port_returns).cumprod()
    total_return = float(cum_returns.iloc[-1] - 1)
    ann_return = float((1 + total_return) ** (252 / n_days) - 1)
    
    # ── Volatility ───────────────────────────────────────────────────────
    ann_vol = float(port_returns.std() * np.sqrt(252))
    
    # ── Sharpe Ratio ─────────────────────────────────────────────────────
    excess_returns = port_returns - daily_rf
    sharpe = float(excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0
    
    # ── Sortino Ratio (FIX #6) ───────────────────────────────────────────
    # Standard formula: downside deviation = sqrt(mean(min(r - MAR, 0)²))
    # computed over ALL observations, not just negatives
    downside_returns = np.minimum(excess_returns, 0)
    downside_vol = float(np.sqrt((downside_returns ** 2).mean()) * np.sqrt(252))
    sortino = float((ann_return - risk_free_rate) / downside_vol) if downside_vol > 1e-8 else 0
    
    # ── Drawdown ─────────────────────────────────────────────────────────
    rolling_max = cum_returns.cummax()
    drawdown = (cum_returns - rolling_max) / rolling_max
    max_dd = float(drawdown.min())
    
    # Drawdown duration
    is_dd = drawdown < -0.001
    dd_periods = []
    current_dd_start = None
    for i, in_dd in enumerate(is_dd):
        if in_dd and current_dd_start is None:
            current_dd_start = i
        elif not in_dd and current_dd_start is not None:
            dd_periods.append(i - current_dd_start)
            current_dd_start = None
    if current_dd_start is not None:
        dd_periods.append(len(is_dd) - current_dd_start)
    max_dd_duration = max(dd_periods) if dd_periods else 0
    
    # ── Calmar Ratio ─────────────────────────────────────────────────────
    calmar = float(ann_return / abs(max_dd)) if abs(max_dd) > 1e-6 else 0
    
    # ── VaR & CVaR (95% and 99%) ─────────────────────────────────────────
    var_95 = float(np.percentile(port_returns, 5))
    var_99 = float(np.percentile(port_returns, 1))
    cvar_95 = float(port_returns[port_returns <= var_95].mean()) if len(port_returns[port_returns <= var_95]) > 0 else var_95
    cvar_99 = float(port_returns[port_returns <= var_99].mean()) if len(port_returns[port_returns <= var_99]) > 0 else var_99
    
    # ── Skewness & Kurtosis ──────────────────────────────────────────────
    skewness = float(port_returns.skew())
    kurtosis = float(port_returns.kurtosis())
    
    # ── Win Rate ─────────────────────────────────────────────────────────
    win_rate = float((port_returns > 0).mean())
    
    # ── Best & Worst Days ────────────────────────────────────────────────
    best_day = float(port_returns.max())
    worst_day = float(port_returns.min())
    
    # ── Transaction cost summary ─────────────────────────────────────────
    avg_turnover = total_turnover / max(n_rebalances, 1)
    ann_cost = total_cost * (252 / n_days)  # Annualize
    
    # ── Benchmark-relative metrics ───────────────────────────────────────
    beta = np.nan
    alpha = np.nan
    tracking_error = np.nan
    info_ratio = np.nan
    
    if benchmark_returns is not None:
        common_idx = port_returns.index.intersection(benchmark_returns.index)
        if len(common_idx) > 50:
            pr = port_returns.loc[common_idx].values
            br = benchmark_returns.loc[common_idx].values
            
            # Beta
            cov_pb = np.cov(pr, br)
            beta = float(cov_pb[0, 1] / cov_pb[1, 1]) if cov_pb[1, 1] > 0 else 1.0
            
            # Alpha (Jensen's)
            bm_ann = float(np.prod(1 + br) ** (252 / len(br)) - 1)
            alpha = float(ann_return - (risk_free_rate + beta * (bm_ann - risk_free_rate)))
            
            # Tracking Error & Information Ratio
            active_ret = pr - br
            tracking_error = float(np.std(active_ret) * np.sqrt(252))
            info_ratio = float(np.mean(active_ret) * 252 / tracking_error) if tracking_error > 0 else 0
    
    # ── Monthly returns for table ────────────────────────────────────────
    monthly_returns = port_returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    
    # ── Rolling metrics (window ≈ 6 months or 1/3 of data) ──────────────
    window = min(126, n_days // 3)
    rolling_vol = port_returns.rolling(window).std() * np.sqrt(252)
    rolling_sharpe = (port_returns.rolling(window).mean() * 252 - risk_free_rate) / (port_returns.rolling(window).std() * np.sqrt(252))
    
    return {
        "name":             name,
        "cum_returns":      cum_returns,
        "daily_returns":    port_returns,
        "drawdown":         drawdown,
        "monthly_returns":  monthly_returns,
        "rolling_vol":      rolling_vol,
        "rolling_sharpe":   rolling_sharpe,
        "weight_history":   weight_history,
        
        # Performance
        "total_return":     total_return,
        "ann_return":       ann_return,
        "ann_vol":          ann_vol,
        "sharpe":           sharpe,
        "sortino":          sortino,
        "calmar":           calmar,
        
        # Drawdown
        "max_dd":           max_dd,
        "max_dd_duration":  max_dd_duration,
        
        # Tail risk
        "var_95":           var_95,
        "var_99":           var_99,
        "cvar_95":          cvar_95,
        "cvar_99":          cvar_99,
        "skewness":         skewness,
        "kurtosis":         kurtosis,
        
        # Stats
        "win_rate":         win_rate,
        "best_day":         best_day,
        "worst_day":        worst_day,
        
        # Relative
        "beta":             beta,
        "alpha":            alpha,
        "tracking_error":   tracking_error,
        "info_ratio":       info_ratio,
        
        # Transaction costs (FIX #12)
        "total_turnover":   total_turnover,
        "avg_turnover":     avg_turnover,
        "total_cost":       total_cost,
        "ann_cost":         ann_cost,
        "n_rebalances":     n_rebalances,
    }


# ═════════════════════════════════════════════════════════════════════════════
# CONCENTRATION & DIVERSIFICATION METRICS
# ═════════════════════════════════════════════════════════════════════════════

def concentration_metrics(
    weights: np.ndarray,
    asset_names: list[str],
    clusters: list[str],
    cov_matrix: np.ndarray,
) -> dict:
    """
    Compute portfolio concentration and diversification metrics.
    
    Metrics:
      - HHI (Herfindahl-Hirschman Index): sum(w_i^2), lower = more diversified
      - ENP (Effective Number of Positions): 1/HHI
      - HHI_cluster: same at cluster level
      - Diversification Ratio: weighted avg vol / portfolio vol (>1 = diversification benefit)
      - Top-5, Top-10 concentration
    """
    n = len(weights)
    
    # ── HHI at position level ────────────────────────────────────────────
    hhi = float(np.sum(weights ** 2))
    enp = 1.0 / hhi if hhi > 0 else n
    
    # ── HHI at cluster level ─────────────────────────────────────────────
    unique_clusters = sorted(set(clusters))
    cluster_weights = {}
    for c in unique_clusters:
        idx = [i for i, cl in enumerate(clusters) if cl == c]
        cluster_weights[c] = float(sum(weights[i] for i in idx))
    
    hhi_cluster = sum(w**2 for w in cluster_weights.values())
    enp_cluster = 1.0 / hhi_cluster if hhi_cluster > 0 else len(unique_clusters)
    
    # ── Diversification Ratio (Choueifaty 2008) ──────────────────────────
    individual_vols = np.sqrt(np.diag(cov_matrix))
    weighted_avg_vol = float(weights @ individual_vols)
    port_vol = float(np.sqrt(weights @ cov_matrix @ weights))
    div_ratio = weighted_avg_vol / port_vol if port_vol > 1e-10 else 1.0
    
    # ── Concentration metrics ────────────────────────────────────────────
    sorted_w = sorted(weights, reverse=True)
    top5  = float(sum(sorted_w[:5]))
    top10 = float(sum(sorted_w[:10]))
    n_significant = int(sum(1 for w in weights if w > 0.005))
    n_meaningful  = int(sum(1 for w in weights if w > 0.01))
    
    # ── Marginal Risk Contribution (Euler decomposition) ─────────────────
    if port_vol > 1e-10:
        mrc = (cov_matrix @ weights) / port_vol
        risk_contrib = weights * mrc
        risk_contrib_pct = risk_contrib / risk_contrib.sum() if risk_contrib.sum() > 0 else risk_contrib
    else:
        risk_contrib_pct = weights.copy()
    
    return {
        "hhi":              hhi,
        "enp":              enp,
        "hhi_cluster":      hhi_cluster,
        "enp_cluster":      enp_cluster,
        "div_ratio":        div_ratio,
        "top5":             top5,
        "top10":            top10,
        "n_significant":    n_significant,
        "n_meaningful":     n_meaningful,
        "cluster_weights":  cluster_weights,
        "risk_contrib_pct": risk_contrib_pct,
        "port_vol":         port_vol,
    }


# ═════════════════════════════════════════════════════════════════════════════
# COMPARISON HELPER
# ═════════════════════════════════════════════════════════════════════════════

def compare_backtests(*backtests) -> pd.DataFrame:
    """
    Build a comparison DataFrame from multiple backtest results.
    """
    metrics = [
        ("Rendement Total",       "total_return",    "{:.1%}"),
        ("Rendement Annualisé",   "ann_return",      "{:.2%}"),
        ("Volatilité Ann.",       "ann_vol",         "{:.2%}"),
        ("Sharpe Ratio",          "sharpe",          "{:.3f}"),
        ("Sortino Ratio",         "sortino",         "{:.3f}"),
        ("Calmar Ratio",          "calmar",          "{:.3f}"),
        ("Max Drawdown",          "max_dd",          "{:.2%}"),
        ("DD Duration (jours)",   "max_dd_duration", "{:.0f}"),
        ("Beta",                  "beta",            "{:.3f}"),
        ("Alpha (Jensen)",        "alpha",           "{:.2%}"),
        ("Tracking Error",        "tracking_error",  "{:.2%}"),
        ("Info Ratio",            "info_ratio",      "{:.3f}"),
        ("VaR 95% (jour)",        "var_95",          "{:.3%}"),
        ("CVaR 95% (jour)",       "cvar_95",         "{:.3%}"),
        ("VaR 99% (jour)",        "var_99",          "{:.3%}"),
        ("Skewness",              "skewness",        "{:.3f}"),
        ("Kurtosis (excess)",     "kurtosis",        "{:.3f}"),
        ("Win Rate",              "win_rate",        "{:.1%}"),
        ("Best Day",              "best_day",        "{:.2%}"),
        ("Worst Day",             "worst_day",       "{:.2%}"),
        ("Coût Ann. (tx costs)",  "ann_cost",        "{:.3%}"),
        ("Turnover Moyen/Rebal",  "avg_turnover",    "{:.2%}"),
    ]
    
    rows = []
    for label, key, fmt in metrics:
        row = {"Métrique": label}
        for bt in backtests:
            val = bt.get(key, np.nan)
            if pd.isna(val):
                row[bt["name"]] = "—"
            else:
                row[bt["name"]] = fmt.format(val)
        rows.append(row)
    
    return pd.DataFrame(rows).set_index("Métrique")