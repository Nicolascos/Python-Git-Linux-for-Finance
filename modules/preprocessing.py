import pandas as pd
import numpy as np



def prepare_ohlc_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Date" not in out.columns and "Datetime" in out.columns:
        out = out.rename(columns={"Datetime": "Date"})
    if "Date" not in out.columns:
        raise KeyError("Colonne 'Date' introuvable.")

    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out = out.dropna(subset=["Date"])
    out = out.sort_values("Date").drop_duplicates("Date").reset_index(drop=True)
    return out


def slice_by_date_window(df: pd.DataFrame, start_d, end_d, min_points: int = 30) -> pd.DataFrame:
    start_d = pd.Timestamp(start_d).date()
    end_d = pd.Timestamp(end_d).date()

    mask = (df["Date"].dt.date >= start_d) & (df["Date"].dt.date <= end_d)
    out = df.loc[mask].copy()

    if out.empty or len(out) < min_points:
        raise ValueError("Période trop courte")

    return out


def normalize_dedup_date(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # 1) Si Date est déjà une colonne
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"]).dt.normalize()
        out = out.sort_values("Date")
        out = out.drop_duplicates(subset=["Date"], keep="first")
        out = out.reset_index(drop=True)
        return out

    # 2) Sinon, on considère que la date est dans l'index (souvent DatetimeIndex)
    idx = out.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.to_datetime(idx, errors="coerce")
    idx = idx.normalize()

    out = out.copy()
    out.index = idx
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="first")]

    # remettre une vraie colonne Date
    out = out.reset_index().rename(columns={"index": "Date"})
    return out

def build_gated_equity(df_full: pd.DataFrame,
                       df_strat_slice: pd.DataFrame,
                       start_d,
                       end_d):
    """
    Courbe sur toute la période :
    - Buy&Hold avant start
    - Stratégie entre start et end (ancrée sur BH à l’entrée)
    - Buy&Hold après end en gardant la perf (BH "scalé" pour continuité)
    Retourne: out, start_ts_eff, end_ts_eff
    """

    out = normalize_dedup_date(df_full)
    out["Date"] = pd.to_datetime(out["Date"]).dt.normalize()
    out = out.sort_values("Date").drop_duplicates(subset=["Date"]).reset_index(drop=True)

    # Close propre
    close = out["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    out["Returns"] = close.pct_change().fillna(0.0)

    # Buy&Hold "sous-jacent" sur toute la période (base 1)
    out["BH"] = (1.0 + out["Returns"]).cumprod()

    # --- stratégie (fenêtre) ---
    strat = normalize_dedup_date(df_strat_slice)
    strat["Date"] = pd.to_datetime(strat["Date"]).dt.normalize()
    strat = strat.sort_values("Date").drop_duplicates(subset=["Date"])

    if "Position" in strat.columns:
        pos_s = strat.set_index("Date")["Position"].astype(float)
    elif "Signal" in strat.columns:
        pos_s = strat.set_index("Date")["Signal"].shift(1).fillna(0.0).astype(float)
    else:
        pos_s = pd.Series(dtype=float)

    out_i = out.set_index("Date")

    # snap start/end au plus proche jour disponible
    start_ts = pd.Timestamp(start_d).normalize()
    end_ts   = pd.Timestamp(end_d).normalize()

    dates = out_i.index
    start_ts_eff = dates[dates.get_indexer([start_ts], method="nearest")][0]
    end_ts_eff   = dates[dates.get_indexer([end_ts], method="nearest")][0]
    if end_ts_eff < start_ts_eff:
        start_ts_eff, end_ts_eff = end_ts_eff, start_ts_eff

    active = (out_i.index >= start_ts_eff) & (out_i.index <= end_ts_eff)

    # positions alignées sur tout l’index
    pos_aligned = pos_s.reindex(out_i.index).fillna(0.0)

    # 1) perf stratégie RELATIVE (base 1) uniquement sur la fenêtre
    r = out_i["Returns"]
    strat_rel = pd.Series(1.0, index=out_i.index)

    # cumprod dans la fenêtre (ancrée à 1 au début de fenêtre)
    strat_rel.loc[active] = (1.0 + r.loc[active] * pos_aligned.loc[active]).cumprod()
    strat_rel.loc[active] /= strat_rel.loc[start_ts_eff]  # force = 1 à l'entrée

    # 2) ancrage sur BH à l’entrée
    bh_start = float(out_i.loc[start_ts_eff, "BH"])
    strategy_window = bh_start * strat_rel

    # 3) hors fenêtre : BH avant, BH scalé après pour continuité
    out_i["Strategy"] = out_i["BH"]  # avant start => BH

    out_i.loc[active, "Strategy"] = strategy_window.loc[active]

    # scale après end pour garder la perf atteinte
    strat_end = float(out_i.loc[end_ts_eff, "Strategy"])
    bh_end = float(out_i.loc[end_ts_eff, "BH"])
    scale = strat_end / bh_end if bh_end != 0 else 1.0

    after = out_i.index > end_ts_eff
    out_i.loc[after, "Strategy"] = out_i.loc[after, "BH"] * scale

    out = out_i.reset_index()
    return out, start_ts_eff, end_ts_eff
