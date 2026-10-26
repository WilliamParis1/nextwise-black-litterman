"""
=============================================================================
  app.py — Streamlit Dashboard: Black-Litterman × HRP Hybrid Allocator
=============================================================================
  
  Run:  streamlit run app.py
  
  Tabs:
    📊 Résumé          KPIs, allocation sunburst, UCITS check
    📈 Backtest        Performance, drawdown, rolling metrics
    ⚖️ Avant/Après     Full comparison tables & charts
    🌳 Clustering      Dendrogram, correlation heatmap
    🎯 Risque          VaR, risk contribution, concentration
    ⚙️ Paramètres      Model explainer & data quality
  
  CHANGES (v2.1):
    — Updated run_full_pipeline call to pass CONVICTION_CONFIDENCE (FIX #2)
    — Updated run_backtest calls to pass transaction_cost (FIX #12)
    — Fixed month label mapping in heatmap (FIX #10)
    — Fixed colorscale domain for risk contribution chart (FIX #11)
    — Added transaction cost display in comparison tables
=============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy.cluster.hierarchy import dendrogram
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json

from config import (
    PORTFOLIO, CONVICTION_EXCESS, CONVICTION_CONFIDENCE,
    ACTION_COLORS, ACTION_EMOJI, DEFAULT_PARAMS,
)
from data_loader import load_portfolio_data, load_benchmark, data_quality_summary
from models import run_full_pipeline
from backtest import run_backtest, concentration_metrics, compare_backtests


# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="BL × HRP — Portfolio Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    /* Dark finance theme overrides */
    .stMetric { background: rgba(17,17,34,0.6); border-radius: 10px; padding: 12px; border: 1px solid #1e1e3e; }
    .stMetric label { color: #8888aa !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.05em; }
    .stMetric [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: rgba(17,17,34,0.8); border-radius: 8px 8px 0 0;
        padding: 8px 20px; border: 1px solid #1e1e3e; font-weight: 600;
    }
    
    div[data-testid="stSidebar"] { background: #0d0d1a; }
    
    .ucits-pass { color: #00ff88; font-weight: 700; }
    .ucits-fail { color: #ff4757; font-weight: 700; }
    
    h1, h2, h3 { font-family: 'Courier New', monospace !important; }
    
    .big-number { font-size: 2.5rem; font-weight: 700; font-family: 'Courier New', monospace; }
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Model Parameters
# ═════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ⚡ BL × HRP")
    st.markdown("**Modèle Hybride d'Allocation**")
    st.divider()
    
    st.markdown("### 📅 Données")
    lookback = st.slider("Historique (années)", 1, 5, DEFAULT_PARAMS["lookback_years"])
    benchmark_tick = st.text_input("Benchmark", DEFAULT_PARAMS["benchmark_ticker"])
    
    st.divider()
    st.markdown("### 🧠 Black-Litterman")
    tau = st.slider("τ (incertitude équilibre)", 0.01, 0.20, DEFAULT_PARAMS["tau"], 0.01,
                    help="Plus tau est bas, plus on fait confiance au CAPM. Typiquement 0.02–0.10.")
    risk_aversion = st.slider("λ (aversion au risque)", 1.0, 5.0, DEFAULT_PARAMS["risk_aversion"], 0.5,
                              help="Lambda du CAPM inversé. Plus élevé = rendements d'équilibre plus hauts.")
    omega_scale = st.slider("Ω scale (confiance vues)", 0.1, 2.0, DEFAULT_PARAMS["omega_scale"], 0.1,
                            help="Multiplicateur global sur l'incertitude des vues. "
                                 "Chaque vue est aussi pondérée par sa confiance individuelle (CONVICTION_CONFIDENCE).")
    
    st.divider()
    st.markdown("### 🌳 HRP")
    linkage_method = st.selectbox("Méthode clustering", ["ward", "complete", "average", "single"],
                                  help="Ward: minimise variance intra-cluster (recommandé)")
    bl_alpha = st.slider("α (force du tilt BL)", 0.0, 1.0, DEFAULT_PARAMS["bl_alpha"], 0.05,
                         help="0 = pur HRP (aucune conviction). 1 = fort tilt BL.")
    
    st.divider()
    st.markdown("### 🏛️ UCITS")
    max_single = st.slider("Max position (%)", 5, 15, int(DEFAULT_PARAMS["max_single"]*100)) / 100
    max_sum_big = st.slider("Σ positions >5% (%)", 20, 50, int(DEFAULT_PARAMS["max_sum_big"]*100)) / 100
    max_cash = st.slider("Max cash (%)", 1, 10, int(DEFAULT_PARAMS["max_cash"]*100)) / 100
    max_cluster = st.slider("Max cluster (%)", 10, 35, int(DEFAULT_PARAMS.get("max_cluster", 0.20)*100)) / 100
    
    st.divider()
    st.markdown("### 🔄 Backtest")
    rebal_days = st.selectbox("Rebalancement", [21, 42, 63, 126, 252],
                              index=2, format_func=lambda x: {21:"Mensuel",42:"Bimensuel",63:"Trimestriel",126:"Semestriel",252:"Annuel"}[x])
    rf_rate = st.number_input("Taux sans risque (%)", 0.0, 10.0, DEFAULT_PARAMS["risk_free_rate"]*100, 0.25) / 100
    tx_cost = st.number_input("Coût transaction (bps one-way)", 0.0, 50.0,
                               DEFAULT_PARAMS.get("transaction_cost", 0.001) * 10000, 1.0) / 10000

    st.divider()
    run_button = st.button("🚀 Lancer le Modèle", type="primary", use_container_width=True)

# Collect params
params = {
    "tau": tau, "risk_aversion": risk_aversion, "omega_scale": omega_scale,
    "bl_alpha": bl_alpha, "linkage_method": linkage_method,
    "max_single": max_single, "max_sum_big": max_sum_big, "max_cash": max_cash,
    "max_cluster": max_cluster,
    "rebalance_days": rebal_days, "risk_free_rate": rf_rate,
    "lookback_years": lookback,
    "transaction_cost": tx_cost,
}


# ═════════════════════════════════════════════════════════════════════════════
# HEADER
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("""
# ⚡ BLACK-LITTERMAN × HRP
### Allocation Hybride Multi-Asset — Backtest & Analyse de Risque
""")

st.caption("Convictions initiales qualitatives : la confiance mesure la force d’une vue Black-Litterman, pas une probabilité de gain. Les valorisations récentes ne sont pas prises en compte.")
st.warning("3AAP est un produit Apple à levier quotidien 3x : il n’est pas équivalent à une action Apple détenue à long terme. Les contraintes du modèle ne certifient pas l’éligibilité réglementaire de ce produit.")

# ═════════════════════════════════════════════════════════════════════════════
# DATA LOADING & MODEL EXECUTION
# ═════════════════════════════════════════════════════════════════════════════

# Use session state to persist results
if "model_results" not in st.session_state:
    st.session_state.model_results = None
    st.session_state.bt_results = None

if run_button or st.session_state.model_results is None:
    
    with st.status("🔄 Pipeline en cours...", expanded=True) as status:
        
        # ── Step 1: Load data ────────────────────────────────────────────
        st.write("📡 Téléchargement des données Yahoo Finance...")
        prices_df, returns_df, valid_assets, failed = load_portfolio_data(lookback)
        
        if len(valid_assets) < 10:
            st.error(f"❌ Seulement {len(valid_assets)} actifs chargés. Vérifiez votre connexion internet.")
            st.stop()
        
        dq = data_quality_summary(prices_df, valid_assets, failed)
        st.write(f"✅ {dq['successfully_loaded']}/{dq['total_requested']} actifs chargés ({dq['date_range']})")
        
        if failed:
            st.write(f"⚠️ Tickers échoués: {', '.join(failed)}")
        
        # ── Step 2: Benchmark ────────────────────────────────────────────
        st.write("📊 Chargement du benchmark...")
        bench_ret = load_benchmark(benchmark_tick, lookback)
        
        # ── Step 3: Run model (FIX #2: pass CONVICTION_CONFIDENCE) ───────
        st.write("🧠 Exécution Black-Litterman + HRP...")
        results = run_full_pipeline(
            returns_df, valid_assets,
            CONVICTION_EXCESS, CONVICTION_CONFIDENCE,  # FIX #2
            params,
        )
        
        # ── Step 4: Backtests (FIX #12: pass transaction_cost) ───────────
        st.write("📈 Backtests en cours...")
        
        bt_ew = run_backtest(returns_df, results["ew_weights"], 
                            "Équipondéré (Avant)", rebal_days, rf_rate, bench_ret,
                            transaction_cost=tx_cost)
        bt_hrp = run_backtest(returns_df, results["hrp_std_weights"],
                             "HRP Standard", rebal_days, rf_rate, bench_ret,
                             transaction_cost=tx_cost)
        bt_hybrid = run_backtest(returns_df, results["ucits_weights"],
                                "BL-HRP UCITS (Après)", rebal_days, rf_rate, bench_ret,
                                transaction_cost=tx_cost)
        
        # ── Step 5: Concentration ────────────────────────────────────────
        st.write("🎯 Calcul des métriques de concentration...")
        clusters_list = [a.get("cluster", "Autre") for a in valid_assets]
        
        conc_ew = concentration_metrics(results["ew_weights"], results["asset_names"],
                                        clusters_list, results["cov_hist"])
        conc_hrp = concentration_metrics(results["hrp_std_weights"], results["asset_names"],
                                         clusters_list, results["cov_hist"])
        conc_hybrid = concentration_metrics(results["ucits_weights"], results["asset_names"],
                                            clusters_list, results["cov_hist"])
        
        # Store everything
        st.session_state.model_results = results
        st.session_state.bt_results = {
            "ew": bt_ew, "hrp": bt_hrp, "hybrid": bt_hybrid,
            "conc_ew": conc_ew, "conc_hrp": conc_hrp, "conc_hybrid": conc_hybrid,
        }
        st.session_state.valid_assets = valid_assets
        st.session_state.returns_df = returns_df
        st.session_state.prices_df = prices_df
        st.session_state.bench_ret = bench_ret
        st.session_state.dq = dq
        st.session_state.clusters_list = clusters_list
        st.session_state.failed = failed
        
        status.update(label="✅ Modèle exécuté avec succès!", state="complete")

# ── Aliases for readability ──────────────────────────────────────────────────
R = st.session_state.model_results
BT = st.session_state.bt_results

if R is None or BT is None:
    st.info("👆 Cliquez sur **Lancer le Modèle** dans la sidebar pour commencer.")
    st.stop()

bt_ew = BT["ew"]
bt_hrp = BT["hrp"]
bt_hybrid = BT["hybrid"]
conc_ew = BT["conc_ew"]
conc_hrp = BT["conc_hrp"]
conc_hybrid = BT["conc_hybrid"]
valid_assets = st.session_state.valid_assets
clusters_list = st.session_state.clusters_list


# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Résumé", "📈 Backtest", "⚖️ Avant / Après",
    "🌳 Clustering", "🎯 Risque", "⚙️ Paramètres",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: RÉSUMÉ
# ─────────────────────────────────────────────────────────────────────────────

with tab1:
    
    # ── KPI Row ──────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    
    with c1:
        delta_sharpe = bt_hybrid["sharpe"] - bt_ew["sharpe"]
        st.metric("Sharpe Ratio", f"{bt_hybrid['sharpe']:.2f}",
                  f"{delta_sharpe:+.2f} vs Avant")
    with c2:
        st.metric("Max Drawdown", f"{bt_hybrid['max_dd']*100:.1f}%",
                  f"{(bt_hybrid['max_dd']-bt_ew['max_dd'])*100:+.1f}pp")
    with c3:
        st.metric("Rendement Ann.", f"{bt_hybrid['ann_return']*100:.1f}%",
                  f"{(bt_hybrid['ann_return']-bt_ew['ann_return'])*100:+.1f}pp")
    with c4:
        st.metric("Volatilité", f"{bt_hybrid['ann_vol']*100:.1f}%",
                  f"{(bt_hybrid['ann_vol']-bt_ew['ann_vol'])*100:+.1f}pp", delta_color="inverse")
    with c5:
        st.metric("Beta", f"{bt_hybrid['beta']:.2f}",
                  f"{(bt_hybrid['beta']-bt_ew['beta']):+.2f}", delta_color="inverse")
    with c6:
        st.metric("Div. Ratio", f"{conc_hybrid['div_ratio']:.2f}x",
                  f"{(conc_hybrid['div_ratio']-conc_ew['div_ratio']):+.2f}")
    
    st.divider()
    
    # ── UCITS Compliance Badge ───────────────────────────────────────────
    ucits = R["ucits_report"]
    if ucits["all_pass"]:
        st.success("🏛️ **UCITS COMPLIANT** — Toutes les contraintes sont satisfaites")
    else:
        st.warning("⚠️ Certaines contraintes UCITS ne sont pas respectées")
    
    constraint_items = [(k, v) for k, v in ucits.items() if isinstance(v, dict)]
    n_cols = len(constraint_items)
    col_ucits = st.columns(min(n_cols, 5))
    for i, (key, data) in enumerate(constraint_items):
        with col_ucits[i % len(col_ucits)]:
            icon = "✅" if data["pass"] else "❌"
            val_fmt = f"{data['value']*100:.1f}%" if isinstance(data['limit'], float) else f"{data['value']}"
            lim_fmt = f"{data['limit']*100:.0f}%" if isinstance(data['limit'], float) else f"≥{data['limit']}"
            st.markdown(f"{icon} **{key}**: {val_fmt} (limite: {lim_fmt})")
    
    st.divider()
    
    # ── Allocation Sunburst ──────────────────────────────────────────────
    col_sun, col_table = st.columns([1, 1])
    
    with col_sun:
        st.markdown("#### 🔆 Allocation par Cluster")
        
        sun_data = []
        for i, asset in enumerate(valid_assets):
            w = R["ucits_weights"][i]
            if w > 0.002:
                sun_data.append({
                    "name": asset["name"],
                    "cluster": asset.get("cluster", "Autre"),
                    "weight": w * 100,
                    "action": asset.get("action", "Maintien"),
                })
        
        sun_df = pd.DataFrame(sun_data)
        fig_sun = px.sunburst(
            sun_df, path=["cluster", "name"], values="weight",
            color="weight", color_continuous_scale="Emrld",
            title="Allocation BL-HRP UCITS",
        )
        fig_sun.update_layout(
            height=500, margin=dict(t=40, l=0, r=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
        )
        st.plotly_chart(fig_sun, use_container_width=True)
    
    with col_table:
        st.markdown("#### 📋 Top 20 Positions")
        
        sorted_idx = np.argsort(R["ucits_weights"])[::-1][:20]
        top_df = pd.DataFrame([{
            "Position": valid_assets[i]["name"],
            "Code fourni": valid_assets[i].get("symbol", valid_assets[i]["ticker"]),
        "Ticker": valid_assets[i]["ticker"],
            "Cluster": valid_assets[i].get("cluster", ""),
            "Poids": f"{R['ucits_weights'][i]*100:.2f}%",
            "Action": f"{ACTION_EMOJI.get(valid_assets[i]['action'],'')} {valid_assets[i]['action']}",
        } for i in sorted_idx])
        
        st.dataframe(top_df, use_container_width=True, hide_index=True, height=500)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: BACKTEST
# ─────────────────────────────────────────────────────────────────────────────

with tab2:
    
    # ── Performance Chart ────────────────────────────────────────────────
    st.markdown("#### 📈 Performance Cumulée")
    
    fig_perf = go.Figure()
    fig_perf.add_trace(go.Scatter(
        x=bt_ew["cum_returns"].index, y=bt_ew["cum_returns"].values,
        name="Équipondéré (Avant)", line=dict(color="#ff6b6b", width=1.5, dash="dot"),
    ))
    fig_perf.add_trace(go.Scatter(
        x=bt_hrp["cum_returns"].index, y=bt_hrp["cum_returns"].values,
        name="HRP Standard", line=dict(color="#ffd93d", width=1.5, dash="dash"),
    ))
    fig_perf.add_trace(go.Scatter(
        x=bt_hybrid["cum_returns"].index, y=bt_hybrid["cum_returns"].values,
        name="BL-HRP UCITS (Après)", line=dict(color="#00ff88", width=3),
    ))
    fig_perf.update_layout(
        height=450, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,10,26,0.8)",
        legend=dict(orientation="h", y=1.12),
        yaxis_title="Valeur (base 1)",
        hovermode="x unified",
    )
    st.plotly_chart(fig_perf, use_container_width=True)
    
    # ── Transaction Cost Summary ─────────────────────────────────────────
    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("Coût Ann. (frais de rebalancement)",
               f"{bt_hybrid['ann_cost']*100:.2f}%")
    tc2.metric("Turnover Moyen / Rebalancement",
               f"{bt_hybrid['avg_turnover']*100:.1f}%")
    tc3.metric("Nombre de Rebalancements",
               f"{bt_hybrid['n_rebalances']}")
    
    st.divider()
    
    # ── Drawdown Chart ───────────────────────────────────────────────────
    st.markdown("#### 📉 Drawdown")
    
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=bt_ew["drawdown"].index, y=bt_ew["drawdown"].values * 100,
        name="Équipondéré", fill="tozeroy",
        line=dict(color="#ff6b6b", width=0.5), fillcolor="rgba(255,107,107,0.2)",
    ))
    fig_dd.add_trace(go.Scatter(
        x=bt_hybrid["drawdown"].index, y=bt_hybrid["drawdown"].values * 100,
        name="BL-HRP UCITS", fill="tozeroy",
        line=dict(color="#00ff88", width=1), fillcolor="rgba(0,255,136,0.15)",
    ))
    fig_dd.update_layout(
        height=300, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,10,26,0.8)",
        yaxis_title="Drawdown (%)", legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig_dd, use_container_width=True)
    
    # ── Rolling Metrics ──────────────────────────────────────────────────
    col_rv, col_rs = st.columns(2)
    
    with col_rv:
        st.markdown("#### 🌊 Volatilité Glissante")
        fig_rv = go.Figure()
        fig_rv.add_trace(go.Scatter(
            x=bt_ew["rolling_vol"].index, y=bt_ew["rolling_vol"].values * 100,
            name="Équipondéré", line=dict(color="#ff6b6b", width=1),
        ))
        fig_rv.add_trace(go.Scatter(
            x=bt_hybrid["rolling_vol"].index, y=bt_hybrid["rolling_vol"].values * 100,
            name="BL-HRP", line=dict(color="#00ff88", width=2),
        ))
        fig_rv.update_layout(
            height=300, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,10,26,0.8)",
            yaxis_title="Vol Ann. (%)",
        )
        st.plotly_chart(fig_rv, use_container_width=True)
    
    with col_rs:
        st.markdown("#### ⚡ Sharpe Glissant")
        fig_rs = go.Figure()
        fig_rs.add_trace(go.Scatter(
            x=bt_ew["rolling_sharpe"].dropna().index,
            y=bt_ew["rolling_sharpe"].dropna().values,
            name="Équipondéré", line=dict(color="#ff6b6b", width=1),
        ))
        fig_rs.add_trace(go.Scatter(
            x=bt_hybrid["rolling_sharpe"].dropna().index,
            y=bt_hybrid["rolling_sharpe"].dropna().values,
            name="BL-HRP", line=dict(color="#00ff88", width=2),
        ))
        fig_rs.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig_rs.update_layout(
            height=300, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,10,26,0.8)",
            yaxis_title="Sharpe",
        )
        st.plotly_chart(fig_rs, use_container_width=True)
    
    # ── Monthly Returns Heatmap (FIX #10: proper month mapping) ──────────
    st.markdown("#### 📅 Rendements Mensuels (BL-HRP UCITS)")
    
    monthly = bt_hybrid["monthly_returns"]
    monthly_df = pd.DataFrame({
        "year": monthly.index.year,
        "month": monthly.index.month,
        "return": monthly.values * 100,
    })
    
    MONTH_NAMES = {
        1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Aoû", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Déc",
    }
    
    if len(monthly_df) > 0:
        pivot = monthly_df.pivot_table(index="year", columns="month", values="return", aggfunc="first")
        # FIX #10: Map actual month numbers to correct labels
        pivot.columns = [MONTH_NAMES.get(c, str(c)) for c in pivot.columns]
        
        fig_heat = px.imshow(
            pivot.values, x=pivot.columns.tolist(), y=[str(y) for y in pivot.index],
            color_continuous_scale="RdYlGn", aspect="auto",
            labels=dict(color="Return (%)"),
            text_auto=".1f",
        )
        fig_heat.update_layout(
            height=250, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_heat, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: AVANT / APRÈS
# ─────────────────────────────────────────────────────────────────────────────

with tab3:
    
    st.markdown("#### ⚖️ Comparaison Complète: Performance")
    comp_df = compare_backtests(bt_ew, bt_hrp, bt_hybrid)
    st.dataframe(comp_df, use_container_width=True, height=650)
    
    st.divider()
    st.markdown("#### 🎯 Comparaison: Concentration & Diversification")
    
    conc_rows = [
        ("HHI (Herfindahl)",       conc_ew["hhi"],         conc_hrp["hhi"],         conc_hybrid["hhi"]),
        ("Nb Effectif Positions",  conc_ew["enp"],         conc_hrp["enp"],         conc_hybrid["enp"]),
        ("HHI Cluster",            conc_ew["hhi_cluster"], conc_hrp["hhi_cluster"], conc_hybrid["hhi_cluster"]),
        ("Nb Effectif Clusters",   conc_ew["enp_cluster"], conc_hrp["enp_cluster"], conc_hybrid["enp_cluster"]),
        ("Ratio Diversification",  conc_ew["div_ratio"],   conc_hrp["div_ratio"],   conc_hybrid["div_ratio"]),
        ("Top 5 Concentration",    conc_ew["top5"],        conc_hrp["top5"],        conc_hybrid["top5"]),
        ("Top 10 Concentration",   conc_ew["top10"],       conc_hrp["top10"],       conc_hybrid["top10"]),
        ("Positions > 0.5%",       conc_ew["n_significant"],conc_hrp["n_significant"],conc_hybrid["n_significant"]),
    ]
    
    conc_df = pd.DataFrame(conc_rows, columns=["Métrique", "Équipondéré", "HRP Standard", "BL-HRP UCITS"])
    conc_df = conc_df.set_index("Métrique")
    
    for col in conc_df.columns:
        conc_df[col] = conc_df[col].apply(lambda x: f"{x:.4f}" if x < 1 else (f"{x:.2f}" if x < 50 else f"{x:.0f}"))
    
    st.dataframe(conc_df, use_container_width=True)
    
    st.divider()
    
    # ── Cluster Weight Comparison ────────────────────────────────────────
    st.markdown("#### 🏗️ Poids par Cluster — Avant vs Après")
    
    all_clusters = sorted(set(clusters_list))
    
    cw_ew = {c: sum(R["ew_weights"][i] for i, cl in enumerate(clusters_list) if cl == c) for c in all_clusters}
    cw_hy = {c: sum(R["ucits_weights"][i] for i, cl in enumerate(clusters_list) if cl == c) for c in all_clusters}
    
    sorted_cl = sorted(all_clusters, key=lambda x: cw_hy[x], reverse=True)
    
    fig_cl = go.Figure()
    fig_cl.add_trace(go.Bar(
        y=sorted_cl, x=[cw_ew[c]*100 for c in sorted_cl],
        name="Avant (EW)", orientation="h", marker_color="#ff6b6b", opacity=0.7,
    ))
    fig_cl.add_trace(go.Bar(
        y=sorted_cl, x=[cw_hy[c]*100 for c in sorted_cl],
        name="Après (BL-HRP)", orientation="h", marker_color="#00ff88", opacity=0.85,
    ))
    fig_cl.update_layout(
        barmode="group", height=max(400, len(sorted_cl)*28),
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10,10,26,0.8)",
        xaxis_title="Poids (%)", legend=dict(orientation="h", y=1.05),
    )
    st.plotly_chart(fig_cl, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: CLUSTERING
# ─────────────────────────────────────────────────────────────────────────────

with tab4:
    
    st.markdown("#### 🌳 Dendrogramme HRP (Matrice Black-Litterman)")
    st.caption("Les actifs proches dans l'arbre partagent du risque. HRP répartit le budget entre branches avant de répartir au sein de chaque branche.")
    
    fig_dend, ax_dend = plt.subplots(figsize=(16, 6))
    fig_dend.patch.set_facecolor("#0a0a1a")
    ax_dend.set_facecolor("#0a0a1a")
    
    short_names = [n[:22] for n in R["asset_names"]]
    dendrogram(
        R["linkage_bl"], labels=short_names, ax=ax_dend,
        leaf_rotation=90, leaf_font_size=7,
        color_threshold=0.7 * R["linkage_bl"][:, 2].max(),
        above_threshold_color="#00ff88",
    )
    ax_dend.tick_params(colors="#888", labelsize=7)
    for spine in ax_dend.spines.values():
        spine.set_color("#333")
    ax_dend.set_title("Dendrogramme — Clustering Ward sur Covariance BL", color="white", fontsize=12)
    
    st.pyplot(fig_dend)
    plt.close()
    
    st.divider()
    
    # ── Correlation Heatmap (inter-cluster) ──────────────────────────────
    st.markdown("#### 🔥 Corrélation Inter-Clusters")
    
    unique_cl = sorted(set(clusters_list))
    n_cl = len(unique_cl)
    cl_corr = np.zeros((n_cl, n_cl))
    
    for i, c1 in enumerate(unique_cl):
        for j, c2 in enumerate(unique_cl):
            idx1 = [k for k, cl in enumerate(clusters_list) if cl == c1]
            idx2 = [k for k, cl in enumerate(clusters_list) if cl == c2]
            sub_corr = R["corr_hist"][np.ix_(idx1, idx2)]
            cl_corr[i, j] = sub_corr.mean()
    
    fig_hm = px.imshow(
        cl_corr, x=unique_cl, y=unique_cl,
        color_continuous_scale="RdYlGn_r", aspect="auto",
        zmin=-0.3, zmax=1.0, text_auto=".2f",
    )
    fig_hm.update_layout(
        height=max(400, n_cl * 32), template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_tickangle=45,
    )
    st.plotly_chart(fig_hm, use_container_width=True)
    
    st.info("💡 Le modèle HRP détecte que les clusters fortement corrélés (ex: 'Indices US' et 'Tech US') "
            "forment une même famille de risque. Même si Google est en 'Achat Fort', son poids est plafonné "
            "car le cluster Tech + Indices US absorbe déjà beaucoup de budget de risque.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: RISQUE
# ─────────────────────────────────────────────────────────────────────────────

with tab5:
    
    # ── Build Risk Contribution DataFrame ────────────────────────────────
    st.markdown("#### 📊 Contribution Marginale au Risque par Position")
    
    rc_raw = conc_hybrid["risk_contrib_pct"]
    
    # Recompute risk contribution directly
    try:
        w_arr = R["ucits_weights"]
        cov_arr = R["cov_hist"]
        port_sigma = np.sqrt(float(w_arr @ cov_arr @ w_arr))
        if port_sigma > 1e-10:
            marginal_rc = (cov_arr @ w_arr) / port_sigma
            total_rc = w_arr * marginal_rc
            rc_pct = total_rc / total_rc.sum() if total_rc.sum() != 0 else total_rc
        else:
            rc_pct = w_arr.copy()
    except Exception:
        rc_pct = rc_raw
    
    rc_data = []
    for i in range(len(valid_assets)):
        wi = float(R["ucits_weights"][i])
        if wi > 0.001:
            rci = float(rc_pct[i]) * 100
            rc_data.append({
                "name": valid_assets[i]["name"],
                "short_name": valid_assets[i]["name"][:20],
                "cluster": valid_assets[i].get("cluster", "Autre"),
                "risk_contrib": rci,
                "risk_contrib_abs": abs(rci),
                "weight": wi * 100,
                "type": "Contributeur" if rci >= 0 else "Diversificateur",
            })
    
    rc_df = pd.DataFrame(rc_data)
    
    if rc_df.empty:
        st.warning("Pas de données de contribution au risque disponibles.")
    else:
        rc_df = rc_df.sort_values("risk_contrib", ascending=True)
        
        # ── PRIMARY: Horizontal Bar Chart (FIX #11: explicit colorscale) ─
        rc_min = rc_df["risk_contrib"].min()
        rc_max = rc_df["risk_contrib"].max()
        
        fig_rc_bar = go.Figure()
        fig_rc_bar.add_trace(go.Bar(
            y=rc_df["short_name"],
            x=rc_df["risk_contrib"],
            orientation="h",
            marker=dict(
                color=rc_df["risk_contrib"],
                colorscale="RdYlGn_r",
                cmin=rc_min,
                cmax=rc_max,
                cmid=0,   # FIX #11: anchor zero at the midpoint
                showscale=True,
                colorbar=dict(title="RC %", ticksuffix="%"),
            ),
            text=[f"{v:+.1f}%" for v in rc_df["risk_contrib"]],
            textposition="outside",
            textfont=dict(size=9),
            hovertemplate="<b>%{y}</b><br>Risk Contribution: %{x:.2f}%<extra></extra>",
        ))
        fig_rc_bar.add_vline(x=0, line_color="white", line_width=1, opacity=0.3)
        fig_rc_bar.update_layout(
            height=max(450, len(rc_df) * 18),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(10,10,26,0.8)",
            xaxis_title="Contribution au Risque (%)",
            title=dict(text="Contribution Marginale au Risque — BL-HRP UCITS", font=dict(size=14)),
            margin=dict(l=160, r=60, t=50, b=40),
            yaxis=dict(tickfont=dict(size=9)),
        )
        st.plotly_chart(fig_rc_bar, use_container_width=True)
        
        st.caption(
            "🔴 **Contributeurs** (barres vers la droite): ces positions ajoutent du risque au portefeuille. "
            "🟢 **Diversificateurs** (barres vers la gauche): ces positions réduisent le risque global grâce à leur faible corrélation."
        )
        
        st.divider()
        
        # ── TREEMAP with absolute values ─────────────────────────────────
        st.markdown("#### 🗺️ Carte de Risque par Cluster")
        
        rc_tree = rc_df[rc_df["risk_contrib_abs"] > 0.01].copy()
        
        if not rc_tree.empty:
            fig_tm = px.treemap(
                rc_tree,
                path=[px.Constant("Portefeuille"), "cluster", "name"],
                values="risk_contrib_abs",
                color="risk_contrib",
                color_continuous_scale="RdYlGn_r",
                color_continuous_midpoint=0,
                title="Budget de Risque par Cluster et Position",
                hover_data={"weight": ":.1f", "risk_contrib": ":.2f"},
            )
            fig_tm.update_layout(
                height=500,
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=50, l=10, r=10, b=10),
            )
            fig_tm.update_traces(
                textinfo="label+percent root",
                textfont=dict(size=11),
            )
            st.plotly_chart(fig_tm, use_container_width=True)
        
        st.divider()
        
        # ── Weight vs Risk Contribution Scatter ──────────────────────────
        st.markdown("#### ⚖️ Poids vs Contribution au Risque")
        
        fig_wr = go.Figure()
        fig_wr.add_trace(go.Scatter(
            x=rc_df["weight"],
            y=rc_df["risk_contrib"],
            mode="markers+text",
            text=rc_df["short_name"],
            textposition="top center",
            textfont=dict(size=8, color="#aaa"),
            marker=dict(
                size=rc_df["weight"] * 1.5 + 6,
                color=rc_df["risk_contrib"],
                colorscale="RdYlGn_r",
                cmid=0,  # FIX #11
                showscale=True,
                colorbar=dict(title="RC %"),
                line=dict(width=1, color="rgba(255,255,255,0.3)"),
            ),
            hovertemplate="<b>%{text}</b><br>Poids: %{x:.1f}%<br>Risk: %{y:.2f}%<extra></extra>",
        ))
        
        # 45-degree line
        axis_max = max(rc_df["weight"].max(), rc_df["risk_contrib"].max(), 1) * 1.1
        axis_min = min(0, rc_df["risk_contrib"].min()) * 1.1
        fig_wr.add_trace(go.Scatter(
            x=[0, axis_max], y=[0, axis_max], mode="lines",
            line=dict(color="rgba(255,255,255,0.2)", dash="dash", width=1),
            showlegend=False,
        ))
        fig_wr.add_hline(y=0, line_color="rgba(255,255,255,0.15)", line_width=1)
        
        fig_wr.add_annotation(
            x=axis_max * 0.8, y=axis_max * 0.3,
            text="📉 Surpondéré<br>mais peu risqué",
            showarrow=False, font=dict(size=9, color="#00ff88"), opacity=0.5,
        )
        fig_wr.add_annotation(
            x=axis_max * 0.3, y=axis_max * 0.8,
            text="⚠️ Forte contribution<br>au risque",
            showarrow=False, font=dict(size=9, color="#ff6b6b"), opacity=0.5,
        )
        
        fig_wr.update_layout(
            height=500, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,10,26,0.8)",
            xaxis_title="Poids dans le Portefeuille (%)",
            yaxis_title="Contribution au Risque (%)",
            xaxis=dict(range=[0, axis_max]),
            yaxis=dict(range=[axis_min, axis_max]),
        )
        st.plotly_chart(fig_wr, use_container_width=True)
        st.caption(
            "**Au-dessus** de la diagonale → l'actif contribue plus au risque que son poids le suggère. "
            "**En dessous** → diversificateur net. "
            "**Sous la ligne 0%** → réduit activement le risque (hedge)."
        )
    
    st.divider()
    
    # ── Risk Decomposition by Cluster ────────────────────────────────────
    st.markdown("#### 🏗️ Risque par Cluster: Poids vs Contribution")
    
    cluster_risk = {}
    for c in sorted(set(clusters_list)):
        idx = [j for j, cl in enumerate(clusters_list) if cl == c]
        cw = sum(R["ucits_weights"][j] for j in idx)
        cr = sum(float(rc_pct[j]) for j in idx) if len(rc_pct) > max(idx) else 0
        if cw > 0.005:
            cluster_risk[c] = {"weight": cw * 100, "risk": cr * 100}
    
    if cluster_risk:
        cl_risk_df = pd.DataFrame(cluster_risk).T.reset_index()
        cl_risk_df.columns = ["Cluster", "Poids (%)", "Risk Contrib (%)"]
        cl_risk_df = cl_risk_df.sort_values("Risk Contrib (%)", ascending=True)
        
        fig_clr = go.Figure()
        fig_clr.add_trace(go.Bar(
            y=cl_risk_df["Cluster"], x=cl_risk_df["Poids (%)"],
            name="Poids", orientation="h", marker_color="#4facfe", opacity=0.6,
        ))
        fig_clr.add_trace(go.Bar(
            y=cl_risk_df["Cluster"], x=cl_risk_df["Risk Contrib (%)"],
            name="Risk Contribution", orientation="h", marker_color="#ff6b6b", opacity=0.8,
        ))
        fig_clr.update_layout(
            barmode="group", height=max(350, len(cluster_risk) * 28),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,10,26,0.8)",
            xaxis_title="%", legend=dict(orientation="h", y=1.05),
            title="Poids vs Contribution au Risque par Cluster",
        )
        st.plotly_chart(fig_clr, use_container_width=True)
    
    st.divider()
    
    # ── VaR Analysis ─────────────────────────────────────────────────────
    st.markdown("#### 📉 Distribution des Rendements & VaR")
    
    col_v1, col_v2 = st.columns(2)
    
    with col_v1:
        ret_data = bt_hybrid["daily_returns"]
        
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=ret_data.values * 100, nbinsx=80,
            marker_color="#4facfe", opacity=0.7, name="Rendements",
        ))
        fig_hist.add_vline(x=bt_hybrid["var_95"]*100, line_color="#ff4757",
                          line_dash="dash", annotation_text=f"VaR 95%: {bt_hybrid['var_95']*100:.2f}%")
        fig_hist.add_vline(x=bt_hybrid["cvar_95"]*100, line_color="#ff0000",
                          line_dash="dot", annotation_text=f"CVaR 95%: {bt_hybrid['cvar_95']*100:.2f}%")
        fig_hist.update_layout(
            height=350, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,10,26,0.8)",
            xaxis_title="Rendement Journalier (%)", yaxis_title="Fréquence",
            title="Distribution BL-HRP UCITS",
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col_v2:
        st.markdown("##### 📐 Métriques de Queue")
        
        tail_data = {
            "Métrique": [
                "VaR 95% (jour)", "CVaR 95% (jour)",
                "VaR 99% (jour)", "CVaR 99% (jour)",
                "Skewness", "Kurtosis (excess)",
                "Win Rate", "Best Day", "Worst Day",
            ],
            "Valeur": [
                f"{bt_hybrid['var_95']*100:.3f}%",
                f"{bt_hybrid['cvar_95']*100:.3f}%",
                f"{bt_hybrid['var_99']*100:.3f}%",
                f"{bt_hybrid['cvar_99']*100:.3f}%",
                f"{bt_hybrid['skewness']:.3f}",
                f"{bt_hybrid['kurtosis']:.3f}",
                f"{bt_hybrid['win_rate']*100:.1f}%",
                f"{bt_hybrid['best_day']*100:.2f}%",
                f"{bt_hybrid['worst_day']*100:.2f}%",
            ],
        }
        st.dataframe(pd.DataFrame(tail_data).set_index("Métrique"),
                      use_container_width=True)
    
    st.divider()
    
    # ── BL Returns Comparison ────────────────────────────────────────────
    st.markdown("#### 🧠 Black-Litterman: Rendements Historiques vs Ajustés")
    
    bl_comp = pd.DataFrame({
        "Actif": R["asset_names"],
        "Historique (ann.)": R["mean_returns"] * 100,
        "Équilibre CAPM": R["equilibrium_returns"] * 100,
        "BL Ajusté": R["bl_returns"] * 100,
        "Delta BL": (R["bl_returns"] - R["mean_returns"]) * 100,
    })
    bl_comp["Action"] = [a.get("action", "Maintien") for a in valid_assets]
    bl_comp = bl_comp.sort_values("Delta BL", ascending=False)
    
    fig_bl = go.Figure()
    fig_bl.add_trace(go.Bar(
        y=bl_comp["Actif"][:20], x=bl_comp["Historique (ann.)"][:20],
        name="Historique", orientation="h", marker_color="#ff6b6b", opacity=0.6,
    ))
    fig_bl.add_trace(go.Bar(
        y=bl_comp["Actif"][:20], x=bl_comp["BL Ajusté"][:20],
        name="BL Ajusté", orientation="h", marker_color="#00ff88", opacity=0.8,
    ))
    fig_bl.update_layout(
        barmode="group", height=500, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,10,26,0.8)",
        xaxis_title="Rendement Annualisé (%)", legend=dict(orientation="h", y=1.05),
        title="Top 20 — Impact des Convictions sur les Rendements Attendus",
    )
    st.plotly_chart(fig_bl, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6: PARAMÈTRES & MÉTHODOLOGIE
# ─────────────────────────────────────────────────────────────────────────────

with tab6:
    
    st.markdown("#### ⚙️ Paramètres du Modèle")
    
    params_df = pd.DataFrame([
        {"Paramètre": "τ (tau)", "Valeur": f"{params['tau']}", "Description": "Incertitude sur l'équilibre CAPM"},
        {"Paramètre": "λ (risk aversion)", "Valeur": f"{params['risk_aversion']}", "Description": "Aversion au risque du marché"},
        {"Paramètre": "Ω scale", "Valeur": f"{params['omega_scale']}", "Description": "Confiance globale dans les vues (modulée par CONVICTION_CONFIDENCE)"},
        {"Paramètre": "α (BL tilt)", "Valeur": f"{params['bl_alpha']}", "Description": "Force du tilt conviction dans le hybrid"},
        {"Paramètre": "Clustering", "Valeur": params['linkage_method'], "Description": "Méthode de clustering hiérarchique"},
        {"Paramètre": "Max position", "Valeur": f"{params['max_single']*100:.0f}%", "Description": "UCITS: position max individuelle"},
        {"Paramètre": "Σ(>5%)", "Valeur": f"{params['max_sum_big']*100:.0f}%", "Description": "UCITS: somme des grosses positions"},
        {"Paramètre": "Max cash", "Valeur": f"{params['max_cash']*100:.0f}%", "Description": "Cash maximum autorisé"},
        {"Paramètre": "Max cluster", "Valeur": f"{params['max_cluster']*100:.0f}%", "Description": "Poids max par cluster (évite concentration sectorielle)"},
        {"Paramètre": "Rebalancement", "Valeur": f"{params['rebalance_days']} jours", "Description": "Fréquence de rebalancement"},
        {"Paramètre": "Taux sans risque", "Valeur": f"{params['risk_free_rate']*100:.1f}%", "Description": "Pour calcul du Sharpe"},
        {"Paramètre": "Coût transaction", "Valeur": f"{params['transaction_cost']*10000:.0f} bps", "Description": "Coût one-way par rebalancement"},
    ])
    st.dataframe(params_df, use_container_width=True, hide_index=True)
    
    st.divider()
    st.markdown("#### 📡 Qualité des Données")
    
    dq = st.session_state.dq
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Actifs Chargés", f"{dq['successfully_loaded']}/{dq['total_requested']}")
    c2.metric("Jours de Trading", dq["trading_days"])
    c3.metric("Période", dq["date_range"])
    c4.metric("NaN Moyen", dq["avg_nan_pct"])
    
    if st.session_state.failed:
        st.warning(f"⚠️ Tickers non chargés: {', '.join(st.session_state.failed)}")
    
    st.divider()
    st.markdown("#### 🧬 Pipeline Méthodologique")
    
    st.markdown("""
    ```
    ┌─────────────────────────────────────────────────────────────┐
    │  1. DONNÉES YAHOO FINANCE                                   │
    │     yfinance → prix ajustés → rendements quotidiens         │
    │     Clip ±30%, filtre multi-actif pour outliers             │
    └──────────────────────┬──────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────┐
    │  2. BLACK-LITTERMAN                                         │
    │     CAPM inversé → π (rendements équilibre)                │
    │     + Convictions (P, Q) avec confiance par vue (Ω)        │
    │     τ contrôle l'incertitude, Ω = f(action, conf)          │
    └──────────────────────┬──────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────┐
    │  3. HRP (sur matrice BL ajustée)                           │
    │     Distance de corrélation → Clustering Ward              │
    │     Quasi-diagonalisation → Bisection Récursive            │
    │     = parité de risque respectant la structure de clusters  │
    └──────────────────────┬──────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────┐
    │  4. TILT HYBRIDE                                           │
    │     w_hybrid = w_HRP × exp(α × z_combined)                 │
    │     z_combined = 0.6 × z_BL_vol_adj + 0.4 × conviction    │
    │     α contrôle la force des convictions dans l'allocation  │
    └──────────────────────┬──────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────┐
    │  5. CONTRAINTES UCITS (avec safety net)                     │
    │     Convergence itérative + hard-clip de sécurité:          │
    │     • Position max ≤ 10%                                   │
    │     • Σ(positions > 5%) ≤ 40%                              │
    │     • Cash ≤ 3%                                            │
    │     • Cluster max ≤ 20%                                    │
    └──────────────────────┬──────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────┐
    │  6. BACKTEST                                               │
    │     Simulation réaliste avec drift des poids               │
    │     Rebalancement périodique + coûts de transaction         │
    │     Métriques: Sharpe, Sortino, DD, VaR, Beta, HHI...     │
    └─────────────────────────────────────────────────────────────┘
    ```
    """)
    
    st.divider()
    st.markdown("#### 📋 Allocation Complète (Export)")
    
    full_alloc = pd.DataFrame([{
        "Position": valid_assets[i]["name"],
        "Code fourni": valid_assets[i].get("symbol", valid_assets[i]["ticker"]),
        "Ticker": valid_assets[i]["ticker"],
        "Cluster": valid_assets[i].get("cluster", ""),
        "Action": valid_assets[i].get("action", ""),
        "Confiance vue BL": valid_assets[i].get("confidence", CONVICTION_CONFIDENCE.get(valid_assets[i].get("action"), 0.30)),
        "Poids BL-HRP (%)": round(R["ucits_weights"][i] * 100, 3),
        "Poids EW (%)": round(R["ew_weights"][i] * 100, 3),
        "Poids HRP (%)": round(R["hrp_std_weights"][i] * 100, 3),
        "Rendement BL (%)": round(R["bl_returns"][i] * 100, 2),
        "Risk Contrib (%)": round(float(conc_hybrid["risk_contrib_pct"][i]) * 100, 3),
    } for i in range(len(valid_assets))])
    
    full_alloc = full_alloc.sort_values("Poids BL-HRP (%)", ascending=False)
    
    st.dataframe(full_alloc, use_container_width=True, hide_index=True, height=600)
    
    # Download button
    csv = full_alloc.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Télécharger CSV",
        csv,
        "bl_hrp_allocation.csv",
        "text/csv",
    )


# ═════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════

st.divider()
st.caption(
    "⚠️ **Disclaimer**: Ce modèle est un outil d'aide à la décision. "
    "Les performances passées ne préjugent pas des performances futures. "
    "Ce n'est pas un conseil en investissement."
)
st.caption(" Black-Litterman × HRP Engine v2.1 — Built with Streamlit & yfinance")