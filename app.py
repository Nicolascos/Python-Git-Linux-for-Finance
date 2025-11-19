"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------
#         MINI PLATFORME STREAMLIT DE BASE
# ---------------------------------------------------------

# Titre principal
st.title("Mini Financial Dashboard (Local Version)")

# -----------------------------------------
# SECTION 1 — INPUT UTILISATEUR
# -----------------------------------------
st.header("Entrée utilisateur")
user_text = st.text_input("Tape quelque chose :", value="Hello Streamlit !")
st.write("Tu as écrit :", user_text)

# -----------------------------------------
# SECTION 2 — GRAPHIQUE SIMPLE
# -----------------------------------------
st.header("Exemple de graphique")

# Création de données
x = np.linspace(0, 10, 200)
y = np.sin(x)

df = pd.DataFrame({"x": x, "Signal": y})

fig = px.line(df, x="x", y="Signal", title="Exemple : sin(x)")
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------
# SECTION 3 — BOUTON DYNAMIQUE
# -----------------------------------------
st.header("⚡ Action avec bouton")

if st.button("Clique ici"):
    st.success("Le bouton fonctionne !")
else:
    st.info("Appuie sur le bouton")

# -----------------------------------------
# SECTION 4 — Rafraîchissement automatique (option)
# -----------------------------------------
st.empty()
"""
import streamlit as st
import Importation_data
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Quant Dashboard", layout="wide")

# Sidebar navigation
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
    st.write("Cette page affichera :")
    st.markdown("""
    - Données live API (Finnhub)  
    - Graphique des prix  
    - Backtests  
    - Indicateurs (Sharpe, Max Drawdown, etc.)  
    """)


# ------------------------------
# PAGE 3 — Portfolio
# ------------------------------
elif page == "📊 Portfolio":
    st.title("Analyse Portefeuille Multi-Actifs")
    st.write("Cette page affichera :")
    st.markdown("""
    - Sélection multi-actifs  
    - Matrice de corrélation  
    - Allocation et rebalancing  
    - Performance cumulée  
    """)


# ------------------------------
# PAGE 4 — 🇫🇷 Taux France (live)
# ------------------------------
elif page == "🇫🇷 Taux France":
    st.title("🇫🇷 Courbe des taux — France (Live Boursorama)")

    # Bouton refresh manuel
    if st.button("🔄 Rafraîchir maintenant"):
        st.cache_data.clear()
        st.success("Données mises à jour !")

    @st.cache_data(ttl=300)  # ⏳ Auto-refresh toutes les 5 minutes
    def load_france_yields():
        return Importation_data.get_france_yields()

    try:
        df = load_france_yields()
        st.subheader("📄 Données brutes")
        st.dataframe(df, use_container_width=True)

        # Graphique Yield Curve
        fig = px.line(
            df.T.iloc[1:],  # ignore la colonne Pays
            title="Courbe des taux — France",
            labels={"index": "Maturité", "value": "Taux (%)"},
        )
        st.subheader("📈 Courbe des taux")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")