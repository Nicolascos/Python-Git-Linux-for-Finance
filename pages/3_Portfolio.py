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

st.title("📊 Portfolio — Multi-Actifs")

tab1, tab2, tab3 = st.tabs(["🧱 Création", "📈 Stratégies", "⚡ Simulations"])

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

    # -------------------------------------------------
    # 👀 Aperçu segments existants (visible AVANT ajout)
    # -------------------------------------------------
    segments = st.session_state.get("segments_list", [])
    if segments:
        seg_df_preview = pd.DataFrame(segments).copy()
        seg_df_preview["start"] = pd.to_datetime(seg_df_preview["start"]).dt.date
        seg_df_preview["end"] = pd.to_datetime(seg_df_preview["end"]).dt.date
        seg_df_preview = seg_df_preview.sort_values("start").reset_index(drop=True)

        with st.expander("👀 Segments existants", expanded=True):
            for i, r in seg_df_preview.iterrows():
                extras = []
                sma_s = r.get("sma_short", np.nan)
                sma_l = r.get("sma_long", np.nan)
                if pd.notna(sma_s) and pd.notna(sma_l):
                    extras.append(f"SMA({int(sma_s)},{int(sma_l)})")

                bb_w = r.get("bb_window", np.nan)
                bb_s = r.get("bb_std", np.nan)
                if pd.notna(bb_w) and pd.notna(bb_s):
                    extras.append(f"BB(window={int(bb_w)}, std={float(bb_s)})")

                st.markdown(f"**{i+1}. {r['strategy']}** — {r['start']} → {r['end']}")
                if extras:
                    st.caption(" · ".join(extras))
    else:
        st.info("Aucun segment pour l’instant.")

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

    with st.expander("📘 Détails métriques", expanded=False):
        df_stats = pd.DataFrame({
            "Stratégie (segments)": metrics_strat,
            "Buy & Hold": metrics_bh,
        })
        st.dataframe(df_stats, use_container_width=True)
