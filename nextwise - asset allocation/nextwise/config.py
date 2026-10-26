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

PORTFOLIO = [
    # ── Obligations & Cash ────────────────────────────────────────────────
    {"name": "Vanguard USD Treasury Bond",  "ticker": "VUTY.L",   "action": "Achat Fort",       "cluster": "Obligations Souveraines", "asset_class": "bond_gov"},
    {"name": "Amundi Euro Gov Bond 1-3Y",   "ticker": "MTE.PA",   "action": "Maintien",         "cluster": "Obligations Souveraines", "asset_class": "bond_gov_short"},
    {"name": "Amundi Green Bond",           "ticker": "AGEB.PA",  "action": "Maintien",         "cluster": "Obligations Crédit",      "asset_class": "bond_corp"},
    {"name": "BNPP Corp 3-5",              "ticker": "CORP.PA",  "action": "Maintien",         "cluster": "Obligations Crédit",      "asset_class": "bond_corp"},

    # ── Métaux Précieux ───────────────────────────────────────────────────
    {"name": "iShares Physical Gold",       "ticker": "IGLN.L",   "action": "Renforcer",        "cluster": "Or",                      "asset_class": "gold"},
    {"name": "Amundi Physical Gold",        "ticker": "GOLD.PA",  "action": "Renforcer",        "cluster": "Or",                      "asset_class": "gold"},
    {"name": "Invesco Physical Gold",       "ticker": "PHAU.L",   "action": "Renforcer",        "cluster": "Or",                      "asset_class": "gold"},
    {"name": "WT Physical Silver",          "ticker": "PHAG.L",   "action": "Renforcer",        "cluster": "Métaux Précieux",         "asset_class": "silver"},
    {"name": "WT Physical Platinum",        "ticker": "PHPT.L",   "action": "Maintien",         "cluster": "Métaux Précieux",         "asset_class": "platinum"},

    # ── Métaux Industriels ────────────────────────────────────────────────
    {"name": "WT Copper (Cuivre)",          "ticker": "COPA.L",   "action": "Renforcer",        "cluster": "Métaux Industriels",      "asset_class": "copper"},
    {"name": "WT Industrial Metals",        "ticker": "AIGI.L",   "action": "Maintien",         "cluster": "Métaux Industriels",      "asset_class": "ind_metals"},

    # ── Défense & Aérospatiale ────────────────────────────────────────────
    {"name": "VanEck Defense ETF",          "ticker": "DFNS.L",   "action": "Conviction Forte", "cluster": "Défense & Aéro",          "asset_class": "defense"},
    {"name": "Dassault Aviation",           "ticker": "AM.PA",    "action": "Conviction Forte", "cluster": "Défense & Aéro",          "asset_class": "defense"},
    {"name": "Safran",                      "ticker": "SAF.PA",   "action": "Achat",            "cluster": "Défense & Aéro",          "asset_class": "defense"},
    {"name": "Airbus",                      "ticker": "AIR.PA",   "action": "Achat",            "cluster": "Défense & Aéro",          "asset_class": "aero"},
    {"name": "Leonardo",                    "ticker": "LDO.MI",   "action": "Achat",            "cluster": "Défense & Aéro",          "asset_class": "defense"},

    # ── Énergie ───────────────────────────────────────────────────────────
    {"name": "VanEck Uranium",              "ticker": "U3O8.L",   "action": "Achat Fort",       "cluster": "Énergie",                 "asset_class": "uranium"},
    {"name": "TotalEnergies",               "ticker": "TTE.PA",   "action": "Achat",            "cluster": "Énergie",                 "asset_class": "energy"},
    {"name": "Engie",                       "ticker": "ENGI.PA",  "action": "Maintien",         "cluster": "Énergie",                 "asset_class": "utility"},

    # ── Industrie & Infrastructure ────────────────────────────────────────
    {"name": "ArcelorMittal",               "ticker": "MT.AS",    "action": "Maintien",         "cluster": "Industrie Cyclique",      "asset_class": "steel"},
    {"name": "Prysmian",                    "ticker": "PRY.MI",   "action": "Conviction Forte", "cluster": "Industrie Infra",          "asset_class": "industrial"},
    {"name": "Vinci",                       "ticker": "DG.PA",    "action": "Maintien",         "cluster": "Industrie Infra",          "asset_class": "construction"},
    {"name": "Michelin",                    "ticker": "ML.PA",    "action": "Achat",            "cluster": "Industrie Cyclique",      "asset_class": "auto_parts"},

    # ── Tech & Growth ─────────────────────────────────────────────────────
    {"name": "Amundi S&P 500",              "ticker": "500.PA",   "action": "Alléger",          "cluster": "Indices US",              "asset_class": "sp500"},
    {"name": "Amundi Nasdaq 100",           "ticker": "ANX.PA",   "action": "Alléger",          "cluster": "Indices US",              "asset_class": "nasdaq"},
    {"name": "Google (Alphabet)",           "ticker": "GOOG",     "action": "Achat Fort",       "cluster": "Tech US",                 "asset_class": "tech_mega"},
    {"name": "Schneider Electric",          "ticker": "SU.PA",    "action": "Alléger",          "cluster": "Tech Europe",             "asset_class": "tech_eu"},
    {"name": "Air Liquide",                 "ticker": "AI.PA",    "action": "Maintien",         "cluster": "Tech Europe",             "asset_class": "industrial_quality"},
    {"name": "ASML Holding",                "ticker": "ASML.AS",  "action": "Alléger",          "cluster": "Semi-conducteurs",        "asset_class": "semicon"},
    {"name": "Dassault Systèmes",           "ticker": "DSY.PA",   "action": "Maintien",         "cluster": "Tech Europe",             "asset_class": "software_eu"},
    {"name": "iShares Taiwan",              "ticker": "EWT",      "action": "Renforcer",        "cluster": "Semi-conducteurs",        "asset_class": "semicon_asia"},
    {"name": "Amundi Russell 2000",         "ticker": "RS2K.PA",  "action": "Maintien",         "cluster": "Small Caps US",           "asset_class": "small_us"},
    {"name": "Equasens",                    "ticker": "EQS.PA",   "action": "Achat",            "cluster": "Small Caps EU",           "asset_class": "small_eu"},

    # ── Financières ───────────────────────────────────────────────────────
    {"name": "Amundi MSCI Financials",      "ticker": "CV9.PA",   "action": "Achat",            "cluster": "Financières",             "asset_class": "financials"},
    {"name": "BNP Paribas",                 "ticker": "BNP.PA",   "action": "Achat",            "cluster": "Financières",             "asset_class": "bank_eu"},

    # ── Immobilier ────────────────────────────────────────────────────────
    {"name": "Merlin Properties",           "ticker": "MRL.MC",   "action": "Renforcer",        "cluster": "Immobilier",              "asset_class": "reit"},
    {"name": "Warehouse Estates",           "ticker": "WEB.BR",   "action": "Renforcer",        "cluster": "Immobilier",              "asset_class": "reit"},
    {"name": "Cairn Homes",                 "ticker": "CRN.L",    "action": "Renforcer",        "cluster": "Immobilier",              "asset_class": "homebuilder"},
    {"name": "Glenveagh Properties",        "ticker": "GLV.L",    "action": "Renforcer",        "cluster": "Immobilier",              "asset_class": "homebuilder"},
    {"name": "Unibail-Rodamco",             "ticker": "URW.PA",   "action": "Renforcer",        "cluster": "Immobilier",              "asset_class": "reit_prime"},
    {"name": "Saint-Gobain",                "ticker": "SGO.PA",   "action": "Alléger",          "cluster": "Construction",            "asset_class": "construction"},

    # ── Émergents & Diversification ───────────────────────────────────────
    {"name": "Amundi MSCI Korea",           "ticker": "KRW.PA",   "action": "Alléger",          "cluster": "Émergents Asie",          "asset_class": "em_korea"},
    {"name": "Amundi MSCI Brazil",          "ticker": "BRZ.PA",   "action": "Alléger",          "cluster": "Émergents LATAM",         "asset_class": "em_brazil"},
    {"name": "Orange",                      "ticker": "ORA.PA",   "action": "Maintien",         "cluster": "Telecom & Conso",         "asset_class": "telecom"},
    {"name": "Accor",                       "ticker": "AC.PA",    "action": "Maintien",         "cluster": "Telecom & Conso",         "asset_class": "hospitality"},
    {"name": "Ahold Delhaize",              "ticker": "AD.AS",    "action": "Maintien",         "cluster": "Telecom & Conso",         "asset_class": "consumer_staple"},
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

TICKER_FALLBACKS = {
    "VUTY.L":  ["VGIT",   "GOVT"],
    "MTE.PA":  ["IBGS.L", "SEGA.PA"],
    "AGEB.PA": ["CB6.PA", "VAGF.L"],
    "CORP.PA": ["C35.PA", "IEAC.L"],
    "PHPT.L":  ["PPLT",   "PHPD.L"],
    "COPA.L":  ["CPER",   "JJC"],
    "AIGI.L":  ["DBB",    "JJM"],
    "DFNS.L":  ["ITA",    "PPA"],
    "U3O8.L":  ["URA",    "URNM"],
    "CV9.PA":  ["XLF",    "IXG"],
    "RS2K.PA": ["IWM",    "VTWO"],
    "KRW.PA":  ["EWY",    "FLKR"],
    "BRZ.PA":  ["EWZ",    "EWZS"],
    "GLV.L":   ["CRN.L",  "IPQ.L"],
    "WEB.BR":  ["URW.PA", "IMMO.AS"],
}