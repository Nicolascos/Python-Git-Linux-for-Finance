# modules/plots.py

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


# ---------------------------------------------------------
# PLOT 1 — Courbe equity (stratégie vs buy&hold)
# ---------------------------------------------------------

def plot_equity_gated(
    df_strat_gated: pd.DataFrame,
    start_ts_eff,
    end_ts_eff,
    title: str = "Comparaison des stratégies",
) -> go.Figure:
    # Copie + normalisation Date
    g = df_strat_gated.copy()
    g["Date"] = pd.to_datetime(g["Date"])

    # Masques : période active / après sortie
    m_active = (g["Date"] >= start_ts_eff) & (g["Date"] <= end_ts_eff)
    m_after = g["Date"] > end_ts_eff

    # Séries segmentées pour afficher des "trous" hors période
    g["Strat_Window"] = np.where(m_active, g["Strategy"], np.nan)
    g["Port_After"] = np.where(m_after, g["Strategy"], np.nan)

    fig = go.Figure()

    # Courbes : BH, stratégie pendant la fenêtre, puis portefeuille après sortie
    fig.add_trace(go.Scatter(x=g["Date"], y=g["BH"], mode="lines", name="Buy & Hold"))
    fig.add_trace(go.Scatter(x=g["Date"], y=g["Strat_Window"], mode="lines", name="Stratégie (active)"))
    fig.add_trace(go.Scatter(
        x=g["Date"], y=g["Port_After"], mode="lines",
        name="Après sortie : Buy&Hold (portefeuille)"
    ))

    # Valeurs aux dates d'entrée/sortie (pour positionner les marqueurs)
    y_start = float(g.loc[g["Date"] == start_ts_eff, "Strategy"].iloc[0])
    y_end = float(g.loc[g["Date"] == end_ts_eff, "Strategy"].iloc[0])

    # Marqueur entrée
    fig.add_trace(go.Scatter(
        x=[start_ts_eff], y=[y_start], mode="markers",
        marker=dict(size=7, color="#00E676", symbol="circle", line=dict(color="black", width=1)),
        name="Entrée", showlegend=True,
        hovertemplate="<b>Entrée</b><br>Date: %{x|%Y-%m-%d}<br>Valeur: %{y:.3f}<extra></extra>",
    ))

    # Marqueur sortie
    fig.add_trace(go.Scatter(
        x=[end_ts_eff], y=[y_end], mode="markers",
        marker=dict(size=7, color="#FF5252", symbol="circle", line=dict(color="black", width=1)),
        name="Sortie", showlegend=True,
        hovertemplate="<b>Sortie</b><br>Date: %{x|%Y-%m-%d}<br>Valeur: %{y:.3f}<extra></extra>",
    ))

    # Ligne verticale sur la date de sortie
    fig.add_vline(
        x=end_ts_eff,
        line_width=2,
        line_dash="dash",
        line_color="rgba(255,255,255,0.65)",
    )

    # Mise en forme
    fig.update_layout(
        template="plotly_dark",
        height=500,
        title=title,
        xaxis_title="Date",
        yaxis_title="Évolution portefeuille (base 1)",
    )
    return fig


def plot_equity_segments(
    df_curve: pd.DataFrame,
    segments_df: pd.DataFrame,
    title: str = "Comparaison des stratégies",
) -> go.Figure:
    """
    df_curve doit contenir: Date, BH, Strategy
    segments_df contient start/end (dates) pour afficher les périodes actives.
    """
    # Copie + normalisation Date
    g = df_curve.copy()
    g["Date"] = pd.to_datetime(g["Date"])

    # Masque "actif" = union de tous les segments (start/end)
    m_active = np.zeros(len(g), dtype=bool)

    if segments_df is not None and not segments_df.empty:
        seg = segments_df.copy()
        seg["start"] = pd.to_datetime(seg["start"])
        seg["end"] = pd.to_datetime(seg["end"])

        for _, r in seg.iterrows():
            m_active |= (g["Date"] >= r["start"]) & (g["Date"] <= r["end"])

    # Séries segmentées : stratégie pendant segments, BH hors segments
    g["Strat_Active"] = np.where(m_active, g["Strategy"], np.nan)
    g["Port_BH"]      = np.where(~m_active, g["Strategy"], np.nan)  # BH hors segments (déjà rescalé)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["Date"], y=g["BH"], mode="lines", name="Buy & Hold"))
    fig.add_trace(go.Scatter(x=g["Date"], y=g["Strat_Active"], mode="lines", name="Stratégie (active)"))
    fig.add_trace(go.Scatter(
        x=g["Date"], y=g["Port_BH"], mode="lines",
        name="Hors segments : Buy&Hold (portefeuille)"
    ))

    # Marqueurs entrée/sortie pour chaque segment
    if segments_df is not None and not segments_df.empty:
        for _, r in seg.iterrows():
            # "Snap" sur la date la plus proche existante dans g
            start = g.loc[g["Date"] >= r["start"], "Date"].iloc[0] if (g["Date"] >= r["start"]).any() else None
            end   = g.loc[g["Date"] <= r["end"],   "Date"].iloc[-1] if (g["Date"] <= r["end"]).any() else None

            if start is not None:
                y_start = float(g.loc[g["Date"] == start, "Strategy"].iloc[0])
                fig.add_trace(go.Scatter(
                    x=[start], y=[y_start], mode="markers",
                    marker=dict(size=7, color="#00E676", symbol="circle", line=dict(color="black", width=1)),
                    name="Entrée", showlegend=False,
                ))

            if end is not None:
                y_end = float(g.loc[g["Date"] == end, "Strategy"].iloc[0])
                fig.add_trace(go.Scatter(
                    x=[end], y=[y_end], mode="markers",
                    marker=dict(size=7, color="#FF5252", symbol="circle", line=dict(color="black", width=1)),
                    name="Sortie", showlegend=False,
                ))

    # Mise en forme
    fig.update_layout(
        template="plotly_dark",
        height=500,
        title=title,
        xaxis_title="Date",
        yaxis_title="Évolution portefeuille (base 1)",
    )
    return fig
