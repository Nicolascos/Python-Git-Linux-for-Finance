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
    strategy_rsi,
    strategy_macd,
    strategy_bollinger,
    strategy_golden_cross,
    compute_metrics
)
from modules.plots import plot_price_with_indicators, plot_equity

# ---------------------------------------------------------
# CACHING ET RAFRAÎCHISSEMENT AUTOMATIQUE (Feature 5)
# ---------------------------------------------------------
@st.cache_data(ttl=300) # Rafraîchit les données toutes les 300 secondes (5 minutes)
def load_historical_data(symbol, lookback_days):
    """Fonction wrappée pour le caching des données historiques."""
    return get_history(symbol, lookback_days=lookback_days)

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
        - **Rafraîchissement automatique des données toutes les 5 minutes.**
        - Stratégies : Buy & Hold, SMA, RSI, MACD, Bandes de Bollinger, Golden Cross.
        - Visualisation : Prix + indicateurs techniques et Equity curve.
        - Indicateurs quantitatifs : Sharpe Ratio, Volatilité annualisée, Max Drawdown.
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

    ticker_dict = {
    "Actions US 🇺🇸": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "Crypto(prix pas à jour) 💎": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Indices 📈": ["^GSPC", "^DJI", "^IXIC"]
    }

    categorie = st.sidebar.selectbox("Catégorie d’actifs :", list(ticker_dict.keys()))
    symbol = st.sidebar.selectbox("Ticker :", ticker_dict[categorie])
    
    # Récupération et affichage du prix live (Feature 3)
    live_price = get_live_price(symbol)
    if live_price is not None:
        st.subheader(f"🏷️ Prix Actuel {symbol} : **{live_price:,.2f} $**")
        st.markdown("---")
    else:
        st.error(f"❌ Impossible de récupérer le prix live pour {symbol}.")


    strategy_choice = st.sidebar.selectbox(
        "Stratégie :",
        [
            "Buy & Hold",
            "SMA Momentum",
            "RSI",
            "MACD",
            "Bollinger",
            "Golden Cross"
        ]
    )

    # Paramètres spécifiques SMA
    if strategy_choice == "SMA Momentum":
        short = st.sidebar.number_input("SMA courte (jours) :", 5, 100, 20)
        long = st.sidebar.number_input("SMA longue (jours) :", 20, 300, 50)

    # Paramètres spécifiques Bollinger (ajout pour l'exemple)
    if strategy_choice == "Bollinger":
        bb_window = st.sidebar.number_input("Fenêtre (jours) :", 10, 100, 20)
        bb_std = st.sidebar.slider("Écarts-types :", 1.0, 3.0, 2.0, step=0.1)


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
        st.info("Configure les paramètres puis clique sur **🚀 Lancer l’analyse**.")
        st.stop()

    # ------------------------------
    # 1. Chargement des données
    # ------------------------------
    st.subheader("📡 Données historiques")

    # MODIFIÉ : Utiliser la fonction cachée
    df = load_historical_data(symbol, lookback_days=lookback)

    if df is None or df.empty:
        st.error(f"❌ Impossible de récupérer des données historiques pour {symbol}.")
        st.stop()

    st.success(f"Données chargées pour {symbol} du {df['Date'].iloc[0].date()} au {df['Date'].iloc[-1].date()}")
    st.dataframe(df.tail(), use_container_width=True)

    # ------------------------------
    # 2. Application des stratégies
    # ------------------------------
    st.subheader("🧠 Stratégie appliquée")

    # Buy & Hold toujours calculé
    df_bh = strategy_buy_and_hold(df)

    # Sélection stratégie
    if strategy_choice == "Buy & Hold":
        df_strat = df_bh.copy()
        st.write("Stratégie utilisée : **Buy & Hold**.")

    elif strategy_choice == "SMA Momentum":
        df_strat = strategy_sma(df, short=short, long=long)
        st.write(f"SMA Momentum — courte = {short}, longue = {long}")

    elif strategy_choice == "RSI":
        df_strat = strategy_rsi(df)
        st.write("Stratégie utilisée : **RSI** (surachat/survente).")

    elif strategy_choice == "MACD":
        df_strat = strategy_macd(df)
        st.write("Stratégie utilisée : **MACD**.")

    elif strategy_choice == "Bollinger":
        # Utilisation des nouveaux paramètres
        df_strat = strategy_bollinger(df, window=bb_window, num_std=bb_std)
        st.write(f"Stratégie utilisée : **Bandes de Bollinger** — Fenêtre={bb_window}, Std={bb_std}.")

    elif strategy_choice == "Golden Cross":
        df_strat = strategy_golden_cross(df)
        st.write("Stratégie utilisée : **Golden Cross / Death Cross**.")

   
    # ------------------------------
    # 3. Courbes de valeur (equity curves)
    # ------------------------------
    st.subheader("📈 Performance — Stratégie vs Buy & Hold")

    fig_equity = plot_equity(df_bh, df_strat)
    st.plotly_chart(fig_equity, use_container_width=True)

    # ------------------------------
    # 4. Indicateurs de performance (Comparaison B&H)
    # ------------------------------
    st.subheader("📊 Indicateurs quantitatifs")

    metrics_strat = compute_metrics(df_strat)
    metrics_bh = compute_metrics(df_bh)
    
    # Calcul du gain total (la 'Strategy' est la courbe de croissance, base 1)
    total_perf_strat = df_strat["Strategy"].iloc[-1] - 1
    total_perf_bh = df_bh["Strategy"].iloc[-1] - 1

    col1, col2, col3, col4 = st.columns(4)
    
    # Sharpe Ratio
    sharpe_delta = metrics_strat['Sharpe Ratio'] - metrics_bh['Sharpe Ratio']
    col1.metric("Sharpe Ratio (Stratégie)", 
                f"{metrics_strat['Sharpe Ratio']:.3f}", 
                delta=f"{sharpe_delta:.3f} vs B&H")
    
    # Max Drawdown
    dd_strat_display = f"{metrics_strat['Max Drawdown']*100:.2f}%"
    dd_bh_display = f"{metrics_bh['Max Drawdown']*100:.2f}%"
    col2.metric("Max Drawdown", dd_strat_display, delta=f"B&H: {dd_bh_display}")

    # Volatilité annualisée
    vol_delta = metrics_strat['Volatility (ann.)'] - metrics_bh['Volatility (ann.)']
    col3.metric("Volatilité (ann.)", 
                f"{metrics_strat['Volatility (ann.)']:.2%}",
                delta=f"{vol_delta:.2%} vs B&H")

    # Gain Total
    perf_delta = total_perf_strat - total_perf_bh
    col4.metric("Gain Total",
                f"{total_perf_strat*100:.2f} %",
                delta=f"{perf_delta*100:.2f} % vs B&H")


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