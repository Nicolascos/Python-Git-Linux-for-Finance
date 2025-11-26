import streamlit as st
import Importation_data
import plotly.express as px
import pandas as pd
from modules.finnhub_api import get_live_price, get_history


# ---------------------------------------------------------
# FIX STREAMLIT — set_page_config doit être en premier !
# ---------------------------------------------------------
st.set_page_config(
    page_title="Quant Dashboard",
    layout="wide"
)

# ---------------------------------------------------------
# Chargement simple et sécurisé de la clé API Finnhub
# ---------------------------------------------------------
try:
    API_KEY = st.secrets["FINNHUB_API_KEY"]

except KeyError:
    st.error("""
    ❌ Clé API Finnhub manquante.

    ➜ Va dans Streamlit Cloud :  
      **Settings → Secrets**

    Et ajoute :

    ```
    FINNHUB_API_KEY = "ta_clé_api"
    ```
    """)
    API_KEY = None

except Exception as e:
    st.error(f"Erreur inattendue lors du chargement de la clé API : {e}")
    API_KEY = None


# ---------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------
page = st.sidebar.radio(
    "📌 Navigation",
    ["🏠 Accueil", "📈 Single Asset", "📊 Portfolio", "🇫🇷 Taux France"]
)


# ------------------------------
# PAGE 1 — Accueil
# ------------------------------
if page == "🏠 Accueil":

    st.title("📊 Quant Dashboard")
    st.markdown("### Bienvenue sur ta plateforme d’analyse financière.")
    st.markdown("Utilise le menu à gauche pour naviguer entre les modules.")


# ------------------------------
# PAGE 2 — Single Asset
# ------------------------------
elif page == "📈 Single Asset":

    st.title("📈 Analyse d’un Actif Unique — Quant A")

    if API_KEY is None:
        st.warning("⚠️ Configure ta clé API dans `.streamlit/secrets.toml`.")
        st.stop()

    # ---------------------------------------------------------
    # Sidebar de paramètres
    # ---------------------------------------------------------
    st.sidebar.subheader("⚙️ Paramètres de l’analyse")

    symbol = st.sidebar.text_input("Ticker :", "AAPL")

    strategy_choice = st.sidebar.selectbox(
        "Stratégie :",
        ["Buy & Hold", "SMA Momentum"]
    )

    if strategy_choice == "SMA Momentum":
        short = st.sidebar.number_input("SMA courte :", 5, 100, 20)
        long = st.sidebar.number_input("SMA longue :", 20, 300, 50)

    lookback = st.sidebar.slider("Nombre de jours d'historique", 100, 1500, 365)

    if st.sidebar.button("🚀 Lancer l’analyse"):
        st.session_state["run_analysis"] = True

    if "run_analysis" not in st.session_state:
        st.info("Configure les paramètres dans la sidebar 😊")
        st.stop()

    # ---------------------------------------------------------
    # 1. Chargement des données
    # ---------------------------------------------------------
    st.subheader("📡 Chargement des données")

    df = get_history(symbol, API_KEY, lookback_days=lookback)

    if df is None:
        st.error("❌ Impossible de récupérer les données Finnhub.")
        st.stop()

    st.success(f"Données chargées pour {symbol}")
    st.dataframe(df.tail(), use_container_width=True)

    # ---------------------------------------------------------
    # 2. Application des stratégies
    # ---------------------------------------------------------
    from modules.strategy_single import (
        strategy_buy_and_hold,
        strategy_sma,
        compute_metrics
    )
    from modules.plots import plot_price_with_indicators, plot_equity

    df_bh = strategy_buy_and_hold(df)

    if strategy_choice == "Buy & Hold":
        df_strat = df_bh.copy()

    else:
        df_strat = strategy_sma(df, short=short, long=long)

    # ---------------------------------------------------------
    # 3. Graphique principal (prix + indicateurs)
    # ---------------------------------------------------------
    st.subheader("📉 Prix & Indicateurs")

    fig_price = plot_price_with_indicators(df_strat)
    st.plotly_chart(fig_price, use_container_width=True)

    # ---------------------------------------------------------
    # 4. Equity curves
    # ---------------------------------------------------------
    st.subheader("📈 Performance — Stratégie vs Buy & Hold")

    fig_equity = plot_equity(df_bh, df_strat)
    st.plotly_chart(fig_equity, use_container_width=True)

    # ---------------------------------------------------------
    # 5. Metrics
    # ---------------------------------------------------------
    st.subheader("📊 Indicateurs quantitatifs")

    metrics = compute_metrics(df_strat)

    col1, col2, col3 = st.columns(3)
    col1.metric("Sharpe Ratio", metrics["Sharpe Ratio"])
    col2.metric("Volatilité (ann.)", metrics["Volatility (ann.)"])
    col3.metric("Max Drawdown", f"{metrics['Max Drawdown']*100:.2f}%")



    st.title("📈 Analyse d'un Actif Unique")

    if API_KEY is None:
        st.warning("⚠️ Configure ta clé API dans `.streamlit/secrets.toml`.")
        st.stop()

    with st.container():
        st.subheader("🔎 Sélection de l'actif")
        symbol = st.text_input("Ticker :", "AAPL")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📡 Prix live"):
            price = get_live_price(symbol, API_KEY)
            if price:
                st.success(f"💵 Prix actuel de **{symbol}** : `{price} USD`")
            else:
                st.error("Erreur de récupération du prix via Finnhub.")

    with col2:
        if st.button("📈 Charger l'historique"):
            df_hist = get_history(symbol, API_KEY, resolution="D", count=200)

            if df_hist is not None:
                st.dataframe(df_hist, use_container_width=True)

                fig = px.line(
                    df_hist,
                    x="Date",
                    y="Close",
                    title=f"Historique des prix — {symbol}"
                )
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.error("Impossible de récupérer les données historiques.")


# ------------------------------
# PAGE 3 — Portfolio
# ------------------------------
elif page == "📊 Portfolio":

    st.title("📊 Analyse Portefeuille Multi-Actifs")
    st.info("🚧 En cours de développement — bientôt disponible !")


# ------------------------------
# PAGE 4 — 🇫🇷 Taux France (live)
# ------------------------------
elif page == "🇫🇷 Taux France":

    st.title("🇫🇷 Courbe des taux — France (Live Boursorama)")

    if st.button("🔄 Rafraîchir maintenant"):
        st.cache_data.clear()
        st.success("Données mises à jour !")

    @st.cache_data(ttl=300)
    def load_france_yields():
        return Importation_data.get_france_yields()

    try:
        df = load_france_yields()

        st.subheader("📋 Tableau des taux souverains")
        st.dataframe(df, use_container_width=True)

        st.subheader("📈 Courbe des taux (graphique)")
        fig = px.line(
            df.T.iloc[1:],
            title="Courbe des taux — France",
            labels={"index": "Maturité", "value": "Taux (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
