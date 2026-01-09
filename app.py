import streamlit as st
import os

# ---------------------------------------------------------
# CONFIG STREAMLIT — DOIT ÊTRE EN PREMIER
# ---------------------------------------------------------
st.set_page_config(page_title="Quant Dashboard", layout="wide")

# ---------------------------------------------------------
# SIDEBAR (navigation gérée par /pages)
# ---------------------------------------------------------
st.sidebar.title("📊 Quant Dashboard")
st.sidebar.markdown("Navigation via les pages à gauche 👈")

# ---------------------------------------------------------
# PAGE ACCUEIL
# ---------------------------------------------------------
st.title("🏠 Quant Dashboard — Projet Python & Finance")

st.markdown(
    """
Bienvenue 👋

Ce dashboard permet de :
- **Backtester des stratégies** sur un actif (Partie A)
- Construire et backtester un **portefeuille multi-actifs** avec **segments de stratégies** (Partie B)
- Explorer une zone **Prédiction** (ML basique) selon la page

---

## 🎯 Partie A — Single Asset (page 2)
**Objectif :** analyser un seul ticker (action, crypto, indice) et comparer plusieurs stratégies.

**Fonctionnalités :**
- Téléchargement des prix via **Yahoo Finance (`yfinance`)**
- Backtests : **Buy & Hold (BH)**, **SMA**, **RSI**, **MACD**, **Bollinger**, **Golden Cross**
- Graphiques : prix, indicateurs, equity curve “gated” (BH → stratégie → BH)
- Statistiques : **Sharpe**, **Sortino** (équivalent du Sharpe mais comptabilise uniquement les mouvements perdants), **volatilité annualisée**, **max drawdown**
- **Zone prédiction** : features de log-returns, modèles simples (baseline / RF / linéaire selon implémentation)

---

## 🧩 Partie B — Portfolio multi-actifs (page 3)
**Objectif :** construire un portefeuille (montants € par ticker), puis backtester une stratégie “segmentée” (sur une période définie: entrée/sortie).

**Fonctionnalités :**
- Création de portefeuille : allocation manuelle, égal-pondération, fusion des doublons
- Construction d’un pseudo-actif portfolio (série Close = valeur du portefeuille)
- Fenêtre globale (slider) + **intervalles non-chevauchants**
- Backtest : **Buy & Hold portefeuille vs stratégies choisies**
- Graphique comparaison entre **Buy and Hold** et **stratégie active** (notes: lorsqu'aucune stratégie n'est présente, on se positionne en buy and hold)
- Statistiques : Sharpe / Sortino / Vol / MaxDD / Perf

---

## ✅ Tips & Debug
- Si vous modifiez le portefeuille : les **segments (intervalles où sont utilisées les stratégies) sont reset** automatiquement.
- Si un graphique semble figé : 
  - vérifiez la **fenêtre de backtest**
  - vérifiez que vous avez **assez de points** (min ~30 jours)
- Les données historiques passent par un **cache Streamlit** pour des raisons de performance.

Bon backtest 👨‍💻📈
"""
)


# =========================================================
# 📂 ESPACE ADMIN (SIDEBAR & VISUALISEUR)
# =========================================================

if "show_report" not in st.session_state:
    st.session_state["show_report"] = False
if "report_content" not in st.session_state:
    st.session_state["report_content"] = ""
if "report_name" not in st.session_state:
    st.session_state["report_name"] = ""

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Espace Admin")

DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "cron",
    "data"
)

report_files = []
if os.path.exists(DATA_DIR):
    report_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".txt")], reverse=True)

if report_files:
    
    # Labels courts (lisibles) -> vrais noms de fichiers
    label_to_file = {
        f.replace("daily_report_", "").replace(".txt", ""): f
        for f in report_files
    }

    selected_label = st.sidebar.selectbox(
        "Choisir un rapport :",
        list(label_to_file.keys()),
        key="admin_select_report"
    )

    selected_report = label_to_file[selected_label]

    

    if st.sidebar.button("Lire le rapport", use_container_width=True):
        file_path = os.path.join(DATA_DIR, selected_report)
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
              content = f.read()
            st.session_state["show_report"] = True
            st.session_state["report_content"] = content
            st.session_state["report_name"] = selected_report
        except Exception as e:
            st.sidebar.error(f"Erreur de lecture : {e}")
else:
    st.sidebar.caption("Aucun rapport (.txt) trouvé dans /cron/data.")

if st.session_state["show_report"]:
    st.markdown("### 📄 Visualiseur de Rapport")
    st.caption(f"Contenu du fichier : {st.session_state['report_name']}")
    st.code(st.session_state["report_content"], language="text")

    if st.button("Fermer le rapport"):
        st.session_state["show_report"] = False
        st.rerun()

    st.markdown("---")
