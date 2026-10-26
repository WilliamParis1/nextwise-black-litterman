"""
=============================================================================
  config.py — Portfolio Definition & Model Parameters
=============================================================================
  
  CHANGES (v2.1):
    • No structural changes — this file was already correct.
    • Added docstring clarification that CONVICTION_CONFIDENCE is now
      actively used in models.py (previously dead code).
=============================================================================
"""

# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO POSITIONS
# Each entry: name, Yahoo ticker, conviction action, cluster, asset class
# ─────────────────────────────────────────────────────────────────────────────

# Exchange-qualified Yahoo mappings checked against live Yahoo history.
# See docs/portfolio.md for the assumptions and confidence rationale.
PORTFOLIO = [
    {'name': 'Adyen', 'symbol': 'ADYEN', 'ticker': 'ADYEN.AS', 'action': 'Maintien', 'confidence': 0.4, 'cluster': 'Paiements', 'asset_class': 'payments'},
    {'name': 'ASM International', 'symbol': 'ASM', 'ticker': 'ASM.AS', 'action': 'Maintien', 'confidence': 0.4, 'cluster': 'Semi-conducteurs', 'asset_class': 'semicon'},
    {'name': 'ASML Holding', 'symbol': 'ASML', 'ticker': 'ASML.AS', 'action': 'Renforcer', 'confidence': 0.55, 'cluster': 'Semi-conducteurs', 'asset_class': 'semicon'},
    {'name': 'Carel Industries', 'symbol': 'CRL', 'ticker': 'CRL.MI', 'action': 'Maintien', 'confidence': 0.4, 'cluster': 'Industrie & efficacité', 'asset_class': 'industrial'},
    {'name': 'Dassault Aviation', 'symbol': 'AM', 'ticker': 'AM.PA', 'action': 'Renforcer', 'confidence': 0.5, 'cluster': 'Défense & Aéro', 'asset_class': 'defense'},
    {'name': 'Eramet', 'symbol': 'ERA', 'ticker': 'ERA.PA', 'action': 'Attente', 'confidence': 0.3, 'cluster': 'Matières premières', 'asset_class': 'mining'},
    {'name': 'Franklin Future of Health and Wellness UCITS ETF', 'symbol': 'FOHW', 'ticker': 'FOHW.PA', 'action': 'Maintien', 'confidence': 0.2, 'cluster': 'Santé', 'asset_class': 'healthcare_equity'},
    {'name': 'Glanbia PLC', 'symbol': 'GL9', 'ticker': 'GL9.IR', 'action': 'Maintien', 'confidence': 0.4, 'cluster': 'Nutrition', 'asset_class': 'nutrition'},
    {'name': 'iShares Agribusiness UCITS ETF USD (Acc)', 'symbol': 'ISAE', 'ticker': 'ISAE.AS', 'action': 'Maintien', 'confidence': 0.4, 'cluster': 'Agribusiness', 'asset_class': 'agribusiness'},
    {'name': 'iShares MSCI Taiwan UCITS ETF', 'symbol': 'ITWN', 'ticker': 'ITWN.AS', 'action': 'Attente', 'confidence': 0.35, 'cluster': 'Semi-conducteurs', 'asset_class': 'taiwan_equity'},
    {'name': 'L&G Battery Value-Chain UCITS ETF', 'symbol': 'BATT', 'ticker': 'BATT.L', 'action': 'Attente', 'confidence': 0.3, 'cluster': 'Batteries', 'asset_class': 'battery_equity'},
    {'name': 'Legrand', 'symbol': 'LR', 'ticker': 'LR.PA', 'action': 'Renforcer', 'confidence': 0.55, 'cluster': 'Électrification', 'asset_class': 'electrification'},
    {'name': 'Leonardo', 'symbol': 'LDO', 'ticker': 'LDO.MI', 'action': 'Renforcer', 'confidence': 0.5, 'cluster': 'Défense & Aéro', 'asset_class': 'defense'},
    {'name': 'Leverage Shares 3x Apple ETP', 'symbol': '3AAP', 'ticker': '3AAP.MI', 'action': 'Alléger', 'confidence': 0.6, 'cluster': 'Technologie à levier', 'asset_class': 'leveraged_equity'},
    {'name': 'iShares MSCI World Health Care Sector Advanced UCITS ETF USD Acc', 'symbol': 'WHCA', 'ticker': 'WHCA.L', 'action': 'Renforcer', 'confidence': 0.5, 'cluster': 'Santé', 'asset_class': 'healthcare_equity'},
    {'name': 'Nexans', 'symbol': 'NEX', 'ticker': 'NEX.PA', 'action': 'Renforcer', 'confidence': 0.5, 'cluster': 'Électrification', 'asset_class': 'electrification'},
    {'name': 'Prysmian', 'symbol': 'PRY', 'ticker': 'PRY.MI', 'action': 'Renforcer', 'confidence': 0.55, 'cluster': 'Électrification', 'asset_class': 'electrification'},
    {'name': 'Schneider Electric', 'symbol': 'SU', 'ticker': 'SU.PA', 'action': 'Renforcer', 'confidence': 0.55, 'cluster': 'Électrification', 'asset_class': 'electrification'},
    {'name': 'SPDR MSCI World Consumer Staples UCITS ETF', 'symbol': 'WCOS', 'ticker': 'WCOS.AS', 'action': 'Renforcer', 'confidence': 0.5, 'cluster': 'Consommation de base', 'asset_class': 'consumer_staples_equity'},
    {'name': 'SPIE', 'symbol': 'SPIE', 'ticker': 'SPIE.PA', 'action': 'Renforcer', 'confidence': 0.5, 'cluster': 'Services industriels', 'asset_class': 'industrial_services'},
    {'name': 'Technip Energies', 'symbol': 'TE', 'ticker': 'TE.PA', 'action': 'Maintien', 'confidence': 0.4, 'cluster': 'Énergie & ingénierie', 'asset_class': 'energy_engineering'},
    {'name': 'Thales', 'symbol': 'HO', 'ticker': 'HO.PA', 'action': 'Renforcer', 'confidence': 0.55, 'cluster': 'Défense & Aéro', 'asset_class': 'defense'},
    {'name': 'VanEck Uranium and Nuclear Technologies UCITS ETF', 'symbol': 'NUCL', 'ticker': 'NUCL.PA', 'action': 'Attente', 'confidence': 0.3, 'cluster': 'Nucléaire', 'asset_class': 'nuclear_equity'},
]


# ─────────────────────────────────────────────────────────────────────────────
# CONVICTION MAPPINGS  (Action → BL view excess return & confidence)
#
# CONVICTION_EXCESS: excess return added to CAPM equilibrium for each view
# CONVICTION_CONFIDENCE: used to scale Omega per-view in BL model
#   High confidence → small Omega → BL posterior pulled closer to the view
#   Low confidence  → large Omega → BL posterior stays near equilibrium
# ─────────────────────────────────────────────────────────────────────────────

CONVICTION_EXCESS = {
    "Achat Fort":        0.08,   # Strong buy  → +8% excess
    "Conviction Forte":  0.07,   # High conviction → +7%
    "Achat":             0.04,   # Buy → +4%
    "Renforcer":         0.03,   # Increase → +3%
    "Maintien":          0.00,   # Hold → neutral
    "Attente":          -0.01,   # Wait → slight drag
    "Alléger":          -0.04,   # Reduce → -4%
}

CONVICTION_CONFIDENCE = {
    "Achat Fort":        0.85,
    "Conviction Forte":  0.90,
    "Achat":             0.65,
    "Renforcer":         0.55,
    "Maintien":          0.30,
    "Attente":           0.20,
    "Alléger":           0.65,
}

ACTION_COLORS = {
    "Achat Fort":        "#00ff88",
    "Conviction Forte":  "#00cc66",
    "Achat":             "#66ddaa",
    "Renforcer":         "#88ccff",
    "Maintien":          "#aaaacc",
    "Attente":           "#888888",
    "Alléger":           "#ff6b6b",
}

ACTION_EMOJI = {
    "Achat Fort":        "✨",
    "Conviction Forte":  "🔒",
    "Achat":             "✨",
    "Renforcer":         "🟢",
    "Maintien":          "🔒",
    "Attente":           "🟡",
    "Alléger":           "↘️",
}


# ─────────────────────────────────────────────────────────────────────────────
# MODEL PARAMETERS (defaults, adjustable in Streamlit sidebar)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_PARAMS = {
    # Black-Litterman
    "tau":              0.05,       # Uncertainty on equilibrium
    "risk_aversion":    2.5,        # Lambda (market risk aversion)
    "omega_scale":      0.50,       # View confidence scale (lower = more confident)

    # Hybrid blend
    "bl_alpha":         0.50,       # BL tilt strength (0=pure HRP, 1=aggressive conviction tilt)

    # HRP
    "linkage_method":   "ward",     # Clustering method: ward, single, complete, average

    # UCITS Constraints
    "max_single":       0.10,       # Max 10% per position
    "max_sum_big":      0.40,       # Sum of positions >5% must be ≤40%
    "max_cash":         0.03,       # Cash ≤ 3%
    "max_cluster":      0.20,       # Max 20% per cluster

    # Backtest
    "lookback_years":   3,          # Years of history
    "rebalance_days":   63,         # Rebalance frequency (~quarterly)
    "risk_free_rate":   0.03,       # For Sharpe calculation
    "transaction_cost": 0.001,      # 10bps one-way cost per rebalance (NEW)

    # Data
    "benchmark_ticker": "^STOXX50E", # EURO STOXX 50 as benchmark
}


# ─────────────────────────────────────────────────────────────────────────────
# TICKER FALLBACKS (if Yahoo doesn't recognize a ticker, try alternatives)
# ─────────────────────────────────────────────────────────────────────────────

# Do not substitute different instruments when a requested asset is unavailable.
TICKER_FALLBACKS = {}
