# modules/portfolio.py
import pandas as pd
import numpy as np

def load_multi_prices(load_historical_data_fn, prepare_ohlc_df_fn, symbols, lookback_days: int) -> pd.DataFrame:
    """
    Charge les prix pour plusieurs tickers.
    Retour format LONG: colonnes ["Date","Close","symbol"].
    """
    rows = []
    for s in symbols:
        d = load_historical_data_fn(s, lookback_days=lookback_days)
        if d is None or d.empty:
            continue
        d = prepare_ohlc_df_fn(d)
        tmp = d[["Date", "Close"]].copy()
        tmp["symbol"] = s
        rows.append(tmp)

    if not rows:
        return pd.DataFrame(columns=["Date", "Close", "symbol"])

    out = pd.concat(rows, ignore_index=True)
    out["Date"] = pd.to_datetime(out["Date"])
    return out


def build_portfolio_close(df_prices_long: pd.DataFrame, alloc_df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit un pseudo-actif "portfolio" avec une colonne Close = valeur portefeuille.

    df_prices_long: colonnes ["Date","Close","symbol"]
    alloc_df: colonnes ["symbol","amount_eur"] (montants > 0, tickers uniques)

    Retour: DataFrame ["Date","Close"] (Close = valeur portefeuille)
    """
    required = {"Date", "Close", "symbol"}
    if not required.issubset(df_prices_long.columns):
        raise ValueError("df_prices_long doit contenir Date/Close/symbol (format long).")

    alloc = alloc_df.copy()
    alloc = alloc.dropna(subset=["symbol", "amount_eur"])
    alloc = alloc[alloc["amount_eur"] > 0]
    if alloc.empty:
        raise ValueError("alloc_df vide ou montants <= 0.")
    if alloc["symbol"].duplicated().any():
        raise ValueError("alloc_df contient des tickers en double.")

    # pivot => Date index, colonnes tickers
    wide = df_prices_long.pivot(index="Date", columns="symbol", values="Close").sort_index()

    # on garde seulement les tickers présents dans les prix
    alloc = alloc.set_index("symbol")["amount_eur"]
    common = [s for s in alloc.index if s in wide.columns]
    if not common:
        raise ValueError("Aucun ticker d'alloc n'a de prix chargé.")
    wide = wide[common]
    alloc = alloc.loc[common]

    # MVP: intersection des dates (ffill puis dropna)
    wide = wide.ffill().dropna(how="any")

    # normalisation à t0
    base = wide.iloc[0]
    norm = wide / base

    portfolio_value = (norm * alloc).sum(axis=1)

    out = portfolio_value.reset_index()
    out.columns = ["Date", "Close"]
    out["Date"] = pd.to_datetime(out["Date"])
    return out



def apply_segments_to_portfolio(
    df_pf_slice: pd.DataFrame,
    segments_df: pd.DataFrame,
    strategy_map: dict,
) -> pd.DataFrame:
    """
    Retourne un df avec colonne Strategy (equity base 1) qui:
    - suit Buy&Hold hors segments
    - suit la stratégie sur les segments
    - REBASCULE en Buy&Hold entre segments en conservant la valeur atteinte (gating)
    """

    out = df_pf_slice.copy().sort_values("Date").reset_index(drop=True)
    out["Date"] = pd.to_datetime(out["Date"])
    out["Close"] = pd.to_numeric(out["Close"], errors="coerce")
    out = out.dropna(subset=["Close"]).reset_index(drop=True)

    # --- Buy&Hold equity de référence (base 1)
    bh_ret = out["Close"].pct_change().fillna(0.0)
    out["BH"] = (1.0 + bh_ret).cumprod()

    # si pas de segments => Strategy = BH
    if segments_df is None or segments_df.empty:
        out["Strategy"] = out["BH"].values
        return out

    segs = segments_df.copy()
    segs["start"] = pd.to_datetime(segs["start"])
    segs["end"]   = pd.to_datetime(segs["end"])
    segs = segs.sort_values("start").reset_index(drop=True)

    # --- On construit une série de multiplicateurs journaliers "gross_ret"
    # Par défaut : Buy&Hold
    gross_ret = (1.0 + bh_ret).values  # numpy array

    # IMPORTANT: pour éviter double-compte au début d’un segment, on mettra le jour start à 1.0
    # et on applique les retours stratégie à partir du jour suivant.

    for _, seg in segs.iterrows():
        s = seg["start"]
        e = seg["end"]
        strat_name = seg["strategy"]

        # masque segment: [start, end) (end exclu pour éviter chevauchement)
        m = (out["Date"] >= s) & (out["Date"] < e)
        idx = np.where(m.values)[0]
        if len(idx) < 3:
            continue

        # slice pour stratégie
        seg_df = out.loc[m, ["Date", "Close"]].copy().reset_index(drop=True)

        # paramètres optionnels
        params = {}
        if strat_name == "SMA Momentum":
            if "sma_short" in seg and "sma_long" in seg:
                params = {"short": int(seg["sma_short"]), "long": int(seg["sma_long"])}
        if strat_name == "Bollinger":
            if "bb_window" in seg and "bb_std" in seg:
                params = {"window": int(seg["bb_window"]), "num_std": float(seg["bb_std"])}

        # calc stratégie (doit retourner df avec colonne Strategy base 1)
        strat_fn = strategy_map[strat_name]
        seg_strat = strat_fn(seg_df, **params) if params else strat_fn(seg_df)

        # retours journaliers de la stratégie
        seg_gross = (1.0 + seg_strat["Strategy"].pct_change().fillna(0.0)).values

        # ---- GATING: on remplace les gross_ret pendant le segment,
        # mais le 1er jour du segment = 1.0 (continuité)
        seg_gross[0] = 1.0

        gross_ret[idx] = seg_gross

    # --- Equity finale (continue)
    out["Strategy"] = np.cumprod(gross_ret)

    return out
