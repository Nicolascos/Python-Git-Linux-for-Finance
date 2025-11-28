import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------
# CONFIG STREAMLIT — DOIT ÊTRE EN PREMIER
# ---------------------------------------------------------
st.set_page_config(page_title="Quant Dashboard", layout="wide")

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
        basée sur des **données de marché (Yahoo Finance via yfinance)**.

        ### 🎯 Partie A — Single Asset
        - Récupération des données historiques (actions, crypto, indices…)
        - Stratégies :
            - Buy & Hold
            - SMA (moyennes mobiles)
        - Visualisation :
            - Prix + indicateurs techniques
            - Equity curve
        - Indicateurs quantitatifs :
            - Sharpe Ratio
            - Volatilité annualisée
            - Max Drawdown

        ### 📌 Partie B — Portfolio (à venir)

        ➜ Utilise le menu à gauche pour lancer l’analyse Single Asset.
        """
    )


# =========================================================
# PAGE 2 — SINGLE ASSET (QUANT A)
# =========================================================
elif page == "📈 Single Asset":

    st.title("📈 Analyse d’un Actif Unique — Quant A")

    # ------------------------------
    # Sidebar paramètres
    # ------------------------------
    st.sidebar.subheader("⚙️ Paramètres de l’analyse")

    symbol = st.sidebar.text_input("Ticker :", "AAPL")   # ex : AAPL / BTC-USD / ^GSPC

    strategy_choice = st.sidebar.selectbox(
        "Stratégie :",
        ["Buy & Hold", "SMA Momentum"]
    )

    if strategy_choice == "SMA Momentum":
        short = st.sidebar.number_input("SMA courte (jours) :", 5, 100, 20)
        long = st.sidebar.number_input("SMA longue (jours) :", 20, 300, 50)

    lookback = st.sidebar.slider(
        "Nombre de jours d’historique",
        min_value=100,
        max_value=3000,
        value=365,
        step=50
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

    df = get_history(symbol, lookback_days=lookback)

    if df is None or df.empty:
        st.error("❌ Impossible de récupérer des données pour ce ticker.")
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
        st.write("Stratégie utilisée : **Buy & Hold**.")

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
        - Récupération de plusieurs tickers
        - Construction d’allocations
        - Corrélations, matrices de covariance
        - Equity curve du portefeuille

        👉 À venir prochainement.
        """
    )
