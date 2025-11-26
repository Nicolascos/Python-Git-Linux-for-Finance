# modules/plots.py

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


# ---------------------------------------------------------
# PLOT 1 — Graphique des prix + SMA + signaux
# ---------------------------------------------------------
def plot_price_with_indicators(df: pd.DataFrame, show_sma=True):
    """
    Graphique : prix, SMA, zones achat/vente.
    """

    fig = go.Figure()

    # Courbe des prix
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Close"],
        mode="lines",
        name="Prix",
        line=dict(color="white", width=2)
    ))

    # SMA short
    if show_sma and "SMA_short" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["SMA_short"],
            mode="lines",
            name="SMA Court",
            line=dict(color="orange", width=1.5)
        ))

    # SMA long
    if show_sma and "SMA_long" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["SMA_long"],
            mode="lines",
            name="SMA Long",
            line=dict(color="blue", width=1.5)
        ))

    fig.update_layout(
        template="plotly_dark",
        height=500,
        title="Prix & Indicateurs",
        xaxis_title="Date",
        yaxis_title="Prix"
    )

    return fig


# ---------------------------------------------------------
# PLOT 2 — Courbe equity (stratégie vs buy&hold)
# ---------------------------------------------------------
def plot_equity(df_bh: pd.DataFrame, df_strat: pd.DataFrame):
    """
    Graphique Equity curve des deux stratégies
    """

    fig = go.Figure()

    # Buy & Hold
    fig.add_trace(go.Scatter(
        x=df_bh["Date"],
        y=df_bh["Strategy"],
        mode="lines",
        name="Buy & Hold",
        line=dict(color="green", width=2)
    ))

    # SMA ou autre stratégie
    fig.add_trace(go.Scatter(
        x=df_strat["Date"],
        y=df_strat["Strategy"],
        mode="lines",
        name="Stratégie",
        line=dict(color="cyan", width=2)
    ))

    fig.update_layout(
        template="plotly_dark",
        height=500,
        title="Comparaison des stratégies",
        xaxis_title="Date",
        yaxis_title="Évolution portefeuille (base 1)"
    )

    return fig
