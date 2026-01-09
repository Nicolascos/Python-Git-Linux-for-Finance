from datetime import date
from typing import Dict, Optional, Tuple

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error

import streamlit as st

from modules.data_loader import load_historical_data
from modules.preprocessing import prepare_ohlc_df, slice_by_date_window
from modules.strategy_single import (
    strategy_sma,
    strategy_bollinger,
    compute_metrics,
)


@st.cache_data(show_spinner=False, ttl=60 * 30)
def best_params_by_sortino(
    symbol: str,
    start_d: date,
    end_d: date,
    lookback: int,
    strategy_choice: str,
) -> Tuple[Optional[Dict[str, float]], Optional[float]]:
    """
    Retourne (best_params, best_sortino) pour SMA Momentum ou Bollinger.
    Optimise sur Sortino.
    """
    # Chargement de l'historique (lookback = profondeur max dispo)
    df = load_historical_data(symbol, lookback_days=lookback)
    if df is None or df.empty:
        return None, None

    # Normalisation du format OHLC (colonnes/types/index cohérents)
    df = prepare_ohlc_df(df)

    # Fenêtrage sur la période demandée (avec garde-fou sur le nb de points)
    try:
        df_slice = slice_by_date_window(df, start_d, end_d, min_points=30)
    except Exception:
        return None, None

    # Meilleur couple (paramètres, score) trouvé sur la grille
    best_params = None
    best_score = None

    # ---------------------------------------------------------
    # STRAT 1 — SMA Momentum : grid search (short, long)
    # ---------------------------------------------------------
    if strategy_choice == "SMA Momentum":
        short_grid = [5, 10, 15, 20, 30]
        long_grid = [30, 50, 75, 100, 150, 200]

        for s in short_grid:
            for l in long_grid:
                # Contrainte: short < long (sinon signal non pertinent)
                if s >= l:
                    continue
                try:
                    # Application stratégie puis scoring via métriques
                    df_s = strategy_sma(df_slice, short=s, long=l)
                    m = compute_metrics(df_s)
                    score = m.get("Sortino", None)
                    if score is None:
                        continue

                    # Mise à jour du meilleur score (maximisation Sortino)
                    if (best_score is None) or (score > best_score):
                        best_score = score
                        best_params = {"short": float(s), "long": float(l)}
                except Exception:
                    # On ignore les combos qui cassent (données insuffisantes, NaN, etc.)
                    continue

    # ---------------------------------------------------------
    # STRAT 2 — Bollinger : grid search (window, num_std)
    # ---------------------------------------------------------
    elif strategy_choice == "Bollinger":
        window_grid = [10, 14, 20, 30, 40, 60]
        std_grid = [1.5, 2.0, 2.5, 3.0]

        for w in window_grid:
            for s in std_grid:
                try:
                    # Application stratégie puis scoring via métriques
                    df_s = strategy_bollinger(df_slice, window=w, num_std=s)
                    m = compute_metrics(df_s)
                    score = m.get("Sortino", None)
                    if score is None:
                        continue

                    # Mise à jour du meilleur score (maximisation Sortino)
                    if (best_score is None) or (score > best_score):
                        best_score = score
                        best_params = {"bb_window": float(w), "bb_std": float(s)}
                except Exception:
                    # On ignore les combos qui cassent (données insuffisantes, NaN, etc.)
                    continue

    # Si aucune combinaison n'a pu être scorée, on renvoie (None, None)
    return best_params, best_score
