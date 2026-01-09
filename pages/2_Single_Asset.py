import streamlit as st
import pandas as pd
from modules.ai_reco import best_params_by_sortino
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
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import plotly.graph_objects as go
from scipy.stats import norm
from modules.prediction import (
    make_features,
    train_test_split_time,
    rf_rollout_paths_fast,
    rollout_one_step,
    returns_to_price_path,
    rf_predict_with_ci,
    linear_predict_with_ci
)

# =========================================================
# PAGE — SINGLE ASSET
# =========================================================
st.title("📈 Analyse d’un Actif Unique — Quant A")

# ------------------------------
# Sidebar paramètres
# ------------------------------
st.sidebar.subheader("⚙️ Paramètres de l’analyse")

# Univers d'actifs / tickers disponibles
ticker_dict = {
    "Actions US 🇺🇸": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "Crypto(prix pas à jour) 💎": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Indices 📈": ["^GSPC", "^DJI", "^IXIC"],
}

categorie = st.sidebar.selectbox("Catégorie d’actifs :", list(ticker_dict.keys()))
symbol = st.sidebar.selectbox("Ticker :", ticker_dict[categorie])

# Choix de stratégie (affiche ensuite les paramètres associés)
strategy_choice = st.sidebar.selectbox(
    "Stratégie :",
    ["Buy & Hold", "SMA Momentum", "RSI", "MACD", "Bollinger", "Golden Cross"],
)

# Valeurs par défaut (évite variables non définies selon le choix)
short, long = 20, 50
bb_window, bb_std = 20, 2.0

# Paramètres spécifiques SMA
if strategy_choice == "SMA Momentum":
    short = st.sidebar.number_input("SMA courte (jours) :", 5, 100, 20, key="sma_short")
    long = st.sidebar.number_input("SMA longue (jours) :", 20, 300, 50, key="sma_long")

# Paramètres spécifiques Bollinger
if strategy_choice == "Bollinger":
    bb_window = st.sidebar.number_input("Fenêtre (jours) :", 10, 100, 20, key="bb_window")
    bb_std = st.sidebar.slider("Écarts-types :", 1.0, 3.0, 2.0, step=0.1, key="bb_std")

# Profondeur d'historique à charger
lookback = st.sidebar.slider(
    "Nombre de jours d’historique",
    min_value=100,
    max_value=3000,
    value=365,
    step=50,
)

# ------------------------------
# 1. Chargement des données
# ------------------------------
df = load_historical_data(symbol, lookback_days=lookback)

# Stop propre si pas de données
if df is None or df.empty:
    st.error(f"❌ Impossible de récupérer des données historiques pour {symbol}.")
    st.stop()

# Normalisation OHLC + Date
df = prepare_ohlc_df(df)

# ------------------------------
# 1.b Fenêtre (Date d'entrée / sortie)
# ------------------------------
st.sidebar.subheader("📅 Période d'analyse")

min_d = df["Date"].min().date()
max_d = df["Date"].max().date()

# Sélection dates analyse
start_d = st.sidebar.date_input(
    "Début",
    value=min_d,
    min_value=min_d,
    max_value=max_d,
    format="YYYY/MM/DD",
)

end_d = st.sidebar.date_input(
    "Fin",
    value=max_d,
    min_value=min_d,
    max_value=max_d,
    format="YYYY/MM/DD",
)

# Garde-fou si l'utilisateur inverse les dates
if start_d > end_d:
    st.sidebar.error("⚠️ La date de début doit être avant la date de fin.")
    st.stop()

# Slice sur la période (min_points évite fenêtres trop courtes)
try:
    df_slice = slice_by_date_window(df, start_d, end_d, min_points=30)
except ValueError:
    st.warning("⚠️ Période trop courte (minimum ~30 jours conseillé).")
    st.stop()

# ------------------------------
# 💡 IA Suggestion (optimisation Sortino)
# ------------------------------
# Propose des paramètres optimaux uniquement pour SMA/Bollinger (grid search)
if strategy_choice in ("SMA Momentum", "Bollinger"):
    with st.sidebar.expander("💡 IA Suggestion", expanded=True):
        best_params, best_score = best_params_by_sortino(
            symbol=symbol,
            start_d=start_d,
            end_d=end_d,
            lookback=lookback,
            strategy_choice=strategy_choice,
        )

        # Affichage + application dans session_state (puis rerun)
        if best_params:
            formatted = ", ".join([f"{k}={v}" for k, v in best_params.items()])
            st.markdown(f"**{formatted}**  \n(Sortino: **{best_score:.2f}**)")
            if st.button("✅ Appliquer", key="apply_ai"):
                if strategy_choice == "SMA Momentum":
                    st.session_state["sma_short"] = int(best_params["short"])
                    st.session_state["sma_long"] = int(best_params["long"])
                elif strategy_choice == "Bollinger":
                    st.session_state["bb_window"] = int(best_params["bb_window"])
                    st.session_state["bb_std"] = float(best_params["bb_std"])
                st.rerun()
        else:
            st.caption("Aucune suggestion disponible (période/données insuffisantes).")

# ------------------------------
# 2. Application des stratégies
# ------------------------------
# Buy&Hold sur fenêtre et sur période complète (utile pour visu "gated")
df_bh_full = strategy_buy_and_hold(df)
df_bh = strategy_buy_and_hold(df_slice)

# Application de la stratégie choisie sur la fenêtre uniquement
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

# Courbe “gated” : BH avant -> stratégie pendant -> BH scalé après
df_strat_gated, start_ts_eff, end_ts_eff = build_gated_equity(df, df_strat, start_d, end_d)

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3 = st.tabs(["📊 Performance", "⚡ Comparaison", "🔮 Prédiction"])

with tab1:
    # Prix live (affichage informatif)
    live_price = get_live_price(symbol)
    if live_price is not None:
        st.subheader(f"🏷️ Prix Actuel {symbol} : **{live_price:,.2f} $**")
        st.markdown("---")
    else:
        st.error(f"❌ Impossible de récupérer le prix live pour {symbol}.")

    # Aperçu données
    st.subheader("📡 Données historiques")
    st.success(
        f"Données chargées pour {symbol} du {df['Date'].iloc[0].date()} au {df['Date'].iloc[-1].date()}"
    )
    st.dataframe(df.tail(), use_container_width=True)

    # Résumé période
    st.info(f"📆 Analyse sur la période : {start_d} → {end_d} ({len(df_slice)} points)")

    # Paramètres stratégie (si applicable)
    st.subheader("🧠 Stratégie appliquée")
    if strategy_choice == "SMA Momentum":
        st.write(f"Stratégie utilisée : **{strategy_choice}** — courte={short}, longue={long}")
    elif strategy_choice == "Bollinger":
        st.write(f"Stratégie utilisée : **{strategy_choice}** — window={bb_window}, std={bb_std}")
    else:
        st.write(f"Stratégie utilisée : **{strategy_choice}**")

    # Courbe equity principale
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

    # Métriques stratégie vs BH (sur fenêtre)
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
# Stratégies "baseline" calculées avec paramètres standards pour comparer
df_sma = strategy_sma(df_slice, short=20, long=50)
df_rsi = strategy_rsi(df_slice)
df_macd = strategy_macd(df_slice)
df_bb = strategy_bollinger(df_slice, window=20, num_std=2)
df_gc = strategy_golden_cross(df_slice)

# DataFrame des courbes (alignées sur Date)
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

# On enlève les lignes incomplètes (rolling windows)
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

# Construction table récap (métriques + perf totale)
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
    st.subheader("🔮 Prédiction — Test + Futur (avec incertitude)")

    horizon = st.selectbox("Horizon (jours)", [1, 5, 10, 20], index=0)
    n_lags = st.slider("Lags (features)", 1, 20, 5)
    test_size = st.slider("Taille zone test (%)", 10, 40, 20) / 100
    future_steps = st.slider("Projection future (jours)", 5, 60, 20)

    # Features/target : retours (log) + dates + close[t] / close[t+h]
    X, y, dates, close_t, close_th = make_features(df_slice, horizon=horizon, n_lags=n_lags)

    # Garde-fou : pas assez d'observations => pas de modèle
    if len(X) < 80:
        st.warning("Pas assez de données pour faire test + futur. Augmente la fenêtre.")
        st.stop()

    # Split temporel (train -> test)
    X_train, X_test, y_train, y_test, d_train, d_test = train_test_split_time(X, y, dates, test_size=test_size)
    split_idx = int(len(X) * (1 - test_size))
    close_t_train, close_t_test = close_t.iloc[:split_idx], close_t.iloc[split_idx:]
    close_th_train, close_th_test = close_th.iloc[:split_idx], close_th.iloc[split_idx:]

    model_choice = st.selectbox("Modèle", ["ARIMA", "Linéaire", "Random Forest"], index=0)
    alpha = 0.05  # 95%

    # --------------------------------------------------
    # A) ZONE TEST (réel vs prédiction)
    # --------------------------------------------------
    st.markdown("### ✅ Zone TEST (réel vs prédiction)")

    # Dernier prix train (utile si besoin de reconstruire un chemin)
    last_train_price = df_slice.loc[df_slice["Date"] <= d_train.iloc[-1], "Close"].iloc[-1]

    if model_choice == "Linéaire":
        lin = LinearRegression()
        lin.fit(X_train, y_train)
        y_pred, y_lo, y_hi = linear_predict_with_ci(lin, X_train, y_train, X_test, alpha=alpha)

    elif model_choice == "Random Forest":
        rf = RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)
        y_pred, y_lo, y_hi = rf_predict_with_ci(rf, X_test, alpha=alpha)

    else:
        # ARIMA sur y_train (retours)
        order = st.selectbox("ARIMA(p,d,q)", [(1,0,1), (2,0,2), (5,0,0), (1,0,0)], index=0)
        arima = ARIMA(y_train.reset_index(drop=True), order=order)
        fit = arima.fit()
        fc = fit.get_forecast(steps=len(y_test))
        y_pred = fc.predicted_mean.values
        ci = fc.conf_int(alpha=alpha)
        y_lo = ci.iloc[:, 0].values
        y_hi = ci.iloc[:, 1].values

    # Métriques sur retours
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    hit = (np.sign(y_test.values) == np.sign(y_pred)).mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("MAE (retours)", f"{mae:.6f}")
    c2.metric("RMSE (retours)", f"{rmse:.6f}")
    c3.metric("Hit rate (direction)", f"{hit*100:.1f}%")

    # Reconstruction en prix (cohérent avec y = log(Close[t+h] / Close[t]))
    pred_price = close_t_test * np.exp(y_pred)
    lo_price   = close_t_test * np.exp(y_lo)
    hi_price   = close_t_test * np.exp(y_hi)

    real_price = close_th_test
    d_test_plot = d_test

    # Plot : réel vs prédiction + intervalle
    fig_test = go.Figure()
    fig_test.add_trace(go.Scatter(
        x=d_test_plot, y=real_price,
        name=f"Réel (Close t+{horizon})", mode="lines"
    ))
    fig_test.add_trace(go.Scatter(
        x=d_test_plot, y=pred_price,
        name="Prédiction", mode="lines"
    ))
    fig_test.add_trace(go.Scatter(
        x=np.concatenate([d_test_plot, d_test_plot[::-1]]),
        y=np.concatenate([hi_price, lo_price[::-1]]),
        fill="toself",
        name="IC 95%",
        mode="lines",
        line=dict(width=0),
        opacity=0.2,
    ))
    st.plotly_chart(fig_test, use_container_width=True)

    # --------------------------------------------------
    # B) FUTUR + INTERVALLE
    # --------------------------------------------------
    st.markdown("### 🔭 Futur (projection + IC 95%)")

    # Base future : dates ouvrées + dernier prix connu
    last_price = df_slice["Close"].iloc[-1]
    last_date = pd.to_datetime(df_slice["Date"].iloc[-1])
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=future_steps, freq="B")

    if model_choice == "Linéaire":
        lin = LinearRegression()
        lin.fit(X, y)

        # Rollout multi-steps sur les features (lags)
        cols = list(X.columns)
        x_curr = X.iloc[-1].values.astype(float).reshape(1, -1)

        y_f = []
        for _ in range(future_steps):
            r_hat = float(lin.predict(x_curr)[0])
            y_f.append(r_hat)
            x_curr = rollout_one_step(x_curr, np.array([r_hat]), cols)
        y_f = np.array(y_f)

        # IC simple basé sur sigma résiduel (MVP)
        y_hat_train = lin.predict(X)
        sigma = (y.values - y_hat_train).std(ddof=1)
        z = norm.ppf(1 - alpha/2)
        y_f_lo = y_f - z * sigma
        y_f_hi = y_f + z * sigma

    elif model_choice == "Random Forest":
        rf = RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)
        rf.fit(X, y)

        # Paths bootstrap via arbres (intervalle empirique)
        paths = rf_rollout_paths_fast(rf, X.iloc[-1], steps=future_steps, n_paths=80)

        y_f = paths.mean(axis=0)
        y_f_lo = np.quantile(paths, alpha/2, axis=0)
        y_f_hi = np.quantile(paths, 1 - alpha/2, axis=0)

    else:
        # ARIMA sur y (retours) puis forecast direct + IC statsmodels
        order = st.selectbox(
            "ARIMA(p,d,q) (futur)",
            [(1,0,1), (2,0,2), (5,0,0), (1,0,0)],
            index=0,
            key="arima_future_order"
        )
        arima = ARIMA(y.reset_index(drop=True), order=order)
        fit = arima.fit()
        fc = fit.get_forecast(steps=future_steps)
        y_f = fc.predicted_mean.values
        ci = fc.conf_int(alpha=alpha)
        y_f_lo = ci.iloc[:, 0].values
        y_f_hi = ci.iloc[:, 1].values

    # Conversion retours -> chemin de prix
    future_price = returns_to_price_path(last_price, y_f)
    future_price_lo = returns_to_price_path(last_price, y_f_lo)
    future_price_hi = returns_to_price_path(last_price, y_f_hi)

    # Plot futur + historique récent
    hist_tail = df_slice.tail(min(120, len(df_slice)))
    fig_future = go.Figure()
    fig_future.add_trace(go.Scatter(
        x=pd.to_datetime(hist_tail["Date"]),
        y=hist_tail["Close"],
        name="Historique",
        mode="lines"
    ))
    fig_future.add_trace(go.Scatter(
        x=future_dates,
        y=future_price,
        name=f"{model_choice} (prévision)",
        mode="lines"
    ))
    fig_future.add_trace(go.Scatter(
        x=np.concatenate([future_dates, future_dates[::-1]]),
        y=np.concatenate([future_price_hi, future_price_lo[::-1]]),
        fill="toself",
        name="Zone de Confiance 95%",
        mode="lines",
        line=dict(width=0),
        opacity=0.2,
        showlegend=True,
    ))
    st.plotly_chart(fig_future, use_container_width=True)

    st.caption("Note: l'IC est rigoureux pour ARIMA. Pour Linéaire/RF, c'est un intervalle empirique basé sur résidus/arbres (MVP).")
