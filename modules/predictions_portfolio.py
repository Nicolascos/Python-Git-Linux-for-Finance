# modules/predictions_portfolio.py
import numpy as np
import pandas as pd
from scipy.stats import norm

def make_features_portfolio(
    df_in: pd.DataFrame,
    horizon: int = 1,
    n_lags: int = 5,
    price_col: str = "Close",
):
    """
    Fabrique features/targets pour un PORTFOLIO (Close = valeur portefeuille).

    df_in attendu: colonnes au minimum ["Date", price_col]
    Retour:
        X (DataFrame),
        y (Series log-return horizon),
        dates_t (Series datetime),
        close_t (Series),
        close_th (Series)
    """
    if "Date" not in df_in.columns or price_col not in df_in.columns:
        raise ValueError(f"df_in doit contenir 'Date' et '{price_col}'")

    df = df_in.copy().sort_values("Date").reset_index(drop=True)

    # sécurité: conversion num
    df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"])

    # log-return 1j
    df["ret"] = np.log(df[price_col]).diff()

    # lags
    for i in range(1, n_lags + 1):
        df[f"ret_lag_{i}"] = df["ret"].shift(i)

    # volatilités roulantes
    df["vol_10"] = df["ret"].rolling(10).std()
    df["vol_20"] = df["ret"].rolling(20).std()

    # target log-return horizon
    df["y"] = np.log(df[price_col].shift(-horizon) / df[price_col])

    # pour affichage (réel vs préd)
    df["close_t"] = df[price_col]
    df["close_th"] = df[price_col].shift(-horizon)

    df = df.dropna().reset_index(drop=True)

    feature_cols = [f"ret_lag_{i}" for i in range(1, n_lags + 1)] + ["vol_10", "vol_20"]
    X = df[feature_cols]
    y = df["y"]
    dates_t = df["Date"]
    close_t = df["close_t"]
    close_th = df["close_th"]

    return X, y, dates_t, close_t, close_th

def train_test_split_time_portfolio(X, y, dates, test_size=0.2):
    split_idx = int(len(X) * (1 - test_size))
    return (X.iloc[:split_idx], X.iloc[split_idx:],
            y.iloc[:split_idx], y.iloc[split_idx:],
            dates.iloc[:split_idx], dates.iloc[split_idx:])

def rf_predict_with_ci_portfolio(rf_model, X, alpha=0.05):
    """
    IC via distribution des arbres (identique à single).
    """
    all_tree_preds = np.vstack([est.predict(X) for est in rf_model.estimators_])
    mean_pred = all_tree_preds.mean(axis=0)
    lower = np.quantile(all_tree_preds, alpha/2, axis=0)
    upper = np.quantile(all_tree_preds, 1 - alpha/2, axis=0)
    return mean_pred, lower, upper

def linear_predict_with_ci_portfolio(lin_model, X_train, y_train, X_pred, alpha=0.05):
    """
    Renvoie 3 sorties: y_hat, lower, upper (stable).
    """
    y_hat_train = lin_model.predict(X_train)
    resid = (y_train.values - y_hat_train)
    sigma = resid.std(ddof=1)
    z = norm.ppf(1 - alpha/2)

    y_hat = lin_model.predict(X_pred)
    lower = y_hat - z * sigma
    upper = y_hat + z * sigma
    return y_hat, lower, upper

def returns_to_portfolio_path(last_value, pred_returns):
    """
    Convertit log-returns en trajectoire de VALEUR portefeuille.
    """
    values = [float(last_value)]
    for r in pred_returns:
        values.append(values[-1] * float(np.exp(r)))
    return np.array(values[1:])

def rollout_one_step_portfolio(X_mat: np.ndarray, r_next: np.ndarray, cols) -> np.ndarray:
    """
    Identique à single: shift des lags ret_lag_k.
    """
    cols = list(cols)
    lag_cols = sorted([c for c in cols if c.startswith("ret_lag_")],
                      key=lambda s: int(s.split("_")[-1]))
    lag_idx = [cols.index(c) for c in lag_cols]

    X_new = X_mat.copy()
    if len(lag_idx) >= 2:
        X_new[:, lag_idx[1:]] = X_mat[:, lag_idx[:-1]]
    X_new[:, lag_idx[0]] = r_next
    return X_new

def rf_rollout_paths_fast_portfolio(rf_model, X_last: pd.Series, steps: int, n_paths: int = 80) -> np.ndarray:
    """
    Simule n_paths trajectoires de log-returns futurs sur le portefeuille.
    """
    cols = list(X_last.index)
    n_trees = len(rf_model.estimators_)
    paths = np.zeros((n_paths, steps), dtype=float)

    x_curr = np.tile(X_last.values.astype(float), (n_paths, 1))

    for t in range(steps):
        x_np = np.asarray(x_curr, dtype=float)
        tree_preds = np.vstack([est.predict(x_np) for est in rf_model.estimators_])

        idx = np.random.randint(0, n_trees, size=n_paths)
        r = tree_preds[idx, np.arange(n_paths)]
        paths[:, t] = r

        x_curr = rollout_one_step_portfolio(x_curr, r, cols)

    return paths
