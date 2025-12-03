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

    df["MA"] = df["Close"].rolling(window).mean()
    df["STD"] = df["Close"].rolling(window).std()

    df["Upper"] = df["MA"] + num_std * df["STD"]
    df["Lower"] = df["MA"] - num_std * df["STD"]

    df["Signal"] = 0
    # Correction (Cause de l'erreur) : Utiliser .values pour garantir l'alignement
    df.loc[df["Close"].values < df["Lower"].values, "Signal"] = 1   # Achat
    df.loc[df["Close"].values > df["Upper"].values, "Signal"] = -1  # Vente

    df["Position"] = df["Signal"].shift(1).fillna(0)

    df["Returns"] = df["Close"].pct_change().fillna(0)
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


# -------------------------------------------------------------
# CLASSE SINGLE ASSET ANALYZER
# -------------------------------------------------------------
class SingleAssetAnalyzer:
    def __init__(self, ticker, start_date, end_date, initial_investment=1000):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.initial_investment = initial_investment
        self.data = pd.DataFrame()
        self.daily_returns = pd.Series(dtype=float)
        self.best_params = {}

    def load_data(self):
        """Télécharge les données."""
        try:
            df = yf.download(self.ticker, start=self.start_date, end=self.end_date, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs('Close', axis=1, level=0, drop_level=False)
                df.columns = ['Close']
            else:
                df = df[['Close']]

            if df.empty:
                return False

            self.data = df
            self.daily_returns = self.data['Close'].pct_change().fillna(0)
            return True
        except Exception:
            # On ne met pas st.error ici, on le gère dans app.py
            return False

    def compute_metrics(self, strategy_returns):
        """Calcule Sharpe, Max Drawdown et Performance Totale."""
        strategy_returns = strategy_returns.dropna()
        if strategy_returns.empty:
            return {'Sharpe': 0.0, 'Max Drawdown': 0.0, 'Total Perf': 0.0}

        rf = 0.03
        mean_ret = strategy_returns.mean()
        std_ret = strategy_returns.std()

        if std_ret == 0:
            sharpe = 0
        else:
            sharpe = (mean_ret - (rf/252)) / std_ret * np.sqrt(252)

        cum_ret = (1 + strategy_returns).cumprod()
        peak = cum_ret.expanding(min_periods=1).max()
        dd = (cum_ret - peak) / peak
        max_dd = abs(dd.min())
        total_perf = cum_ret.iloc[-1] - 1

        return {
            'Sharpe': round(sharpe, 2),
            'Max Drawdown': f"{max_dd:.2%}",
            'Total Perf': f"{total_perf:.2%}",
            'Raw_Sharpe': sharpe
        }

    def run_strategy(self, strat_name, **params):
        """Exécute une stratégie spécifique avec des paramètres donnés."""
        signals = pd.Series(0, index=self.data.index)

        # --- LOGIQUE DES STRATÉGIES ---
        if strat_name == "Momentum":
            window = int(params.get('window', 50))
            mms = self.data['Close'].rolling(window=window).mean()
            signals = np.where(self.data['Close'] > mms, 1.0, 0.0)

        elif strat_name == "Cross MMS":
            short_w = int(params.get('short_w', 20))
            long_w = int(params.get('long_w', 50))
            mms_short = self.data['Close'].rolling(window=short_w).mean()
            mms_long = self.data['Close'].rolling(window=long_w).mean()
            signals = np.where(mms_short > mms_long, 1.0, 0.0)

        elif strat_name == "Mean Reversion (BB)":
            window = int(params.get('window', 20))
            std_dev = float(params.get('std_dev', 2.0))
            sma = self.data['Close'].rolling(window=window).mean()
            std = self.data['Close'].rolling(window=window).std()
            lower_band = sma - (std * std_dev)
            signals = np.where(self.data['Close'] < lower_band, 1.0, 0.0)

        # Backtest
        signals = pd.Series(signals, index=self.data.index)
        strat_returns = self.daily_returns.shift(-1) * signals.shift(1).fillna(0)
        strat_curve = (1 + strat_returns).cumprod() * self.initial_investment
        strat_curve = strat_curve.ffill()

        return strat_curve, strat_returns

    def find_best_params(self):
        """Teste plein de combinaisons et stocke les gagnantes."""

        # 1. Optimisation Momentum
        best_sharpe = -999
        best_p = {'window': 50}
        for w in range(10, 100, 10):
            _, rets = self.run_strategy("Momentum", window=w)
            m = self.compute_metrics(rets)
            if m['Raw_Sharpe'] > best_sharpe:
                best_sharpe = m['Raw_Sharpe']
                best_p = {'window': w}
        self.best_params['Momentum'] = best_p

        # 2. Optimisation Cross MMS
        best_sharpe = -999
        best_p = {'short_w': 20, 'long_w': 50}
        for s, l in itertools.product(range(10, 50, 10), range(50, 150, 20)):
            if s >= l:
                continue
            _, rets = self.run_strategy("Cross MMS", short_w=s, long_w=l)
            m = self.compute_metrics(rets)
            if m['Raw_Sharpe'] > best_sharpe:
                best_sharpe = m['Raw_Sharpe']
                best_p = {'short_w': s, 'long_w': l}
        self.best_params['Cross MMS'] = best_p

        # 3. Optimisation BB
        best_sharpe = -999
        best_p = {'window': 20, 'std_dev': 2.0}
        for w, std in itertools.product(range(10, 50, 10), [1.5, 2.0, 2.5]):
            _, rets = self.run_strategy("Mean Reversion (BB)", window=w, std_dev=std)
            m = self.compute_metrics(rets)
            if m['Raw_Sharpe'] > best_sharpe:
                best_sharpe = m['Raw_Sharpe']
                best_p = {'window': w, 'std_dev': std}
        self.best_params['Mean Reversion (BB)'] = best_p

    def predict_future(self, days_ahead=30, model_type="Linear Regression"):
        """Génère des prédictions selon le modèle choisi."""
        df = self.data.copy()
        last_date = df.index[-1]
        future_dates = [last_date + timedelta(days=i) for i in range(1, days_ahead + 1)]

        # --- MODÈLE 1 : RÉGRESSION LINÉAIRE (CORRIGÉ) ---
        if model_type == "Linear Regression":
            df = df.reset_index()
            df['Date_Ordinal'] = df['Date'].map(pd.Timestamp.toordinal)
            X = df[['Date_Ordinal']].values
            y = df['Close'].values

            model = LinearRegression().fit(X, y)
            future_ordinals = [[d.toordinal()] for d in future_dates]
            preds = model.predict(future_ordinals)

            # Fix Ancrage
            last_day_ordinal = [[X[-1][0]]]
            theoretical_price_today = model.predict(last_day_ordinal)[0]
            actual_price_today = y[-1]
            offset = actual_price_today - theoretical_price_today
            preds = preds + offset

            # Fix Volatilité Locale
            recent_returns = df['Close'].pct_change().tail(90)
            sigma_pct = recent_returns.std()
            std_dev = sigma_pct * df['Close'].iloc[-1]

            return future_dates, preds, std_dev

        # --- MODÈLE 2 : ARIMA ---
        elif model_type == "ARIMA":
            history = df['Close'].values
            model = ARIMA(history, order=(5, 1, 0))
            model_fit = model.fit()
            preds = model_fit.forecast(steps=days_ahead)

            residuals = model_fit.resid
            std_dev = np.std(residuals[1:])
            return future_dates, preds, std_dev

        # --- MODÈLE 3 : RANDOM FOREST ---
        elif model_type == "Machine Learning (RF)":
            df['Lag1'] = df['Close'].shift(1)
            df['Lag2'] = df['Close'].shift(2)
            df['MA5'] = df['Close'].rolling(5).mean()
            df = df.dropna()

            X = df[['Lag1', 'Lag2', 'MA5']].values
            y = df['Close'].values

            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)

            preds = []
            current_lag1 = df['Close'].iloc[-1]
            current_lag2 = df['Close'].iloc[-2]
            # Keep track of recent values for rolling MA calculation
            recent_values = list(df['Close'].tail(5).values)

            for _ in range(days_ahead):
                current_ma = np.mean(recent_values[-5:])
                pred = model.predict([[current_lag1, current_lag2, current_ma]])[0]
                preds.append(pred)
                current_lag2 = current_lag1
                current_lag1 = pred
                recent_values.append(pred)

            train_preds = model.predict(X)
            std_dev = np.std(y - train_preds)

            return future_dates, np.array(preds), std_dev

        return [], [], 0