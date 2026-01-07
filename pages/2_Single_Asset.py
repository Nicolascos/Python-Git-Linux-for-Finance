import streamlit as st
import pandas as pd

from modules.data_loader import get_live_price, load_historical_data
from modules.strategy_single import (
    strategy_buy_and_hold,
    strategy_sma,
    strategy_rsi,
    strategy_macd,
    strategy_bollinger,
    strategy_golden_cross,
    compute_metrics,
)
from modules.preprocessing import build_gated_equity, prepare_ohlc_df, slice_by_date_window
from modules.plots import plot_equity_gated


# =========================================================
# PAGE — SINGLE ASSET
# =========================================================
st.title("📈 Analyse d’un Actif Unique — Quant A")

# ------------------------------
# Sidebar paramètres
# ------------------------------
st.sidebar.subheader("⚙️ Paramètres de l’analyse")

ticker_dict = {
    "Actions US 🇺🇸": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "Crypto(prix pas à jour) 💎": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Indices 📈": ["^GSPC", "^DJI", "^IXIC"],
}

categorie = st.sidebar.selectbox("Catégorie d’actifs :", list(ticker_dict.keys()))
symbol = st.sidebar.selectbox("Ticker :", ticker_dict[categorie])

strategy_choice = st.sidebar.selectbox(
    "Stratégie :",
    ["Buy & Hold", "SMA Momentum", "RSI", "MACD", "Bollinger", "Golden Cross"],
)

# Defaults (évite short/long/bb_* non définis)
short, long = 20, 50
bb_window, bb_std = 20, 2.0

# Paramètres spécifiques SMA
if strategy_choice == "SMA Momentum":
    short = st.sidebar.number_input("SMA courte (jours) :", 5, 100, 20)
    long = st.sidebar.number_input("SMA longue (jours) :", 20, 300, 50)

# Paramètres spécifiques Bollinger
if strategy_choice == "Bollinger":
    bb_window = st.sidebar.number_input("Fenêtre (jours) :", 10, 100, 20)
    bb_std = st.sidebar.slider("Écarts-types :", 1.0, 3.0, 2.0, step=0.1)

lookback = st.sidebar.slider(
    "Nombre de jours d’historique",
    min_value=100,
    max_value=3000,
    value=365,
    step=50,
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

df = load_historical_data(symbol, lookback_days=lookback)

if df is None or df.empty:
    st.error(f"❌ Impossible de récupérer des données historiques pour {symbol}.")
    st.stop()

df = prepare_ohlc_df(df)


# ------------------------------
# 1.b Fenêtre (Date d'entrée / sortie)
# ------------------------------
st.sidebar.subheader("📅 Période d'analyse")

min_d = df["Date"].min().date()
max_d = df["Date"].max().date()

start_d, end_d = st.sidebar.slider(
    "Date d'entrée / sortie",
    min_value=min_d,
    max_value=max_d,
    value=(min_d, max_d),
    format="YYYY-MM-DD",
)

try:
    df_slice = slice_by_date_window(df, start_d, end_d, min_points=30)
except ValueError:
    st.warning("⚠️ Période trop courte (minimum ~30 jours conseillé).")
    st.stop()




# ------------------------------
# 2. Application des stratégies
# ------------------------------


# Buy & Hold
df_bh_full = strategy_buy_and_hold(df)      # pour BH global / visu
df_bh = strategy_buy_and_hold(df_slice)     # pour comparaison sur fenêtre

# Stratégie choisie
if strategy_choice == "Buy & Hold":
    df_strat = df_bh.copy()
    

elif strategy_choice == "SMA Momentum":
    df_strat = strategy_sma(df_slice, short=short, long=long)
    

elif strategy_choice == "RSI":
    df_strat = strategy_rsi(df_slice)

elif strategy_choice == "MACD":
    df_strat = strategy_macd(df_slice)

elif strategy_choice == "Bollinger":
    df_strat = strategy_bollinger(df_slice, window=bb_window, num_std=bb_std)

elif strategy_choice == "Golden Cross":
    df_strat = strategy_golden_cross(df_slice)

# Courbe “gated” (BH -> Stratégie -> BH scalé)
df_strat_gated, start_ts_eff, end_ts_eff = build_gated_equity(df, df_strat, start_d, end_d)


# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3 = st.tabs(["📊 Performance", "⚡ Comparaison", "🔮 Prédiction"])

with tab1:
    # Prix live
    live_price = get_live_price(symbol)
    if live_price is not None:
        st.subheader(f"🏷️ Prix Actuel {symbol} : **{live_price:,.2f} $**")
        st.markdown("---")
    else:
        st.error(f"❌ Impossible de récupérer le prix live pour {symbol}.")

    # Données historiques
    st.subheader("📡 Données historiques")
    st.success(
        f"Données chargées pour {symbol} du {df['Date'].iloc[0].date()} au {df['Date'].iloc[-1].date()}"
    )
    st.dataframe(df.tail(), use_container_width=True)

    # Info période
    st.info(f"📆 Analyse sur la période : {start_d} → {end_d} ({len(df_slice)} points)")

    # Stratégie utilisée
    st.subheader("🧠 Stratégie appliquée")
    if strategy_choice == "SMA Momentum":
        st.write(f"Stratégie utilisée : **{strategy_choice}** — courte={short}, longue={long}")
    elif strategy_choice == "Bollinger":
        st.write(f"Stratégie utilisée : **{strategy_choice}** — window={bb_window}, std={bb_std}")
    else:
        st.write(f"Stratégie utilisée : **{strategy_choice}**")

    # Graph principal
    st.subheader("📈 Performance — Stratégie vs Buy & Hold")
    fig_equity = plot_equity_gated(
        df_strat_gated=df_strat_gated,
        start_ts_eff=start_ts_eff,
        end_ts_eff=end_ts_eff,
        title="Comparaison des stratégies",
    )
    st.plotly_chart(fig_equity, use_container_width=True, key="equity_main")
    st.caption(
        "Après la date de sortie, le portefeuille repasse en Buy&Hold en conservant la performance atteinte à la sortie."
    )

    # Metrics cards
    st.subheader("📊 Indicateurs quantitatifs")

    metrics_strat = compute_metrics(df_strat)
    metrics_bh = compute_metrics(df_bh)

    total_perf_strat = df_strat["Strategy"].iloc[-1] - 1
    total_perf_bh = df_bh["Strategy"].iloc[-1] - 1

    col1, col2, col3, col4, col5 = st.columns(5)

    sharpe_delta = metrics_strat["Sharpe Ratio"] - metrics_bh["Sharpe Ratio"]
    col1.metric("Sharpe Ratio", f"{metrics_strat['Sharpe Ratio']:.3f}", delta=f"{sharpe_delta:.3f} vs B&H")

    dd_strat_display = f"{metrics_strat['Max Drawdown']*100:.2f}%"
    dd_bh_display = f"{metrics_bh['Max Drawdown']*100:.2f}%"
    col2.metric("Max Drawdown", dd_strat_display, delta=f"B&H: {dd_bh_display}")

    vol_delta = metrics_strat["Volatility (ann.)"] - metrics_bh["Volatility (ann.)"]
    col3.metric("Volatilité (ann.)", f"{metrics_strat['Volatility (ann.)']:.2%}", delta=f"{vol_delta:.2%} vs B&H")

    perf_delta = total_perf_strat - total_perf_bh
    col4.metric("Gain Total", f"{total_perf_strat*100:.2f} %", delta=f"{perf_delta*100:.2f} % vs B&H")

    sortino_delta = metrics_strat["Sortino"] - metrics_bh["Sortino"]
    col5.metric("Sortino Ratio", f"{metrics_strat['Sortino']:.3f}", delta=f"{sortino_delta:.3f} vs B&H")

# =========================================================
# 🔥 COMPARAISON MULTI-STRATÉGIES
# =========================================================

df_sma = strategy_sma(df_slice, short=20, long=50)
df_rsi = strategy_rsi(df_slice)
df_macd = strategy_macd(df_slice)
df_bb = strategy_bollinger(df_slice, window=20, num_std=2)
df_gc = strategy_golden_cross(df_slice)

df_compare = pd.DataFrame(
    {
        "Buy & Hold": df_bh["Strategy"].values,
        "SMA": df_sma["Strategy"].values,
        "RSI": df_rsi["Strategy"].values,
        "MACD": df_macd["Strategy"].values,
        "Bollinger": df_bb["Strategy"].values,
        "Golden Cross": df_gc["Strategy"].values,
    },
    index=pd.to_datetime(df_slice["Date"]),
)

# conseillé : enlever les lignes incomplètes (rolling windows)
df_compare = df_compare.dropna(how="any")


# =========================================================
# 📊 TABLEAU DES METRICS POUR TOUTES LES STRATÉGIES
# =========================================================


strategies_results = {
    "Buy & Hold": df_bh,
    "SMA": df_sma,
    "RSI": df_rsi,
    "MACD": df_macd,
    "Bollinger": df_bb,
    "Golden Cross": df_gc,
}

table_stats = []
for name, df_s in strategies_results.items():
    metrics = compute_metrics(df_s)
    table_stats.append(
        {
            "Stratégie": name,
            "Sharpe Ratio": metrics["Sharpe Ratio"],
            "Sortino Ratio": metrics["Sortino"],
            "Volatilité (ann.)": metrics["Volatility (ann.)"],
            "Max Drawdown": metrics["Max Drawdown"],
            "Performance totale (%)": (df_s["Strategy"].iloc[-1] - 1) * 100,
        }
    )

df_stats = (
    pd.DataFrame(table_stats)
    .set_index("Stratégie")
    .sort_values("Sharpe Ratio", ascending=False)
)


with tab2:
    st.subheader("⚡ Comparaison Multi-Stratégies")
    st.line_chart(df_compare)

    st.subheader("📘 Tableau de synthèse des performances")
    st.dataframe(df_stats, use_container_width=True)


with tab3:
    st.subheader("🔮 Prédiction")
    st.info("À venir.")

