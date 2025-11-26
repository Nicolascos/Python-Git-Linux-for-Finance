# Python-Git-Linux-for-Finance

quant--dashboard/
│
├── app.py                         # Point d'entrée Streamlit
│
├── modules/
│   ├── finnhub_api.py             # API Finnhub
│   ├── portfolio.py               # Calculs quantitatifs du portefeuille
│   ├── indicators.py              # Indicateurs (RSI, MACD, ATR…)
│   ├── utils.py                   # Fonctions utilitaires (dates, cache…)
│
├── data/
│   └── assets.json                # Liste des tickers suivis
│
├── pages/
│   ├── 1_Accueil.py
│   ├── 2_Single_Asset.py
│   ├── 3_Portfolio.py
│   └── 4_Taux_France.py           # OU laisser dans app.py, c’est au choix
│
├── Importation_data.py            # Scraping Boursorama → peut aller dans modules/
│
├── requirements.txt
├── .streamlit/
│   ├── secrets.toml               # Clé API (cloud)
│   └── config.toml                # Customisation interface Streamlit
│
└── README.md
