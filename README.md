# Quant Dashboard — Python / Git / Linux for Finance

Dashboard **Streamlit** orienté *quant/finance* pour :
- analyser un **actif unique** (actions/indices/crypto) ;
- construire et backtester un **portfolio multi-actifs** ;
- comparer plusieurs **stratégies** simples (SMA, RSI, MACD, Bollinger, Golden Cross, Buy & Hold) ;
- générer des **prédictions** (modèles simples + intervalles d’incertitude) ;
- produire un **rapport journalier** via un script `cron/`.

> Le projet utilise principalement **yfinance** pour les prix historiques et Streamlit pour l’interface.

---

## Aperçu des fonctionnalités

### Page 1 — Accueil (`app.py`)
- Présentation du projet, des pages, et des modules.

### Page 2 — Actif unique (`pages/2_Single_Asset.py`)
- Choix ticker (actions US, indices, crypto)
- Prix « live » (dernier prix connu via yfinance)
- Téléchargement et affichage de données historiques (OHLC)
- Application d’une stratégie au choix :
  - Buy & Hold
  - SMA (moyennes mobiles)
  - RSI
  - MACD
  - Bollinger Bands
  - Golden Cross
- Comparaison **Stratégie vs Buy & Hold**
- Tableau de métriques (Sharpe, Sortino, Volatilité annualisée, Max Drawdown)
- Comparaison **multi-stratégies** + tableau de synthèse
- Module “AI reco” : recherche de **meilleurs paramètres** (optimisation simple, ex. maximiser Sortino)

### Page 3 — Portfolio (`pages/3_Portfolio.py`)
- Création d’un portefeuille (montant par ticker, fusion des doublons, égal-pondération possible)
- Construction d’un « pseudo-actif » portfolio (série Close = valeur du portefeuille)
- Fenêtre globale + **segments non chevauchants** (périodes d’entrée/sortie)
- Backtest **Buy & Hold portfolio** vs stratégies sélectionnées
- Graphiques d’équity “gated/segmentée” + métriques (Sharpe/Sortino/Vol/MaxDD/Perf)

### Cron — Rapport journalier (`cron/daily_report.py`)
- Génère un rapport texte par ticker (dans `cron/data/`)
- Exemple de planification dans `cron/crontab.txt`

---

## Structure du dépôt

```
Python-Git-Linux-for-Finance/
├── app.py                          # Page d'accueil Streamlit
├── pages/
│   ├── 2_Single_Asset.py           # Analyse actif unique
│   └── 3_Portfolio.py              # Analyse portefeuille
├── modules/
│   ├── data_loader.py              # Chargement prix (yfinance) + cache streamlit
│   ├── preprocessing.py            # Nettoyage/slicing dates, equity “gated”
│   ├── strategy_single.py          # Stratégies + métriques (Sharpe/Sortino/…)
│   ├── plots.py                    # Graphiques plotly pour équity/segments
│   ├── prediction.py               # Prédictions pour actif unique (RF/linéaire + CI)
│   ├── portfolio.py                # Construction portfolio + segments
│   ├── predictions_portfolio.py    # Prédictions adaptées au portfolio
│   └── ai_reco.py                  # Reco paramètres (grid simple, ex. Sortino)
├── .streamlit/
│   ├── config.toml                 # Theme + server.runOnSave
│   └── secrets.toml                # ⚠️ secrets (à ne pas committer)
├── cron/
│   ├── daily_report.py             # Script de rapport pour cron
│   ├── crontab.txt                 # Exemple de crontab
│   └── data/                       # Rapports générés (exemples)
├── requirements.txt                # Dépendances runtime (nettoyées)
└── requirements-dev.txt            # Outils dev (optionnels)
```

---

## Installation (local)

### Prérequis
- Python **3.10+** recommandé
- pip récent

### 1) Créer un environnement virtuel

```bash
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate         # Windows PowerShell
python -m pip install -U pip
```

### 2) Installer les dépendances

```bash
pip install -r requirements.txt
```

Optionnel (dev) :

```bash
pip install -r requirements-dev.txt
```

---

## Lancer l’application

À la racine du projet :

```bash
streamlit run app.py
```

Streamlit détectera automatiquement les pages dans `pages/`.

---

## Configuration & secrets

### ⚠️ `secrets.toml`
Le fichier `.streamlit/secrets.toml` contient une clé `FINNHUB_API_KEY`.

- **Recommandation :** ne **jamais** versionner ce fichier dans Git.
- Ajoutez au `.gitignore` (si pas déjà fait) :

```gitignore
.streamlit/secrets.toml
```

> Note : dans l’état actuel du code, l’API Finnhub n’est pas utilisée (yfinance est la source principale).  
> Si vous n’utilisez pas Finnhub, vous pouvez supprimer la clé.

---

## Utilisation (workflow typique)

### Actif unique
1. Choisir un ticker (ex. `AAPL`, `^GSPC`, `BTC-USD`)
2. Sélectionner une période (dates)
3. Choisir une stratégie + paramètres
4. Lire la perf, les métriques, comparer plusieurs stratégies
5. Tester les prédictions (modèle linéaire / random forest)

### Portfolio
1. Ajouter 2+ tickers et un montant (€) par ticker
2. Générer la série portfolio
3. Définir une fenêtre globale + segments
4. Comparer Buy & Hold vs stratégies

---

## Rapport journalier (cron)

Lancer manuellement :

```bash
python cron/daily_report.py
```

Résultats : fichiers texte dans `cron/data/` (un par ticker et par jour).

Planification (exemple) : voir `cron/crontab.txt`.

---

## Notes techniques (ce que font les modules)

- `modules/data_loader.py`
  - `get_live_price()` : récupère le dernier prix via yfinance
  - `get_history()` / `load_historical_data()` : OHLC + cache Streamlit
- `modules/preprocessing.py`
  - normalisation/dédoublonnage dates
  - slicing par fenêtre
  - construction d’équity “gated” (afficher uniquement sur segments)
- `modules/strategy_single.py`
  - stratégies (SMA/RSI/MACD/Bollinger/GoldenCross/B&H)
  - `compute_metrics()` : Sharpe, Sortino, Vol ann., MaxDD
- `modules/prediction.py` et `modules/predictions_portfolio.py`
  - feature engineering simple
  - split temporel
  - modèles : linéaire + RF
  - simulation/rollout + bandes d’incertitude
- `modules/plots.py`
  - graphes plotly pour equity segmentée
- `modules/ai_reco.py`
  - recherche simple (grid) des paramètres maximisant le Sortino

---

## Dépannage

- **yfinance renvoie des données vides**
  - vérifier le ticker
  - tester une autre période
  - relancer (limitations réseau / rate limits)
- **erreurs de dates**
  - vérifier que vos segments sont **non chevauchants**
  - vérifier que la fenêtre globale contient les segments
- **Streamlit ne voit pas les pages**
  - garder `pages/` à la racine du projet
  - nommage des fichiers `pages/2_*.py`, `pages/3_*.py` etc.

---

## Sécurité / hygiène repo (recommandé)
- Ne pas committer :
  - `.streamlit/secrets.toml`
  - `.venv/`
  - `cron/data/` si c’est du bruit (ou le garder mais en l’assumant)
- Éviter de versionner `.git/` dans une archive/zip si l’objectif est le partage.

---

## Licence
À définir (MIT / Apache-2.0 / …) selon votre usage.

