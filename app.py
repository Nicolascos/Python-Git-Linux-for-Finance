import streamlit as st

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

Ce dashboard te permet de :
- **Backtester des stratégies** sur un actif (Partie A)
- Construire et backtester un **portefeuille multi-actifs** avec **segments de stratégies** (Partie B)
- Explorer une zone **Prédiction** (ML basique) selon la page

---

## 🎯 Partie A — Single Asset (page 2)
**Objectif :** analyser un seul ticker (action, crypto, indice) et comparer plusieurs stratégies.

**Fonctionnalités :**
- Téléchargement des prix via **Yahoo Finance (`yfinance`)**
- Backtests : **Buy & Hold**, **SMA**, **RSI**, **MACD**, **Bollinger**, **Golden Cross**
- Graphiques : prix, indicateurs, **equity curve “gated”** (BH → stratégie → BH)
- Statistiques : **Sharpe**, **Sortino**, **volatilité annualisée**, **max drawdown**
- **Zone prédiction** : features de log-returns, modèles simples (baseline / RF / linéaire selon implémentation)

➡️ Ouvre **“2_Single_Asset”** dans le menu à gauche.

---

## 🧩 Partie B — Portfolio multi-actifs (page 3)
**Objectif :** construire un portefeuille (montants € par ticker), puis backtester une stratégie “segmentée”.

**Fonctionnalités :**
- Création de portefeuille : allocation manuelle, **égal-pondération**, fusion des doublons
- Construction d’un pseudo-actif **portfolio** (série Close = valeur du portefeuille)
- Fenêtre globale (slider) + **segments non-chevauchants**
- Backtest : **Buy & Hold portefeuille vs stratégie segmentée**
- Graphique comparaison : **BH**, **stratégie active**, **hors segments = BH scalé**
- Statistiques : Sharpe / Sortino / Vol / MaxDD / Perf

➡️ Ouvre **“3_Portfolio”** dans le menu à gauche.

---

## ✅ Tips & Debug
- Si tu modifies le portefeuille : les **segments sont reset** automatiquement (normal).
- Si un graphique semble figé : 
  - vérifie la **fenêtre de backtest**
  - vérifie que tu as **assez de points** (min ~30 jours)
- Les données historiques passent par un **cache Streamlit** (performance).

Bon backtest 👨‍💻📈
"""
)
