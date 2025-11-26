# modules/data_loader.py

import time
import requests
import pandas as pd

# --------------------------------------------
# 1. Récupération du prix en direct
# --------------------------------------------
def get_live_price(symbol: str, api_key: str):
    """
    Récupère le prix actuel via Finnhub.
    Retourne float ou None.
    """
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        return data.get("c")   # price ("current")
    except Exception as e:
        print("ERROR FINNHUB:", e)
        raise e


# --------------------------------------------
# 2. Récupération historique OHLC
# --------------------------------------------
def get_history(symbol, api_key, resolution="D", lookback_days=365):

    try:
        now = int(time.time())
        past = now - lookback_days * 24 * 3600

        # 🔥 1) Détection automatique du type d’actif
        if ":" in symbol:
            endpoint = "crypto"
            url = (
                f"https://finnhub.io/api/v1/crypto/candle?"
                f"symbol={symbol}&resolution={resolution}&from={past}&to={now}&token={api_key}"
            )
        else:
            endpoint = "stock"
            url = (
                f"https://finnhub.io/api/v1/stock/candle?"
                f"symbol={symbol}&resolution={resolution}&from={past}&to={now}&token={api_key}"
            )

        print("DEBUG URL =", url)

        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()

        print("DEBUG JSON =", data)

        if data.get("s") != "ok":
            return None

        df = pd.DataFrame({
            "Date": pd.to_datetime(data["t"], unit="s"),
            "Open": data["o"],
            "High": data["h"],
            "Low": data["l"],
            "Close": data["c"],
            "Volume": data["v"],
        })

        return df

    except Exception as e:
        print("ERROR FINNHUB get_history:", e)
        raise
    """
    Récupère les prix historiques (OHLC) sur 1 an par défaut.
    Retourne un DataFrame propre.
    """

    try:
        now = int(time.time())
        past = now - lookback_days * 24 * 3600

        url = (
            f"https://finnhub.io/api/v1/stock/candle?"
            f"symbol={symbol}&resolution={resolution}&from={past}&to={now}&token={api_key}"
        )

        print("url = ", url)   # <—— AJOUT

        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()

        return data
    
        print("DEBUG FINNHUB RAW RESPONSE:", data)   # <—— AJOUT
        

        if data.get("s") != "ok":
            return None

        df = pd.DataFrame({
            "Date": pd.to_datetime(data["t"], unit="s"),
            "Open": data["o"],
            "High": data["h"],
            "Low": data["l"],
            "Close": data["c"],
            "Volume": data["v"],
        })

        return df

    except Exception as e:
        print("ERROR FINNHUB:", e)
        raise e
