# modules/plots.py

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ---------------------------------------------------------
# PLOT 1 — Courbe equity (stratégie vs buy&hold)
# ---------------------------------------------------------

def plot_equity_gated(
    df_strat_gated: pd.DataFrame,
    start_ts_eff,
    end_ts_eff,
    title: str = "Comparaison des stratégies",
) -> go.Figure:
    g = df_strat_gated.copy()
    g["Date"] = pd.to_datetime(g["Date"])

    m_active = (g["Date"] >= start_ts_eff) & (g["Date"] <= end_ts_eff)
    m_after = g["Date"] > end_ts_eff

    g["Strat_Window"] = np.where(m_active, g["Strategy"], np.nan)
    g["Port_After"] = np.where(m_after, g["Strategy"], np.nan)

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=g["Date"], y=g["BH"], mode="lines", name="Buy & Hold"))
    fig.add_trace(go.Scatter(x=g["Date"], y=g["Strat_Window"], mode="lines", name="Stratégie (active)"))
    fig.add_trace(go.Scatter(x=g["Date"], y=g["Port_After"], mode="lines",
                             name="Après sortie : Buy&Hold (portefeuille)"))

    y_start = float(g.loc[g["Date"] == start_ts_eff, "Strategy"].iloc[0])
    y_end = float(g.loc[g["Date"] == end_ts_eff, "Strategy"].iloc[0])

    fig.add_trace(go.Scatter(
        x=[start_ts_eff], y=[y_start], mode="markers",
        marker=dict(size=7, color="#00E676", symbol="circle", line=dict(color="black", width=1)),
        name="Entrée", showlegend=True,
        hovertemplate="<b>Entrée</b><br>Date: %{x|%Y-%m-%d}<br>Valeur: %{y:.3f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=[end_ts_eff], y=[y_end], mode="markers",
        marker=dict(size=7, color="#FF5252", symbol="circle", line=dict(color="black", width=1)),
        name="Sortie", showlegend=True,
        hovertemplate="<b>Sortie</b><br>Date: %{x|%Y-%m-%d}<br>Valeur: %{y:.3f}<extra></extra>",
    ))

    fig.add_vline(
        x=end_ts_eff,
        line_width=2,
        line_dash="dash",
        line_color="rgba(255,255,255,0.65)",
    )

    fig.update_layout(
        template="plotly_dark",
        height=500,
        title=title,
        xaxis_title="Date",
        yaxis_title="Évolution portefeuille (base 1)",
    )
    return fig