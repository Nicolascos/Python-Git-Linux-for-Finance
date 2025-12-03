# modules/data_loader.py

import pandas as pd
import yfinance as yf

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
    """
    Récupère les prix historiques OHLC via yfinance.
    Retourne un DataFrame propre compatible avec ton projet.
    """

    try:
        df = yf.download(symbol, period=f"{lookback_days}d", interval="1d")

        if df is None or df.empty:
            return None

        df = df.reset_index()

        return df

    except Exception as e:
        print("ERROR get_history:", e)
        return None
