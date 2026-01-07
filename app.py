import streamlit as st

# ---------------------------------------------------------
# CONFIG STREAMLIT — DOIT ÊTRE EN PREMIER
# ---------------------------------------------------------
st.set_page_config(page_title="Quant Dashboard", layout="wide")

# ---------------------------------------------------------
# SIDEBAR (petit message, la navigation est gérée par /pages)
# ---------------------------------------------------------
st.sidebar.title("📊 Quant Dashboard")
st.sidebar.markdown("Navigation via les pages à gauche 👈")

# ---------------------------------------------------------
# PAGE ACCUEIL (contenu fusionné)
# ---------------------------------------------------------
st.title("🏠 Quant Dashboard — Projet Python & Finance")

st.markdown(
    """
Bienvenue 👋

Ce dashboard permet de **backtester des stratégies** sur un actif (Partie A) puis de passer à un **portefeuille multi-actifs** (Partie B).

---

## 🎯 Partie A — Single Asset
Fonctionnalités :
- Téléchargement des prix (Yahoo Finance via `yfinance`)
- Backtests : Buy & Hold, SMA, RSI, MACD, Bollinger, Golden Cross
- Courbes : prix + indicateurs, equity curve
- Statistiques : Sharpe, Sortino, volatilité annualisée, max drawdown

➡️ Va sur **“2_Single_Asset”** dans le menu à gauche.

---

## 🧩 Partie B — Portfolio (multi-actifs)
À venir :
- Sélection de plusieurs tickers
- Construction d’allocations (equal-weight / custom)
- Corrélation, covariance
- Equity curve du portefeuille + métriques

➡️ Va sur **“3_Portfolio”** quand prêt.

---

## ✅ Tips
- Si un graphique ne s’affiche pas : clique sur **Reset analyse**
- Les données sont rafraîchies (cache) toutes les **5 minutes**
"""
)
