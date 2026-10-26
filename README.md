# Nextwise — Black-Litterman × HRP

Application Streamlit d’allocation multi-actifs combinant les convictions Black-Litterman, la parité de risque hiérarchique (HRP), des contraintes UCITS et un backtest avec coûts de transaction.

## Lancement Windows par double-clic

Téléchargez le dépôt avec **Code → Download ZIP**, puis extrayez entièrement le ZIP. Ouvrez **Start Nextwise.bat** à la racine du dossier extrait. Avec Python 3.10+ installé et disponible dans le PATH, le lanceur crée l’environnement Python, installe les dépendances et lance Streamlit. Gardez sa fenêtre ouverte pendant l’utilisation. Ce lanceur doit être exécuté depuis le dossier complet ; le fichier `.bat` seul ne contient pas l’application.

## Démarrage rapide

Prérequis : **Python 3.10 ou supérieur** et un accès Internet pour les données Yahoo Finance.

Depuis la racine du dépôt :

```bash
python -m venv .venv
```

Activez l’environnement :

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Installez les dépendances et lancez le dashboard :

```bash
python -m pip install -r "nextwise - asset allocation/nextwise/requirements.txt"
cd "nextwise - asset allocation/nextwise"
python -m streamlit run app.py
```

## Documentation

- [Portefeuille et convictions](docs/portfolio.md) : les 23 actifs, correspondances Yahoo et validation en direct et hypothèses de confiance.

- [Guide utilisateur](docs/guide.md) : pipeline, onglets du dashboard, paramètres, convictions et personnalisation du portefeuille.
- [Code de l’application](nextwise%20-%20asset%20allocation/nextwise/) : dashboard, modèles, collecte des données et backtest.

## Organisation

```text
.
├── README.md
├── docs/
│   └── guide.md
└── nextwise - asset allocation/
    └── nextwise/
        ├── app.py             # Dashboard Streamlit
        ├── config.py          # Portefeuille, convictions et paramètres
        ├── data_loader.py     # Données Yahoo Finance et nettoyage
        ├── models.py          # Black-Litterman, HRP et contraintes
        ├── backtest.py        # Backtest et métriques de risque
        └── requirements.txt   # Dépendances Python
```

Les fichiers `__pycache__` présents dans l’import initial sont des fichiers Python générés et ne sont pas nécessaires au lancement.

## Limites

La disponibilité des cours dépend de Yahoo Finance et des tickers configurés. Les contrôles UCITS sont ceux du modèle ; ils ne remplacent pas une validation réglementaire indépendante.

Cet outil ne constitue pas un conseil en investissement. Les performances passées ne préjugent pas des performances futures.
