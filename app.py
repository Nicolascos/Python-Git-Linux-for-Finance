import streamlit as st
import pandas as pd
import plotly.express as px
from modules.plots import plot_price_with_indicators, plot_equity
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # 1) si yfinance intraday : "Datetime"
    if "Date" in out.columns:
        return out
    if "Datetime" in out.columns:
        return out.rename(columns={"Datetime": "Date"})

    # 2) si "Date" est l'index (ou Datetime)
    if out.index.name in ("Date", "Datetime"):
        out = out.reset_index()
        if "Datetime" in out.columns and "Date" not in out.columns:
            out = out.rename(columns={"Datetime": "Date"})
        return out

    # 3) index anonyme -> reset_index crée "index"
    out = out.reset_index()
    if "Date" not in out.columns and "index" in out.columns:
        out = out.rename(columns={"index": "Date"})
    return out

def normalize_dedup_date(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # 1) Si Date est déjà une colonne
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"]).dt.normalize()
        out = out.sort_values("Date")
        out = out.drop_duplicates(subset=["Date"], keep="first")
        out = out.reset_index(drop=True)
        return out

    # 2) Sinon, on considère que la date est dans l'index (souvent DatetimeIndex)
    idx = out.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.to_datetime(idx, errors="coerce")
    idx = idx.normalize()

    out = out.copy()
    out.index = idx
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="first")]

    # remettre une vraie colonne Date
    out = out.reset_index().rename(columns={"index": "Date"})
    return out

def build_gated_equity(df_full: pd.DataFrame,
                       df_strat_slice: pd.DataFrame,
                       start_d,
                       end_d):
    """
    Courbe sur toute la période :
    - Buy&Hold avant start
    - Stratégie entre start et end (ancrée sur BH à l’entrée)
    - Buy&Hold après end en gardant la perf (BH "scalé" pour continuité)
    Retourne: out, start_ts_eff, end_ts_eff
    """

    out = normalize_dedup_date(df_full)
    out["Date"] = pd.to_datetime(out["Date"]).dt.normalize()
    out = out.sort_values("Date").drop_duplicates(subset=["Date"]).reset_index(drop=True)

    # Close propre
    close = out["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    out["Returns"] = close.pct_change().fillna(0.0)

    # Buy&Hold "sous-jacent" sur toute la période (base 1)
    out["BH"] = (1.0 + out["Returns"]).cumprod()

    # --- stratégie (fenêtre) ---
    strat = normalize_dedup_date(df_strat_slice)
    strat["Date"] = pd.to_datetime(strat["Date"]).dt.normalize()
    strat = strat.sort_values("Date").drop_duplicates(subset=["Date"])

    if "Position" in strat.columns:
        pos_s = strat.set_index("Date")["Position"].astype(float)
    elif "Signal" in strat.columns:
        pos_s = strat.set_index("Date")["Signal"].shift(1).fillna(0.0).astype(float)
    else:
        pos_s = pd.Series(dtype=float)

    out_i = out.set_index("Date")

    # snap start/end au plus proche jour disponible
    start_ts = pd.Timestamp(start_d).normalize()
    end_ts   = pd.Timestamp(end_d).normalize()

    dates = out_i.index
    start_ts_eff = dates[dates.get_indexer([start_ts], method="nearest")][0]
    end_ts_eff   = dates[dates.get_indexer([end_ts], method="nearest")][0]
    if end_ts_eff < start_ts_eff:
        start_ts_eff, end_ts_eff = end_ts_eff, start_ts_eff

    active = (out_i.index >= start_ts_eff) & (out_i.index <= end_ts_eff)

    # positions alignées sur tout l’index
    pos_aligned = pos_s.reindex(out_i.index).fillna(0.0)

    # 1) perf stratégie RELATIVE (base 1) uniquement sur la fenêtre
    r = out_i["Returns"]
    strat_rel = pd.Series(1.0, index=out_i.index)

    # cumprod dans la fenêtre (ancrée à 1 au début de fenêtre)
    strat_rel.loc[active] = (1.0 + r.loc[active] * pos_aligned.loc[active]).cumprod()
    strat_rel.loc[active] /= strat_rel.loc[start_ts_eff]  # force = 1 à l'entrée

    # 2) ancrage sur BH à l’entrée
    bh_start = float(out_i.loc[start_ts_eff, "BH"])
    strategy_window = bh_start * strat_rel

    # 3) hors fenêtre : BH avant, BH scalé après pour continuité
    out_i["Strategy"] = out_i["BH"]  # avant start => BH

    out_i.loc[active, "Strategy"] = strategy_window.loc[active]

    # scale après end pour garder la perf atteinte
    strat_end = float(out_i.loc[end_ts_eff, "Strategy"])
    bh_end = float(out_i.loc[end_ts_eff, "BH"])
    scale = strat_end / bh_end if bh_end != 0 else 1.0

    after = out_i.index > end_ts_eff
    out_i.loc[after, "Strategy"] = out_i.loc[after, "BH"] * scale

    out = out_i.reset_index()
    return out, start_ts_eff, end_ts_eff



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

    with st.sidebar.form("run_form"):
        submitted = st.form_submit_button("🚀 Lancer l’analyse")

    if not submitted and "run_single" not in st.session_state:
        st.info("Configure les paramètres puis clique sur **🚀 Lancer l’analyse**.")
        st.stop()

    if submitted:
        st.session_state["run_single"] = True

    if st.sidebar.button("🔄 Reset analyse"):
        st.session_state.pop("run_single", None)
        st.rerun()

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
    # 1.b Sélection de la période (Date d'entrée / sortie)
    # ------------------------------
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    st.sidebar.subheader("📅 Période d'analyse")

    min_d = df["Date"].min().date()
    max_d = df["Date"].max().date()

    start_d, end_d = st.sidebar.slider(
        "Date d'entrée / sortie",
        min_value=min_d,
        max_value=max_d,
        value=(min_d, max_d),
        format="YYYY-MM-DD"
    )

    mask = (df["Date"].dt.date >= start_d) & (df["Date"].dt.date <= end_d)
    df_slice = df.loc[mask].copy()

    if df_slice.empty or len(df_slice) < 30:
        st.warning("⚠️ Période trop courte (minimum ~30 jours conseillé).")
        st.stop()

    st.info(f"📆 Analyse sur la période : {start_d} → {end_d} ({len(df_slice)} points)")


    # ------------------------------
    # 2. Application des stratégies
    # ------------------------------
    st.subheader("🧠 Stratégie appliquée")

    # Buy & Hold toujours calculé
    df_bh_full = strategy_buy_and_hold(df)       # B&H complet pour les visus
    df_bh = strategy_buy_and_hold(df_slice)      # B&H fenêtre pour les metrics si tu veux


    # Sélection stratégie
    if strategy_choice == "Buy & Hold":
        df_strat = df_bh.copy()
        st.write("Stratégie utilisée : **Buy & Hold**.")

    elif strategy_choice == "SMA Momentum":
        df_strat = strategy_sma(df_slice, short=short, long=long)
        st.write(f"SMA Momentum — courte = {short}, longue = {long}")

    elif strategy_choice == "RSI":
        df_strat = strategy_rsi(df_slice)
        

    elif strategy_choice == "MACD":
        df_strat = strategy_macd(df_slice)
        

    elif strategy_choice == "Bollinger":
        # Utilisation des nouveaux paramètres
        df_strat = strategy_bollinger(df_slice, window=bb_window, num_std=bb_std)
        

    elif strategy_choice == "Golden Cross":
        df_strat = strategy_golden_cross(df_slice)
        
    df_bh_full = strategy_buy_and_hold(df)   # B&H sur toute la période (visu)


    df_strat_gated, start_ts_eff, end_ts_eff = build_gated_equity(df, df_strat, start_d, end_d)


   
    # ------------------------------
    # 3. Courbes de valeur (equity curves)
    # ------------------------------
    st.subheader("📈 Performance — Stratégie vs Buy & Hold")

    g = df_strat_gated.copy()
    g["Date"] = pd.to_datetime(g["Date"])

    # Masques (fenêtre et après-sortie)
    m_active = (g["Date"] >= start_ts_eff) & (g["Date"] <= end_ts_eff)
    m_after  = g["Date"] > end_ts_eff

    # Séries segmentées (NaN hors zone => Plotly coupe la ligne)
    g["Strat_Window"] = np.where(m_active, g["Strategy"], np.nan)
    g["Port_After"]   = np.where(m_after,  g["Strategy"], np.nan)

    # Figure
    fig_equity = go.Figure()

    # Buy&Hold (sous-jacent)
    fig_equity.add_trace(go.Scatter(
        x=g["Date"], y=g["BH"],
        mode="lines",
        name="Buy & Hold"
    ))

    # Stratégie uniquement pendant la fenêtre
    fig_equity.add_trace(go.Scatter(
        x=g["Date"], y=g["Strat_Window"],
        mode="lines",
        name="Stratégie (active)"
    ))

    # Après sortie : portefeuille en Buy&Hold (scalé, continuité)
    fig_equity.add_trace(go.Scatter(
        x=g["Date"], y=g["Port_After"],
        mode="lines",
        name="Après sortie : Buy&Hold (portefeuille)"
    ))

    # Points entrée/sortie (sur la courbe "Strategy")
    y_start = float(g.loc[g["Date"] == start_ts_eff, "Strategy"].iloc[0])
    y_end   = float(g.loc[g["Date"] == end_ts_eff, "Strategy"].iloc[0])

    # Points entrée/sortie (UNE seule gommette chacun, plus petit, pas dans la légende)
    fig_equity.add_trace(go.Scatter(
        x=[start_ts_eff],
        y=[y_start],
        mode="markers",
        marker=dict(
            size=7,                      # petite gommette
            color="#00E676",              # vert vif
            symbol="circle",
            line=dict(color="black", width=1)
        ),
        name="Entrée",
        showlegend=True,
        hovertemplate=(
            "<b>Entrée</b><br>"
            "Date: %{x|%Y-%m-%d}<br>"
            "Valeur: %{y:.3f}"
            "<extra></extra>"
        )
    ))

    fig_equity.add_trace(go.Scatter(
        x=[end_ts_eff],
        y=[y_end],
        mode="markers",
        marker=dict(
            size=7,                      # petite gommette
            color="#FF5252",              # rouge vif
            symbol="circle",
            line=dict(color="black", width=1)
        ),
        name="Sortie",
        showlegend=True,
        hovertemplate=(
            "<b>Sortie</b><br>"
            "Date: %{x|%Y-%m-%d}<br>"
            "Valeur: %{y:.3f}"
            "<extra></extra>"
        )
    ))


    # Ligne verticale + annotation (Option 2)
    fig_equity.add_vline(
    x=end_ts_eff,
    line_width=2,
    line_dash="dash",
    line_color="rgba(255,255,255,0.65)"  # plus foncé/visible
    )


    fig_equity.update_layout(
        template="plotly_dark",
        height=500,
        title="Comparaison des stratégies",
        xaxis_title="Date",
        yaxis_title="Évolution portefeuille (base 1)"
    )

    st.plotly_chart(fig_equity, use_container_width=True, key="equity_main")

    st.caption("Après la date de sortie, le portefeuille repasse en Buy&Hold en conservant la performance atteinte à la sortie.")

    

    # =========================================================
    # 🔥 COMPARAISON MULTI-STRATÉGIES
    # =========================================================
    st.subheader("⚡ Comparaison Multi-Stratégies")

    # Calcul des stratégies
    df_sma = strategy_sma(df_slice, short=20, long=50)
    df_rsi = strategy_rsi(df_slice)
    df_macd = strategy_macd(df_slice)
    df_bb = strategy_bollinger(df_slice, window=20, num_std=2)
    df_gc = strategy_golden_cross(df_slice)

    df_compare = pd.DataFrame({
        "Buy & Hold": df_bh["Strategy"].values,
        "SMA": df_sma["Strategy"].values,
        "RSI": df_rsi["Strategy"].values,
        "MACD": df_macd["Strategy"].values,
        "Bollinger": df_bb["Strategy"].values,
        "Golden Cross": df_gc["Strategy"].values
    }, index=pd.to_datetime(df_slice["Date"]))

    # optionnel mais conseillé : enlever les lignes incomplètes (rolling windows)
    df_compare = df_compare.dropna(how="any")

    st.line_chart(df_compare)

    
    # =========================================================
    # 📊 TABLEAU DES METRICS POUR TOUTES LES STRATÉGIES
    # =========================================================
    st.subheader("📘 Tableau de synthèse des performances")

    strategies_results = {
        "Buy & Hold": df_bh,
        "SMA": df_sma,
        "RSI": df_rsi,
        "MACD": df_macd,
        "Bollinger": df_bb,
        "Golden Cross": df_gc
    }

    table_stats = []

    for name, df_s in strategies_results.items():
        metrics = compute_metrics(df_s)
        table_stats.append({
            "Stratégie": name,
            "Sharpe Ratio": metrics["Sharpe Ratio"],
            "Sortino Ratio": metrics["Sortino"],
            "Volatilité (ann.)": metrics["Volatility (ann.)"],
            "Max Drawdown": metrics["Max Drawdown"],
            "Performance totale (%)": (df_s["Strategy"].iloc[-1] - 1) * 100
        })

    df_stats = (
        pd.DataFrame(table_stats)
        .set_index("Stratégie")
        .sort_values("Sharpe Ratio", ascending=False)
    )

    st.dataframe(df_stats)



    # ------------------------------
    # 4. Indicateurs de performance (Comparaison B&H)
    # ------------------------------
    st.subheader("📊 Indicateurs quantitatifs")

    metrics_strat = compute_metrics(df_strat)
    metrics_bh = compute_metrics(df_bh)
    
    # Calcul du gain total (la 'Strategy' est la courbe de croissance, base 1)
    total_perf_strat = df_strat["Strategy"].iloc[-1] - 1
    total_perf_bh = df_bh["Strategy"].iloc[-1] - 1

    col1, col2, col3, col4,col5 = st.columns(5)
    
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
    
    # Sortino Ratio
    sortino_delta = metrics_strat['Sortino'] - metrics_bh['Sortino']
    col5.metric("Sortino Ratio (Stratégie)",
            f"{metrics_strat['Sortino']:.3f}",
            delta=f"{sortino_delta:.3f} vs B&H")



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