import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from modules.data_loader import get_live_price
from modules.portfolio import load_multi_prices, build_portfolio_close,apply_segments_to_portfolio
from modules.data_loader import load_historical_data
from modules.preprocessing import prepare_ohlc_df, slice_by_date_window
from modules.strategy_single import (
    strategy_buy_and_hold,
    strategy_sma,
    strategy_rsi,
    strategy_macd,
    strategy_bollinger,
    strategy_golden_cross,
    compute_metrics,
)
from modules.plots import plot_equity_segments
import json
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA
from modules.predictions_portfolio import (
    make_features_portfolio,
    train_test_split_time_portfolio,
    rf_predict_with_ci_portfolio,
    linear_predict_with_ci_portfolio,
    returns_to_portfolio_path,
    rollout_one_step_portfolio,
    rf_rollout_paths_fast_portfolio,
)
from scipy.stats import norm
import plotly.express as px



st.title("📊 Portfolio — Multi-Actifs")

tab1, tab2, tab3, tab4 = st.tabs(["🧱 Création", "📈 Stratégies", "⚡ Simulations", "🛡️ Risques & 🔮 Prédiction"])


ticker_dict = {
    "Actions US 🇺🇸": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "Crypto 💎": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Indices 📈": ["^GSPC", "^DJI", "^IXIC"],
}
all_tickers = sorted({t for v in ticker_dict.values() for t in v})


with tab1:
    st.subheader("🧱 Création du portefeuille")

    if "alloc_df" not in st.session_state:
        st.session_state["alloc_df"] = pd.DataFrame(
            [{"symbol": "AAPL", "amount_eur": 2000.0}]
        )

    # --- Edition principale
    edited = st.data_editor(
        st.session_state["alloc_df"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=["symbol", "amount_eur"],
        column_config={
            "symbol": st.column_config.SelectboxColumn(
                "Ticker",
                options=all_tickers,
                required=True,
            ),
            "amount_eur": st.column_config.NumberColumn(
                "Montant investi (€)",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                required=True,
            ),
        },
        key="alloc_editor",
    )
    st.session_state["alloc_df"] = edited.copy()

    df_alloc = edited.copy()
    df_alloc["symbol"] = df_alloc["symbol"].astype(str).str.strip()
    df_alloc["amount_eur"] = pd.to_numeric(df_alloc["amount_eur"], errors="coerce")

    df_alloc = df_alloc.dropna(subset=["symbol", "amount_eur"])
    df_alloc = df_alloc[df_alloc["symbol"] != ""]
    df_alloc = df_alloc[df_alloc["amount_eur"] > 0]
    df_alloc = df_alloc.reset_index(drop=True)

    if df_alloc.empty:
        st.info("Ajoute au moins un actif avec un montant > 0.")
        st.stop()

    if df_alloc["symbol"].duplicated().any():
        st.warning("⚠️ Tickers en double détectés. Clique sur 'Fusionner doublons (somme)'.")

    total_value = float(df_alloc["amount_eur"].sum())
    df_alloc["weight"] = df_alloc["amount_eur"] / total_value
    
    alloc_signature = json.dumps(
        df_alloc.sort_values("symbol")[["symbol","amount_eur"]].to_dict(orient="records"),
        sort_keys=True
    )

    prev_sig = st.session_state.get("alloc_signature")

    if prev_sig != alloc_signature:
        st.session_state["alloc_signature"] = alloc_signature

        # (optionnel) reset segments quand on change de portefeuille
        st.session_state["segments_list"] = []
        st.session_state["segments_df_clean"] = pd.DataFrame()

        # force rerun pour reconstruire df_portfolio avec la nouvelle alloc
        st.rerun()

    # --- KPI ligne propre
    c1, c2, c3 = st.columns([1.2, 1, 1])
    c1.metric("Valeur totale du portefeuille", f"{total_value:,.2f} €")
    c2.metric("Nombre d'actifs", f"{len(df_alloc)}")
    c3.metric("Poids max", f"{(df_alloc['weight'].max()*100):.1f}%")

    b1, b2 = st.columns(2)

    with b1:
        if st.button("⚖️ Égal-pondérer (garde le total)", use_container_width=True):
            equal_amount = total_value / len(df_alloc)
            df_alloc["amount_eur"] = equal_amount
            st.session_state["alloc_df"] = df_alloc[["symbol", "amount_eur"]].copy()
            st.rerun()

    with b2:
        if st.button("🧹 Fusionner doublons (somme)", use_container_width=True):
            df_alloc2 = df_alloc.groupby("symbol", as_index=False)["amount_eur"].sum()
            st.session_state["alloc_df"] = df_alloc2.copy()
            st.rerun()



     
    # --- Détails "jolis"
    with st.expander("Détails (poids / prix / quantités)", expanded=True):
        # live prices (peut être None parfois)
        prices = [get_live_price(s) for s in df_alloc["symbol"]]
        df_alloc["live_price"] = prices

        # qty estimée si prix dispo
        p = pd.to_numeric(df_alloc["live_price"], errors="coerce")
        df_alloc["qty_est"] = np.where(
            (p.notna()) & (p > 0),
            df_alloc["amount_eur"] / p,
            np.nan,
        )

        # table display formatée
        df_show = df_alloc.copy()
        df_show["weight"] = (df_show["weight"] * 100).round(2)
        df_show["amount_eur"] = df_show["amount_eur"].round(2)
        df_show["live_price"] = df_show["live_price"].round(4)
        df_show["qty_est"] = df_show["qty_est"].round(4)

        df_show = df_show.rename(
            columns={
                "symbol": "Ticker",
                "amount_eur": "Montant (€)",
                "weight": "Poids (%)",
                "live_price": "Prix live",
                "qty_est": "Qté estimée",
            }
        )

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
        )

        # mini pie chart allocation
        fig = go.Figure(
        data=[
            go.Pie(
                labels=df_alloc["symbol"],
                values=df_alloc["amount_eur"],  # <- ici
                hole=0.5,
            )
        ])

        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig, use_container_width=True)

        df_sorted = df_alloc.sort_values("amount_eur", ascending=True)
        fig_bar = go.Figure(
            data=[go.Bar(x=df_sorted["amount_eur"], y=df_sorted["symbol"], orientation="h")]
        )
        fig_bar.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_bar, use_container_width=True)


# =========================
# BUILD PORTFOLIO DATA (shared for tab2 & tab3)
# =========================
symbols = df_alloc["symbol"].tolist()

lookback_pf = st.sidebar.slider(
    "Lookback historique portefeuille (jours)",
    min_value=200,
    max_value=5000,
    value=1500,
    step=100,
    key="pf_lookback",
)


@st.cache_data(show_spinner=False)
def load_multi_prices_cached(symbols_tuple, lookback_pf):
    return load_multi_prices(
        load_historical_data_fn=load_historical_data,
        prepare_ohlc_df_fn=prepare_ohlc_df,
        symbols=list(symbols_tuple),
        lookback_days=lookback_pf,
    )

symbols_tuple = tuple(df_alloc["symbol"].tolist())

df_prices_long = load_multi_prices_cached(symbols_tuple, lookback_pf)
df_portfolio = build_portfolio_close(df_prices_long, df_alloc)

strategy_map = {
    "Buy & Hold": strategy_buy_and_hold,
    "SMA Momentum": strategy_sma,
    "RSI": strategy_rsi,
    "MACD": strategy_macd,
    "Bollinger": strategy_bollinger,
    "Golden Cross": strategy_golden_cross,
}


# =========================
# TAB 2 — STRATEGIES (UI)
# =========================
with tab2:
    st.subheader("📈 Stratégies — Segments (timeline)")
    st.markdown("### 📅 Période globale de backtest (slider)")

    min_date = pd.to_datetime(df_portfolio["Date"]).min().date()
    max_date = pd.to_datetime(df_portfolio["Date"]).max().date()

    start_d, end_d = st.slider(
        "Fenêtre de backtest",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY/MM/DD",
        key="pf_backtest_slider",
    )

    if start_d >= end_d:
        st.error("⚠️ Fenêtre invalide.")
        st.stop()

    st.caption("Par défaut, hors segments, la stratégie est **Buy & Hold**.")

    # init state
    if "segments_list" not in st.session_state:
        st.session_state["segments_list"] = []  # list[dict]


    # -----------------------------
    # ➕ UI builder (ajout segment)
    # -----------------------------
    st.markdown("### ➕ Ajouter un segment")
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.6, 1.0])

    with c1:
        seg_start = st.date_input(
            "Début segment",
            value=start_d,
            min_value=start_d,
            max_value=end_d,
            key="seg_start_input",
        )

    with c2:
        seg_end = st.date_input(
            "Fin segment",
            value=end_d,
            min_value=start_d,
            max_value=end_d,
            key="seg_end_input",
        )

    with c3:
        seg_strategy = st.selectbox(
            "Stratégie",
            ["SMA Momentum", "RSI", "MACD", "Bollinger", "Golden Cross"],
            index=3,
            key="seg_strategy_select",
        )

    with c4:
        st.write("")
        st.write("")
        add_clicked = st.button("➕ Ajouter", use_container_width=True)

    # Params dynamiques (affichés seulement si besoin)
    params = {}
    if seg_strategy == "SMA Momentum":
        p1, p2 = st.columns(2)
        with p1:
            params["sma_short"] = st.number_input("SMA courte", 5, 100, 20, key="seg_sma_short")
        with p2:
            params["sma_long"] = st.number_input("SMA longue", 20, 300, 50, key="seg_sma_long")

    elif seg_strategy == "Bollinger":
        p1, p2 = st.columns(2)
        with p1:
            params["bb_window"] = st.number_input("BB window", 10, 100, 20, key="seg_bb_window")
        with p2:
            params["bb_std"] = st.slider("BB std", 1.0, 3.0, 2.0, 0.1, key="seg_bb_std")

    # -----------------------------
    # add segment (no overlap)
    # -----------------------------
    if add_clicked:
        if seg_start >= seg_end:
            st.error("⚠️ Segment invalide : début >= fin.")
        else:
            new_start = pd.to_datetime(seg_start).date()
            new_end = pd.to_datetime(seg_end).date()

            existing = pd.DataFrame(st.session_state["segments_list"])
            if not existing.empty:
                existing["start"] = pd.to_datetime(existing["start"]).dt.date
                existing["end"] = pd.to_datetime(existing["end"]).dt.date

                # overlap si intervals se croisent : (a < d) & (c < b)
                overlap_mask = (new_start < existing["end"]) & (existing["start"] < new_end)

                if overlap_mask.any():
                    last_end = existing.loc[overlap_mask, "end"].max()
                    st.error("🚫 Ce segment chevauche un segment existant.")
                    st.info(f"💡 Suggestion : mets le **début** du segment à {last_end} (juste après).")
                else:
                    st.session_state["segments_list"].append(
                        {"start": new_start, "end": new_end, "strategy": seg_strategy, **params}
                    )
                    st.success("✅ Segment ajouté.")
                    st.rerun()
            else:
                st.session_state["segments_list"].append(
                    {"start": new_start, "end": new_end, "strategy": seg_strategy, **params}
                )
                st.success("✅ Segment ajouté.")
                st.rerun()

    # -----------------------------
    # 🧩 Affichage "cards" + actions
    # -----------------------------
    st.markdown("### 🧩 Segments définis")
    segments = st.session_state["segments_list"]

    if not segments:
        st.info("Aucun segment → Buy & Hold sur toute la période.")
        st.session_state["segments_df_clean"] = pd.DataFrame()
    else:
        seg_df = pd.DataFrame(segments).copy()
        seg_df["start"] = pd.to_datetime(seg_df["start"]).dt.date
        seg_df["end"] = pd.to_datetime(seg_df["end"]).dt.date

        # clamp dans la fenêtre
        seg_df.loc[seg_df["start"] < start_d, "start"] = start_d
        seg_df.loc[seg_df["end"] > end_d, "end"] = end_d
        seg_df = seg_df.sort_values("start").reset_index(drop=True)

        # 🚫 INTERDICTION DES CHEVAUCHEMENTS
        overlaps = (seg_df["start"].shift(-1) < seg_df["end"])[:-1]
        if overlaps.any():
            i = overlaps[overlaps].index[0]
            st.error(
                f"🚫 Segments chevauchants détectés :\n\n"
                f"Segment {i+1}: {seg_df.loc[i,'start']} → {seg_df.loc[i,'end']}\n"
                f"Segment {i+2}: {seg_df.loc[i+1,'start']} → {seg_df.loc[i+1,'end']}\n\n"
                f"Règle: le segment suivant doit commencer **le jour de fin ou après**."
            )
            st.session_state["segments_df_clean"] = pd.DataFrame()
            seg_df = None

        if seg_df is not None:
            for i, row in seg_df.iterrows():
                left, _, right = st.columns([6, 2, 2])

                with left:
                    st.markdown(f"**{row['strategy']}** — {row['start']} → {row['end']}")
                    extras = []

                    sma_s = row.get("sma_short", np.nan)
                    sma_l = row.get("sma_long", np.nan)
                    if pd.notna(sma_s) and pd.notna(sma_l):
                        extras.append(f"SMA({int(sma_s)},{int(sma_l)})")

                    bb_w = row.get("bb_window", np.nan)
                    bb_s = row.get("bb_std", np.nan)
                    if pd.notna(bb_w) and pd.notna(bb_s):
                        extras.append(f"BB(window={int(bb_w)}, std={float(bb_s)})")

                    if extras:
                        st.caption(" · ".join(extras))

                with right:
                    if st.button("🗑️ Supprimer", key=f"del_seg_{i}", use_container_width=True):
                        new_list = seg_df.drop(index=i).to_dict(orient="records")
                        st.session_state["segments_list"] = new_list
                        st.rerun()

            st.session_state["segments_df_clean"] = seg_df.copy()

    # -----------------------------
    # Actions rapides
    # -----------------------------
    st.markdown("---")
    cA, cB = st.columns([1, 1])
    with cA:
        if st.button("🧹 Reset segments", use_container_width=True):
            st.session_state["segments_list"] = []
            st.session_state["segments_df_clean"] = pd.DataFrame()
            st.rerun()
    with cB:
        st.caption("Prochain step: appliquer ces segments aux stratégies asset-par-asset puis agréger le portefeuille.")


with tab3:
    st.subheader("📊 Backtest — Portefeuille vs Buy & Hold")

    start_d = st.session_state.get("pf_backtest_slider", (None, None))[0]
    end_d   = st.session_state.get("pf_backtest_slider", (None, None))[1]

    if start_d is None or end_d is None:
        st.info("Choisis d'abord une fenêtre de backtest dans l'onglet Stratégies.")
        st.stop()

    try:
        df_pf_slice = slice_by_date_window(df_portfolio, start_d, end_d, min_points=30)
    except ValueError:
        st.warning("⚠️ Fenêtre trop courte (minimum ~30 jours conseillé).")
        st.stop()

    # 1) Stratégie segmentée (doit renvoyer Date/BH/Strategy)
    seg_clean = st.session_state.get("segments_df_clean", pd.DataFrame())
    df_pf_strat = apply_segments_to_portfolio(
        df_pf_slice,
        segments_df=seg_clean,
        strategy_map=strategy_map,
    )

    # 2) Buy & Hold cohérent (même Date/index)
    df_pf_bh = df_pf_strat.copy()
    df_pf_bh["Strategy"] = df_pf_bh["BH"]


    # 3) Plot
    st.markdown("### 📈 Equity curve")
    df_plot = pd.DataFrame({
        "Date": pd.to_datetime(df_pf_strat["Date"]),
        "BH": df_pf_strat["BH"].values,
        "Strategy": df_pf_strat["Strategy"].values,
    })

    fig = plot_equity_segments(
        df_curve=df_plot,
        segments_df=seg_clean,
        title="Comparaison des stratégies",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 4) Metrics
    st.markdown("### 📊 Indicateurs (vs Buy & Hold)")
    metrics_strat = compute_metrics(df_pf_strat)
    metrics_bh = compute_metrics(df_pf_bh)

    total_perf_strat = df_pf_strat["Strategy"].iloc[-1] - 1
    total_perf_bh = df_pf_bh["Strategy"].iloc[-1] - 1

    col1, col2, col3, col4, col5 = st.columns(5)

    sharpe_delta = metrics_strat["Sharpe Ratio"] - metrics_bh["Sharpe Ratio"]
    col1.metric("Sharpe", f"{metrics_strat['Sharpe Ratio']:.3f}", delta=f"{sharpe_delta:.3f} vs B&H")

    dd_strat_display = f"{metrics_strat['Max Drawdown']*100:.2f}%"
    dd_bh_display = f"{metrics_bh['Max Drawdown']*100:.2f}%"
    col2.metric("Max DD", dd_strat_display, delta=f"B&H: {dd_bh_display}")

    vol_delta = metrics_strat["Volatility (ann.)"] - metrics_bh["Volatility (ann.)"]
    col3.metric("Vol (ann.)", f"{metrics_strat['Volatility (ann.)']:.2%}", delta=f"{vol_delta:.2%} vs B&H")

    perf_delta = total_perf_strat - total_perf_bh
    col4.metric("Perf totale", f"{total_perf_strat*100:.2f} %", delta=f"{perf_delta*100:.2f} % vs B&H")

    sortino_delta = metrics_strat["Sortino"] - metrics_bh["Sortino"]
    col5.metric("Sortino", f"{metrics_strat['Sortino']:.3f}", delta=f"{sortino_delta:.3f} vs B&H")


with tab4:
    st.subheader("🛡️ Risques & 🔮 Prédiction (Portefeuille)")

    # ---- même fenêtre que tab2
    start_d = st.session_state.get("pf_backtest_slider", (None, None))[0]
    end_d   = st.session_state.get("pf_backtest_slider", (None, None))[1]
    if start_d is None or end_d is None:
        st.info("Choisis d'abord une fenêtre de backtest dans l'onglet Stratégies.")
        st.stop()

    try:
        df_pf_slice = slice_by_date_window(df_portfolio, start_d, end_d, min_points=60)
    except ValueError:
        st.warning("⚠️ Fenêtre trop courte (minimum ~60 jours conseillé pour risques & prédiction).")
        st.stop()

    df_pf_slice = df_pf_slice.sort_values("Date").reset_index(drop=True)

    # =========================================================
    # A) RISQUES
    # =========================================================
    st.markdown("## 🛡️ Risques")

    # --- utiliser la même equity que Tab3 : Strategy segmentée ---
    seg_clean = st.session_state.get("segments_df_clean", pd.DataFrame())
    df_pf_strat = apply_segments_to_portfolio(
        df_pf_slice,
        segments_df=seg_clean,
        strategy_map=strategy_map,
    )

    # --- réutilise EXACTEMENT les métriques de compute_metrics (comme Tab3) ---
    metrics_strat = compute_metrics(df_pf_strat)
    ann_vol = metrics_strat["Volatility (ann.)"]
    sharpe  = metrics_strat["Sharpe Ratio"]
    max_dd  = metrics_strat["Max Drawdown"]

    # returns (log) sur la courbe Strategy (pour VaR/CVaR + histogramme)
    r = np.log(df_pf_strat["Strategy"]).diff().dropna()
    if len(r) < 30:
        st.warning("Pas assez de points pour calculer les risques.")
        st.stop()

    # Rendement ann. (moy) : on garde ton calcul MVP (moyenne des log-returns annualisée)
    ann_ret = r.mean() * 252

    # Drawdown série (pour le graphique)
    close = df_pf_strat["Strategy"].values
    peak = np.maximum.accumulate(close)
    dd = close / peak - 1.0

    # VaR / CVaR (historique) sur Strategy
    alpha = st.slider("Niveau de confiance VaR/CVaR", 0.90, 0.99, 0.95, 0.01)
    q = np.quantile(r, 1 - alpha)          # quantile côté pertes
    var = -q
    cvar = -(r[r <= q].mean()) if (r <= q).any() else np.nan

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Volatilité ann.", f"{ann_vol:.2%}")
    c2.metric("Rendement ann. (moy)", f"{ann_ret:.2%}")
    c3.metric("Sharpe (simple)", f"{sharpe:.2f}")
    c4.metric("Max Drawdown", f"{max_dd:.2%}")
    c5.metric(f"VaR {int(alpha*100)}%", f"{var:.2%}")

    st.caption("VaR/CVaR = calcul historique sur log-returns journaliers. Sharpe ici sans taux sans risque (MVP).")

    # mini charts
    st.markdown("### 📉 Drawdown")
    dd_df = pd.DataFrame({"Date": pd.to_datetime(df_pf_strat["Date"].iloc[1:]), "Drawdown": dd[1:]})
    st.line_chart(dd_df.set_index("Date"))

    st.markdown("### 📊 Distribution des returns")
    
    # Création de l'histogramme
    fig_hist = px.histogram(
        x=r, 
        nbins=50, 
        labels={'x': 'Log-Returns', 'y': 'Fréquence'},
        opacity=0.75,
        color_discrete_sequence=["#3b82f6"] # Bleu moderne
    )

    # Ajout de la ligne verticale pour la VaR (Zone de risque)
    # q a été calculé plus haut : q = np.quantile(r, 1 - alpha)
    fig_hist.add_vline(
        x=q, 
        line_width=2, 
        line_dash="dash", 
        line_color="#ef4444", # Rouge
        annotation_text=f"VaR {int(alpha*100)}%", 
        annotation_position="top left"
    )

    # Ajout de la ligne pour la Moyenne
    fig_hist.add_vline(
        x=r.mean(), 
        line_width=2, 
        line_dash="dot", 
        line_color="#22c55e", # Vert
        annotation_text="Moyenne", 
        annotation_position="top right"
    )

    fig_hist.update_layout(
        title={
            'text': "Distribution des rendements & Seuil de risque",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        bargap=0.1, # Espace entre les barres
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20)
    )

    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")

    # =========================================================
    # B) PRÉDICTION (copie Single Asset mais entrée = df_pf_slice)
    # =========================================================
    st.markdown("## 🔮 Prédiction (Portefeuille)")

    horizon = st.selectbox("Horizon (jours)", [1, 5, 10, 20], index=0, key="pf_pred_h")
    n_lags = st.slider("Lags (features)", 1, 20, 5, key="pf_pred_lags")
    test_size = st.slider("Taille zone test (%)", 10, 40, 20, key="pf_pred_test") / 100
    future_steps = st.slider("Projection future (jours)", 5, 60, 20, key="pf_pred_steps")

    # réutilise EXACTEMENT tes fonctions du single asset:
    # make_features, train_test_split_time, rf_predict_with_ci, linear_predict_with_ci,
    # returns_to_price_path, rollout_one_step, rf_rollout_paths_fast

    X, y, dates, close_t, close_th = make_features_portfolio(df_pf_slice, horizon=horizon, n_lags=n_lags)

    if len(X) < 120:
        st.warning("Pas assez de données pour faire test + futur. Augmente la fenêtre.")
        st.stop()

    X_train, X_test, y_train, y_test, d_train, d_test = train_test_split_time_portfolio(X, y, dates, test_size=test_size)
    split_idx = int(len(X) * (1 - test_size))
    close_t_test = close_t.iloc[split_idx:]
    close_th_test = close_th.iloc[split_idx:]

    model_choice = st.selectbox("Modèle", ["ARIMA", "Linéaire", "Random Forest"], index=0, key="pf_pred_model")
    alpha_ci = 0.05  # 95%

    st.markdown("### ✅ Zone TEST (réel vs prédiction)")

    if model_choice == "Linéaire":
        lin = LinearRegression()
        lin.fit(X_train, y_train)
        y_pred, y_lo, y_hi = linear_predict_with_ci_portfolio(lin, X_train, y_train, X_test, alpha=alpha_ci)

    elif model_choice == "Random Forest":
        rf = RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)
        y_pred, y_lo, y_hi = rf_predict_with_ci_portfolio(rf, X_test, alpha=alpha_ci)

    else:
        order = st.selectbox("ARIMA(p,d,q)", [(1,0,1), (2,0,2), (5,0,0), (1,0,0)], index=0, key="pf_arima_test")
        arima = ARIMA(y_train.reset_index(drop=True), order=order)
        fit = arima.fit()
        fc = fit.get_forecast(steps=len(y_test))
        y_pred = fc.predicted_mean.values
        ci = fc.conf_int(alpha=alpha_ci)
        y_lo = ci.iloc[:, 0].values
        y_hi = ci.iloc[:, 1].values

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    hit = (np.sign(y_test.values) == np.sign(y_pred)).mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("MAE (retours)", f"{mae:.6f}")
    c2.metric("RMSE (retours)", f"{rmse:.6f}")
    c3.metric("Hit rate (direction)", f"{hit*100:.1f}%")

    pred_price = close_t_test * np.exp(y_pred)
    lo_price   = close_t_test * np.exp(y_lo)
    hi_price   = close_t_test * np.exp(y_hi)

    real_price = close_th_test
    d_test_plot = d_test

    fig_test = go.Figure()
    fig_test.add_trace(go.Scatter(x=d_test_plot, y=real_price, name=f"Réel (Close t+{horizon})", mode="lines"))
    fig_test.add_trace(go.Scatter(x=d_test_plot, y=pred_price, name="Prédiction", mode="lines"))
    fig_test.add_trace(go.Scatter(
        x=np.concatenate([d_test_plot, d_test_plot[::-1]]),
        y=np.concatenate([hi_price, lo_price[::-1]]),
        fill="toself", name="IC 95%", mode="lines", line=dict(width=0), opacity=0.2,
    ))
    st.plotly_chart(fig_test, use_container_width=True)

    st.markdown("### 🔭 Futur (projection + IC 95%)")

    last_price = df_pf_slice["Close"].iloc[-1]
    last_date = pd.to_datetime(df_pf_slice["Date"].iloc[-1])
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=future_steps, freq="B")

    if model_choice == "Linéaire":
        lin = LinearRegression()
        lin.fit(X, y)

        cols = list(X.columns)
        x_curr = X.iloc[-1].values.astype(float).reshape(1, -1)

        y_f = []
        for _ in range(future_steps):
            r_hat = float(lin.predict(x_curr)[0])
            y_f.append(r_hat)
            x_curr = rollout_one_step_portfolio(x_curr, np.array([r_hat]), cols)
        y_f = np.array(y_f)

        y_hat_train = lin.predict(X)
        sigma = (y.values - y_hat_train).std(ddof=1)
        z = norm.ppf(1 - alpha_ci/2)
        y_f_lo = y_f - z * sigma
        y_f_hi = y_f + z * sigma

    elif model_choice == "Random Forest":
        rf = RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)
        rf.fit(X, y)
        paths = rf_rollout_paths_fast_portfolio(rf, X.iloc[-1], steps=future_steps, n_paths=80)

        y_f = paths.mean(axis=0)
        y_f_lo = np.quantile(paths, alpha_ci/2, axis=0)
        y_f_hi = np.quantile(paths, 1 - alpha_ci/2, axis=0)

    else:
        order = st.selectbox("ARIMA(p,d,q) (futur)", [(1,0,1), (2,0,2), (5,0,0), (1,0,0)], index=0, key="pf_arima_future")
        arima = ARIMA(y.reset_index(drop=True), order=order)
        fit = arima.fit()
        fc = fit.get_forecast(steps=future_steps)
        y_f = fc.predicted_mean.values
        ci = fc.conf_int(alpha=alpha_ci)
        y_f_lo = ci.iloc[:, 0].values
        y_f_hi = ci.iloc[:, 1].values

    y_f_daily = y_f / horizon
    y_f_lo_daily = y_f_lo / horizon
    y_f_hi_daily = y_f_hi / horizon

    future_price = returns_to_portfolio_path(last_price, y_f_daily)
    future_price_lo = returns_to_portfolio_path(last_price, y_f_lo_daily)
    future_price_hi = returns_to_portfolio_path(last_price, y_f_hi_daily)
    
    hist_tail = df_pf_slice.tail(min(120, len(df_pf_slice)))
    fig_future = go.Figure()
    fig_future.add_trace(go.Scatter(x=pd.to_datetime(hist_tail["Date"]), y=hist_tail["Close"], name="Historique", mode="lines"))
    fig_future.add_trace(go.Scatter(x=future_dates, y=future_price, name=f"{model_choice} (prévision)", mode="lines"))
    fig_future.add_trace(go.Scatter(
        x=np.concatenate([future_dates, future_dates[::-1]]),
        y=np.concatenate([future_price_hi, future_price_lo[::-1]]),
        fill="toself", name="Zone de Confiance 95%", mode="lines", line=dict(width=0), opacity=0.2
    ))
    st.plotly_chart(fig_future, use_container_width=True)

    st.caption("IC rigoureux pour ARIMA. Pour Linéaire/RF : intervalle empirique (résidus/arbres) — MVP.")
