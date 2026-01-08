
from datetime import date
from typing import Dict, Optional, Tuple

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
    df = load_historical_data(symbol, lookback_days=lookback)
    if df is None or df.empty:
        return None, None

    df = prepare_ohlc_df(df)

    try:
        df_slice = slice_by_date_window(df, start_d, end_d, min_points=30)
    except Exception:
        return None, None

    best_params = None
    best_score = None

    if strategy_choice == "SMA Momentum":
        short_grid = [5, 10, 15, 20, 30]
        long_grid = [30, 50, 75, 100, 150, 200]

        for s in short_grid:
            for l in long_grid:
                if s >= l:
                    continue
                try:
                    df_s = strategy_sma(df_slice, short=s, long=l)
                    m = compute_metrics(df_s)
                    score = m.get("Sortino", None)  # <-- Sortino
                    if score is None:
                        continue
                    if (best_score is None) or (score > best_score):
                        best_score = score
                        best_params = {"short": float(s), "long": float(l)}
                except Exception:
                    continue

    elif strategy_choice == "Bollinger":
        window_grid = [10, 14, 20, 30, 40, 60]
        std_grid = [1.5, 2.0, 2.5, 3.0]

        for w in window_grid:
            for s in std_grid:
                try:
                    df_s = strategy_bollinger(df_slice, window=w, num_std=s)
                    m = compute_metrics(df_s)
                    score = m.get("Sortino", None)  # <-- Sortino
                    if score is None:
                        continue
                    if (best_score is None) or (score > best_score):
                        best_score = score
                        best_params = {"bb_window": float(w), "bb_std": float(s)}
                except Exception:
                    continue

    return best_params, best_score
