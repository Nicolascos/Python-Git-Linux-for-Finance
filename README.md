# Python-Git-Linux-for-Finance

quant--dashboard/
│
├── app.py                    # le point d’entrée Streamlit, très léger
│
├── modules/
│   ├── data_loader.py        # récupération API / web scraping, rafraîchissement
│   ├── strategy_single.py    # stratégies du Quant A
│   ├── portfolio_tools.py    # outils du Quant B
│   ├── metrics.py            # Sharpe, max drawdown, volatility, etc.
│   ├── plots.py              # fonctions plotly centralisées
│   └── utils.py              # fonctions génériques
│
├── cron/
│   ├── daily_report.py       # script lancé à 20h pour rapport quant A/B
│   └── crontab.txt           # config cron documentée
│
├── .streamlit/
│   ├── secrets.toml
│   └── config.toml
│
├── requirements.txt
├── README.md
└── LICENSE (optionnel)

