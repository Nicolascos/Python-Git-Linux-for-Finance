# modules/data_loader.py

import pandas as pd
import yfinance as yf
import streamlit as st

# ---------------------------------------------------------
# 1. Récupération du prix "live" (en réalité dernier prix connu)
# ---------------------------------------------------------
def get_live_price(symbol: str):
    """
    Récupère le dernier prix 'live' via yfinance.
    Retourne float ou None.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")

        if data.empty:
            return None

        return float(data["Close"].iloc[-1])

    except Exception as e:
        print("ERROR get_live_price:", e)
        return None


# ---------------------------------------------------------
# 2. Récupération historique OHLC
# ---------------------------------------------------------
def get_history(symbol: str, lookback_days=365):
    try:
        df = yf.download(symbol, period=f"{lookback_days}d", interval="1d")

        if df is None or df.empty:
            return None

        df = df.reset_index()

        # --- FIX MultiIndex colonnes (Close/AAPL etc.) ---
        if isinstance(df.columns, pd.MultiIndex):
            # On garde le 1er niveau (Date, Open, High...) et on drop le ticker
            df.columns = [c[0] for c in df.columns]

        # normalisation du nom de date
        if "Datetime" in df.columns and "Date" not in df.columns:
            df = df.rename(columns={"Datetime": "Date"})
        if "index" in df.columns and "Date" not in df.columns:
            df = df.rename(columns={"index": "Date"})

        return df

    except Exception as e:
        print("ERROR get_history:", e)
        return None

# ---------------------------------------------------------
# CACHING — données historiques
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def load_historical_data(symbol: str, lookback_days: int) -> pd.DataFrame:
    from modules.data_loader import get_history
    return get_history(symbol, lookback_days=lookback_days)