import streamlit as st
import Importation_data
import plotly.express as px
import pandas as pd

# ---------------------------------------------------------
# FIX STREAMLIT — set_page_config doit être en premier !
# ---------------------------------------------------------
st.set_page_config(page_title="Quant Dashboard", layout="wide")

# Import Finnhub API module
from modules.finnhub_api import get_live_price, get_history

# ---------------------------------------------------------
# Chargement simple et sécurisé de la clé API Finnhub
# ---------------------------------------------------------
try:
    API_KEY = st.secrets["FINNHUB_API_KEY"]

except Exception:
    st.error("""
    ❌ Impossible de trouver la clé API Finnhub.

    👉 Tu dois créer un fichier `.streamlit/secrets.toml` contenant :

    FINNHUB_API_KEY = "ta_clé_api"
    """)
    API_KEY = None

except KeyError:
    st.error("""
    ❌ Le fichier `.finnhub/secrets.toml` existe mais la clé API manque.

    Ajoute :

    FINNHUB_API_KEY = "ta_clé_api"
    """)
    API_KEY = None

except Exception as e:
    st.error(f"Erreur lors du chargement de la clé API : {e}")
    API_KEY = None


# ---------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------
page = st.sidebar.selectbox(
    "Navigation",
    ["🏠 Accueil", "📈 Single Asset", "📊 Portfolio", "🇫🇷 Taux France"]
)

# ------------------------------
# PAGE 1 — Accueil
# ------------------------------
if page == "🏠 Accueil":
    st.title("Bienvenue sur ton Quant Dashboard")
    st.write("Choisis une section dans le menu de gauche.")


# ------------------------------
# PAGE 2 — Single Asset
# ------------------------------
elif page == "📈 Single Asset":
    st.title("Analyse d’un Actif Unique")

    if API_KEY is None:
        st.warning("⚠️ Configure ta clé API dans `.finnhub/secrets.toml`.")
        st.stop()

    symbol = st.text_input("🔎 Ticker :", "AAPL")

    # Prix en direct
    if st.button("📡 Prix live"):
        price = get_live_price(symbol, API_KEY)
        if price:
            st.success(f"Prix actuel de {symbol} : {price} USD")
        else:
            st.error("Erreur de récupération du prix via Finnhub.")

    # Historique OHLC
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
    st.title("Analyse Portefeuille Multi-Actifs")
    st.write("En cours de développement...")


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
        st.dataframe(df, use_container_width=True)

        fig = px.line(
            df.T.iloc[1:],
            title="Courbe des taux — France",
            labels={"index": "Maturité", "value": "Taux (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
