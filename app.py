import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------
# CONFIG STREAMLIT — DOIT ÊTRE EN PREMIER
# ---------------------------------------------------------
st.set_page_config(page_title="Quant Dashboard", layout="wide")

# ---------------------------------------------------------
# CHARGEMENT DE LA CLÉ API FINNHUB (SECRETS)
# ---------------------------------------------------------
try:
    API_KEY = st.secrets["FINNHUB_API_KEY"]

except KeyError:
    st.error(
        """
        ❌ Clé API Finnhub manquante.

        ➜ Va dans *Streamlit Cloud* → *Settings* → *Secrets*  
        et ajoute par exemple :

        FINNHUB_API_KEY = "ta_clé_api_finnhub"
        """
    )
    API_KEY = None

except Exception as e:
    st.error(f"Erreur inattendue lors du chargement de la clé API Finnhub : {e}")
    API_KEY = None

# ---------------------------------------------------------
# IMPORT DES MODULES
# ---------------------------------------------------------
from modules.data_loader import get_live_price, get_history
from modules.strategy_single import (
    strategy_buy_and_hold,
    strategy_sma,
    compute_metrics
)
from modules.plots import plot_price_with_indicators, plot_equity

# ---------------------------------------------------------
# SIDEBAR — NAVIGATION
# ---------------------------------------------------------
st.sidebar.title("📊 Quant Dashboard")
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Accueil", "📈 Single Asset", "📊 Portfolio (bientôt)"]
)

# =========================================================
# PAGE 1 — ACCUEIL
# =========================================================
if page == "🏠 Accueil":
    st.title("🏠 Quant Dashboard — Projet Python & Finance")

    st.markdown(
        """
        Ce projet a pour objectif de construire une **plateforme de backtest quantitatif**
        à partir de **données de marché récupérées via API (Finnhub)**.

        ### 🎯 Partie A — Single Asset
        - Récupération des données historiques d’un actif (ex : AAPL)
        - Implémentation de stratégies simples :
            - Buy & Hold
            - SMA (moyennes mobiles courte / longue)
        - Backtest de la stratégie sur l’historique
        - Visualisation :
            - Prix + indicateurs techniques
            - Courbe de valeur du portefeuille
        - Indicateurs de performance :
            - Sharpe Ratio
            - Volatilité annualisée
            - Max Drawdown

        ### 📌 Partie B — Portfolio (à venir)
        - Extension à un portefeuille multi-actifs
        - Corrélations, diversification, allocation

        ➜ Utilise le menu à gauche pour lancer l’analyse Single Asset.
        """
    )

# =========================================================
# PAGE 2 — SINGLE ASSET (QUANT A)
# =========================================================
elif page == "📈 Single Asset":

    st.title("📈 Analyse d’un Actif Unique — Quant A")

    if API_KEY is None:
        st.warning("⚠️ La clé API Finnhub n’est pas configurée. Va dans les *Secrets* Streamlit.")
        st.stop()

    # ------------------------------
    # Sidebar paramètres
    # ------------------------------
    st.sidebar.subheader("⚙️ Paramètres de l’analyse")

    symbol = st.sidebar.text_input("Ticker :", "AAPL")

    strategy_choice = st.sidebar.selectbox(
        "Stratégie :",
        ["Buy & Hold", "SMA Momentum"]
    )

    if strategy_choice == "SMA Momentum":
        short = st.sidebar.number_input("SMA courte (jours) :", 5, 100, 20)
        long = st.sidebar.number_input("SMA longue (jours) :", 20, 300, 50)

    lookback = st.sidebar.slider(
        "Nombre de points historiques (bougies journalières)",
        min_value=100,
        max_value=1500,
        value=365,
        step=10
    )

    if st.sidebar.button("🚀 Lancer l’analyse"):
        st.session_state["run_single"] = True

    if "run_single" not in st.session_state:
        st.info("Configure les paramètres dans la colonne de gauche, puis clique sur **🚀 Lancer l’analyse**.")
        st.stop()

    # ------------------------------
    # 1. Chargement des données
    # ------------------------------
    st.subheader("📡 Données historiques")

    try:
        # On utilise le module Finnhub existant : on mappe `lookback` sur `lookback_days`
        df = get_history(symbol, API_KEY, resolution="D", lookback_days=lookback)
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données Finnhub : {e}")
        st.stop()

    if df is None or df.empty:
        st.error("❌ Aucune donnée reçue de Finnhub pour ce ticker / ces paramètres.")
        st.stop()

    st.success(f"Données chargées pour {symbol}")
    st.dataframe(df.tail(), use_container_width=True)

    # ------------------------------
    # 2. Application des stratégies
    # ------------------------------
    st.subheader("🧠 Stratégie appliquée")

    df_bh = strategy_buy_and_hold(df)

    if strategy_choice == "Buy & Hold":
        df_strat = df_bh.copy()
        st.write("Stratégie utilisée : **Buy & Hold** (pleinement investi tout du long).")

    else:
        df_strat = strategy_sma(df, short=short, long=long)
        st.write(
            f"Stratégie utilisée : **SMA Momentum** avec SMA courte = {short} jours, "
            f"SMA longue = {long} jours."
        )

    # ------------------------------
    # 3. Graphique prix + indicateurs
    # ------------------------------
    st.subheader("📉 Prix & Indicateurs")

    fig_price = plot_price_with_indicators(df_strat)
    st.plotly_chart(fig_price, use_container_width=True)

    # ------------------------------
    # 4. Courbes de valeur (equity curves)
    # ------------------------------
    st.subheader("📈 Performance — Stratégie vs Buy & Hold")

    fig_equity = plot_equity(df_bh, df_strat)
    st.plotly_chart(fig_equity, use_container_width=True)

    # ------------------------------
    # 5. Indicateurs de performance
    # ------------------------------
    st.subheader("📊 Indicateurs quantitatifs")

    metrics = compute_metrics(df_strat)

    col1, col2, col3 = st.columns(3)
    col1.metric("Sharpe Ratio", metrics["Sharpe Ratio"])
    col2.metric("Volatilité (ann.)", f"{metrics['Volatility (ann.)']:.2%}")
    col3.metric("Max Drawdown", f"{metrics['Max Drawdown']*100:.2f}%")

# =========================================================
# PAGE 3 — PORTFOLIO (PLACEHOLDER)
# =========================================================
elif page == "📊 Portfolio (bientôt)":
    st.title("📊 Portfolio — Multi-Actifs (à venir)")

    st.markdown(
        """
        Cette section sera dédiée à la **Partie B** du projet :

        - Gestion d’un portefeuille multi-actifs
        - Récupération des prix pour plusieurs tickers
        - Construction de portefeuilles
        - Indicateurs de performance globaux
        - Corrélations, diversification, matrices de covariance

        👉 Pour l’instant, concentre-toi sur la partie **Single Asset (Quant A)**.
        """
    )
