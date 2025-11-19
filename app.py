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
st.header("🔍 Entrée utilisateur")
user_text = st.text_input("Tape quelque chose :", value="Hello Streamlit !")
st.write("Tu as écrit :", user_text)

# -----------------------------------------
# SECTION 2 — GRAPHIQUE SIMPLE
# -----------------------------------------
st.header("📈 Exemple de graphique")

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
