# ⚡ Black-Litterman × HRP — Hybrid Portfolio Optimizer

Modèle hybride d'allocation multi-asset combinant **Black-Litterman** (convictions investisseur) et **HRP** (parité de risque hiérarchique) avec contraintes **UCITS**.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)

---

## 🚀 Installation & Lancement

```bash
# Depuis la racine du dépôt (Python 3.10+)
python -m venv .venv

# Activer sous macOS / Linux
source .venv/bin/activate

# Sous Windows PowerShell, utiliser à la place :
# .\.venv\Scripts\Activate.ps1

# Installer les dépendances et lancer le dashboard
python -m pip install -r "nextwise - asset allocation/nextwise/requirements.txt"
cd "nextwise - asset allocation/nextwise"
python -m streamlit run app.py
```

L'application s'ouvrira dans votre navigateur à `http://localhost:8501`.

---

## 📁 Structure du Projet

```
nextwise - asset allocation/nextwise/
├── app.py              # Dashboard Streamlit principal (6 onglets)
├── config.py           # Définition du portefeuille, convictions, paramètres
├── data_loader.py      # Téléchargement Yahoo Finance + fallbacks
├── models.py           # Black-Litterman, HRP, Hybride, UCITS
├── backtest.py         # Moteur de backtest + métriques de risque
├── requirements.txt    # Dépendances Python
```

---

Le guide se trouve dans [`docs/guide.md`](guide.md). Les fichiers Python restent dans le dossier ci-dessus.

## 🧬 Pipeline

```
Yahoo Finance → Black-Litterman → HRP (sur cov BL) → Tilt Hybride → UCITS Filter → Backtest
```

### ① Black-Litterman
- Inverse le CAPM pour obtenir les rendements d'équilibre (Π)
- Intègre vos convictions (Achat Fort → +8%, Alléger → -4%) comme vues bayésiennes
- Produit des rendements et une covariance ajustés (µ_BL, Σ_BL)

### ② HRP (Hierarchical Risk Parity)
- Calcule la distance de corrélation sur la matrice **BL-ajustée**
- Clustering hiérarchique (Ward) pour grouper les actifs corrélés
- Bisection récursive pour allouer le budget de risque entre branches

### ③ Hybride
- `w_hybrid = w_HRP × exp(α × z_BL)` — tilt par z-scores des rendements BL
- α = 0 → pur HRP (aucune conviction), α = 1 → fort tilt

### ④ UCITS
- Position max ≤ 10%
- Σ(positions > 5%) ≤ 40%  (règle 5/10/40)
- Cash ≤ 3%
- Convergence itérative jusqu'à satisfaction de toutes les contraintes

---

## 📊 Dashboard (6 onglets)

| Onglet | Contenu |
|--------|---------|
| 📊 Résumé | KPIs, sunburst allocation, badge UCITS, top 20 positions |
| 📈 Backtest | Performance cumulée, drawdown, vol/sharpe glissants, rendements mensuels |
| ⚖️ Avant/Après | Tableau comparatif complet (20 métriques), HHI/diversification, poids par cluster |
| 🌳 Clustering | Dendrogramme HRP, heatmap corrélation inter-clusters |
| 🎯 Risque | Treemap risque, scatter poids vs contribution, VaR/CVaR, rendements BL |
| ⚙️ Paramètres | Paramètres du modèle, qualité données, pipeline, export CSV |

---

## ⚙️ Paramètres Ajustables (Sidebar)

Tous les paramètres sont modifiables en temps réel dans la sidebar:

- **τ (tau)**: Incertitude sur l'équilibre (0.01–0.20)
- **λ (risk aversion)**: Aversion au risque du marché (1.0–5.0)
- **Ω scale**: Confiance dans vos vues (0.1–2.0, plus bas = plus confiant)
- **α (BL tilt)**: Force des convictions dans l'allocation (0.0–1.0)
- **Clustering**: Ward, Complete, Average, Single
- **Contraintes UCITS**: Max position, Σ(>5%), cash max
- **Rebalancement**: Mensuel à Annuel
- **Lookback**: 1–5 ans d'historique

---

## 🔧 Personnalisation du Portefeuille

Modifiez [`config.py`](../nextwise%20-%20asset%20allocation/nextwise/config.py) pour ajuster:

```python
PORTFOLIO = [
    {
        "name": "Google (Alphabet)",   # Nom affiché
        "ticker": "GOOG",             # Ticker Yahoo Finance
        "action": "Achat Fort",       # Votre conviction
        "cluster": "Tech US",         # Groupe de risque
        "asset_class": "tech_mega",   # Classe d'actif
    },
    # ... ajoutez/retirez des positions
]
```

Actions disponibles: `Achat Fort`, `Conviction Forte`, `Achat`, `Renforcer`, `Maintien`, `Attente`, `Alléger`

---

## Données et accès réseau

Le dashboard télécharge les cours via Yahoo Finance (`yfinance`) et met les résultats en cache pendant une heure. Aucun fichier de données ni clé API n’est fourni dans ce dépôt. Le chargement nécessite un accès réseau à Yahoo Finance ; certains tickers utilisent les alternatives définies dans `TICKER_FALLBACKS` dans `config.py`.

## ⚠️ Disclaimer

Ce modèle est un outil d'aide à la décision et ne constitue pas un conseil en investissement.
Les performances passées ne préjugent pas des performances futures.
