import streamlit as st
import os
from datetime import date, timedelta
import re

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

# Dossier où cron écrit les rapports : cron/data
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cron", "data")

# --- 1) Lister les rapports existants (on exclut les ERROR)
report_files = []
if os.path.exists(DATA_DIR):
    report_files = [
        f for f in os.listdir(DATA_DIR)
        if f.startswith("daily_report_")
        and f.endswith(".txt")
        and "_ERROR_" not in f
    ]

# --- Helper: parser les noms daily_report_{TICKER}_{YYYY-MM-DD}.txt
def parse_report_filename(fn: str):
    base = fn.replace("daily_report_", "").replace(".txt", "")
    parts = base.split("_")
    if len(parts) < 2:
        return None, None
    ticker = "_".join(parts[:-1])
    d = parts[-1]
    try:
        y, m, dd = map(int, d.split("-"))
        return ticker, date(y, m, dd)
    except Exception:
        return None, None

reports = []
for f in report_files:
    tkr, d = parse_report_filename(f)
    if tkr and d:
        reports.append((tkr, d, f))

if not reports:
    st.sidebar.caption("Aucun rapport trouvé dans cron/data.")
else:
    # tickers dispo
    tickers = sorted({t for (t, _, _) in reports})
    selected_ticker = st.sidebar.selectbox("Ticker", tickers, key="admin_ticker")

    # 30 derniers rapports (pas 30 jours calendaires)
    reports_ticker = [(t, d, f) for (t, d, f) in reports if t == selected_ticker]
    reports_ticker = sorted(reports_ticker, key=lambda x: x[1], reverse=True)[:30]

    if not reports_ticker:
        st.sidebar.caption("Aucun rapport trouvé pour ce ticker.")
    else:
        dates_avail = [d for (_, d, _) in reports_ticker]  # déjà triées desc

        selected_day = st.sidebar.selectbox(
            "Jour (Pour avoir accès aux 30 derniers rapport, run le code manuellement)",
            dates_avail,
            format_func=lambda d: d.isoformat(),
            key="admin_day",
        )

        file_match = next((f for (_, d, f) in reports_ticker if d == selected_day), None)

        if st.sidebar.button("Lire le rapport", use_container_width=True):
            if file_match is None:
                st.sidebar.error("Aucun fichier correspondant trouvé.")
            else:
                file_path = os.path.join(DATA_DIR, file_match)
                try:
                    with open(file_path, "r", encoding="utf-8") as fh:
                        content = fh.read()
                except UnicodeDecodeError:
                    # fallback vieux fichiers (ANSI/cp1252)
                    with open(file_path, "r", encoding="cp1252", errors="replace") as fh:
                        content = fh.read()
                except Exception as e:
                    st.sidebar.error(f"Erreur de lecture : {e}")
                    content = None

                if content is not None:
                    st.session_state["show_report"] = True
                    st.session_state["report_content"] = content
                    st.session_state["report_name"] = file_match

# --- Viewer
if st.session_state["show_report"]:
    st.markdown("### 📄 Visualiseur de Rapport")
    st.caption(f"Fichier : {st.session_state['report_name']}")
    st.code(st.session_state["report_content"], language="text")

    if st.button("Fermer le rapport"):
        st.session_state["show_report"] = False
        st.rerun()

    st.markdown("---")

