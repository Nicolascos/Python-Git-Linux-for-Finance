# modules/strategy_single.py

import pandas as pd
import numpy as np


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
    df.loc[df["SMA_short"] > df["SMA_long"], "Signal"] = 1
    df.loc[df["SMA_short"] < df["SMA_long"], "Signal"] = -1

    # Position = signal d'aujourd’hui (sans look-ahead bias)
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
    """

    returns = df[column].pct_change().dropna()

    # annualisation (marchés US ~ 252 jours)
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
    vol = returns.std() * np.sqrt(252)

    # Max drawdown
    cum_max = df[column].cummax()
    drawdown = (df[column] - cum_max) / cum_max
    max_dd = drawdown.min()

    return {
        "Sharpe Ratio": round(sharpe, 3),
        "Volatility (ann.)": round(vol, 3),
        "Max Drawdown": round(max_dd, 3),
    }
