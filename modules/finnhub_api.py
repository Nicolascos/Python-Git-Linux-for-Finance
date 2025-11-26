'''
import finnhub
import pandas as pd

# ---------------------------------------------------------
#   FINNHUB API MODULE
#   Ce fichier regroupe toutes les fonctions d'accès API.
# ---------------------------------------------------------

def init_client(api_key: str):
    """Initialise le client Finnhub."""
    try:
        return finnhub.Client(api_key=api_key)
    except Exception as e:
        print("Erreur lors de l'initialisation du client Finnhub :", e)
        return None


def get_live_price(symbol: str, api_key: str):
    """Retourne le prix actuel d'un ticker."""
    client = init_client(api_key)
    if client is None:
        return None

    try:
        quote = client.quote(symbol)
        return quote.get("c")  # prix actuel
    except Exception as e:
        print(f"Erreur API Finnhub pour {symbol} :", e)
        return None


def get_history(symbol: str, api_key: str, resolution="D", count=100):
    """Récupère l'historique des prix (OHLC)."""
    client = init_client(api_key)
    if client is None:
        return None

    try:
        data = client.stock_candles(symbol, resolution, count=count)

        if data.get("s") != "ok":
            print(f"Erreur dans les données Finnhub pour {symbol} :", data)
            return None

        df = pd.DataFrame(data)
        df["t"] = pd.to_datetime(df["t"], unit="s")
        df.rename(columns={"t": "Date", "o": "Open", "h": "High",
                           "l": "Low", "c": "Close"}, inplace=True)

        return df[["Date", "Open", "High", "Low", "Close"]]

    except Exception as e:
        print(f"Erreur API pour l'historique de {symbol} :", e)
        return None

'''