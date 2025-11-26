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
