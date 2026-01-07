# modules/strategy_single.py

import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.arima.model import ARIMA
from datetime import timedelta
import itertools


# -------------------------------------------------------------
# STRATÉGIE 1 : BUY & HOLD
# -------------------------------------------------------------
def strategy_buy_and_hold(df: pd.DataFrame):
    """
    Stratégie Buy & Hold :
    Toujours investi du début à la fin.
    Retourne un DataFrame avec la position et le portefeuille.
    """

    df = df.copy()
    df["Position"] = 1   # toujours investi
    df["Returns"] = df["Close"].pct_change().fillna(0)
    df["Strategy"] = (1 + df["Returns"]).cumprod()
    return df


# -------------------------------------------------------------
# STRATÉGIE 2 : MOMENTUM SMA — Simple Moving Average
# -------------------------------------------------------------
def strategy_sma(df: pd.DataFrame, short=20, long=50):
    """
    Stratégie Momentum basée sur croisement de moyennes mobiles :
    - Achat lorsque SMA courte > SMA longue
    - Vente lorsque SMA courte < SMA longue

    Retourne un DataFrame avec signaux, positions, performance.
    """

    df = df.copy()

    df["SMA_short"] = df["Close"].rolling(short).mean()
    df["SMA_long"] = df["Close"].rolling(long).mean()

    df["Signal"] = 0
    # Correction : Utiliser .values pour garantir l'alignement
    df.loc[df["SMA_short"].values > df["SMA_long"].values, "Signal"] = 1
    df.loc[df["SMA_short"].values < df["SMA_long"].values, "Signal"] = -1

    # Position = signal d'aujourd’hui (sans look-ahead bias)
    df["Position"] = df["Signal"].shift(1).fillna(0)

    df["Returns"] = df["Close"].pct_change().fillna(0)
    df["Strategy"] = (1 + df["Returns"] * df["Position"]).cumprod()

    return df


# -------------------------------------------------------------
# STRATÉGIE 3 : RSI Momentum - Relative Strength Index
# -------------------------------------------------------------
def compute_rsi(df: pd.DataFrame, window=14):
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()

    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df


def strategy_rsi(df: pd.DataFrame, window=14):
    df = df.copy()
    df = compute_rsi(df, window)

    df["Signal"] = 0
    # Correction : Utiliser .values pour garantir l'alignement
    df.loc[df["RSI"].values < 30, "Signal"] = 1      # Achat
    df.loc[df["RSI"].values > 70, "Signal"] = -1     # Vente

    df["Position"] = df["Signal"].shift(1).fillna(0)
    df["Returns"] = df["Close"].pct_change().fillna(0)

    df["Strategy"] = (1 + df["Returns"] * df["Position"]).cumprod()

    return df


# -------------------------------------------------------------
# STRATÉGIE 4 :  MACD - Moving Average Convergence Divergence
# -------------------------------------------------------------
def strategy_macd(df: pd.DataFrame):
    df = df.copy()

    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()

    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    df["Position"] = 0
    # Correction : Utiliser .values pour garantir l'alignement
    df.loc[df["MACD"].values > df["Signal"].values, "Position"] = 1
    df.loc[df["MACD"].values < df["Signal"].values, "Position"] = -1

    # Le shift est appliqué à la Position, pas au Signal
    df["Position"] = df["Position"].shift(1).fillna(0)
    df["Returns"] = df["Close"].pct_change().fillna(0)

    df["Strategy"] = (1 + df["Returns"] * df["Position"]).cumprod()

    return df


# -------------------------------------------------------------
# STRATÉGIE 5 :  Bollinger Bands - Reversion to Mean
# -------------------------------------------------------------
def strategy_bollinger(df: pd.DataFrame, window=20, num_std=2):
    df = df.copy()

    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        # prends la première colonne, ou sélectionne ton ticker explicitement
        close = close.iloc[:, 0]

    df["MA"] = close.rolling(window).mean()
    df["STD"] = close.rolling(window).std()
    df["Upper"] = df["MA"] + num_std * df["STD"]
    df["Lower"] = df["MA"] - num_std * df["STD"]

    df["Signal"] = 0
    df.loc[close < df["Lower"], "Signal"] = 1
    df.loc[close > df["Upper"], "Signal"] = -1

    df["Position"] = df["Signal"].shift(1).fillna(0)
    df["Returns"] = close.pct_change().fillna(0)
    df["Strategy"] = (1 + df["Returns"] * df["Position"]).cumprod()

    return df




# -------------------------------------------------------------
# STRATÉGIE 6 :  Golden Cross / Death Cross
# -------------------------------------------------------------
def strategy_golden_cross(df: pd.DataFrame):
    df = df.copy()

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    df["Signal"] = 0
    # Correction : Utiliser .values pour garantir l'alignement
    df.loc[df["SMA50"].values > df["SMA200"].values, "Signal"] = 1
    df.loc[df["SMA50"].values < df["SMA200"].values, "Signal"] = -1

    df["Position"] = df["Signal"].shift(1).fillna(0)
    df["Returns"] = df["Close"].pct_change().fillna(0)

    df["Strategy"] = (1 + df["Returns"] * df["Position"]).cumprod()

    return df


# -------------------------------------------------------------
# MÉTRIQUES QUANTITATIVES
# -------------------------------------------------------------
def compute_metrics(df: pd.DataFrame, column="Strategy"):
    """
    Calcule les métriques de performance :
    - Sharpe Ratio (252 jours)
    - Max Drawdown
    - Volatilité annualisée
    - Sortino Ratio
    """

    # Rendements journaliers de la stratégie
    returns = df[column].pct_change().dropna()

    if returns.empty:
        return {
            "Sharpe Ratio": 0.0,
            "Volatility (ann.)": 0.0,
            "Max Drawdown": 0.0,
            "Sortino": 0.0,
        }

    # Volatilité / Sharpe
    std = returns.std()
    if std > 0:
        sharpe = (returns.mean() / std) * np.sqrt(252)
    else:
        sharpe = 0.0
    vol = std * np.sqrt(252)

    # Sortino : uniquement la volatilité des rendements négatifs
    downside = returns[returns < 0]
    downside_std = downside.std()
    if downside_std > 0:
        sortino = (returns.mean() / downside_std) * np.sqrt(252)
    else:
        sortino = 0.0

    # Max drawdown
    cum_max = df[column].cummax()
    drawdown = (df[column] - cum_max) / cum_max
    max_dd = drawdown.min()

    return {
        "Sharpe Ratio": round(sharpe, 3),
        "Volatility (ann.)": round(vol, 3),
        "Max Drawdown": round(max_dd, 3),
        "Sortino": round(sortino, 3),
    }