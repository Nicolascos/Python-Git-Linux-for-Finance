import pandas as pd
import numpy as np


def prepare_ohlc_df(df: pd.DataFrame) -> pd.DataFrame:
    # Assure une colonne Date (renomme Datetime si besoin) + tri/dedup
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
    # Extrait une fenêtre [start_d, end_d] avec un minimum de points
    start_d = pd.Timestamp(start_d).date()
    end_d = pd.Timestamp(end_d).date()

    mask = (df["Date"].dt.date >= start_d) & (df["Date"].dt.date <= end_d)
    out = df.loc[mask].copy()

    if out.empty or len(out) < min_points:
        raise ValueError("Période trop courte")

    return out


def normalize_dedup_date(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # 1) Cas standard : Date en colonne
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"]).dt.normalize()
        out = out.sort_values("Date")
        out = out.drop_duplicates(subset=["Date"], keep="first")
        out = out.reset_index(drop=True)
        return out

    # 2) Sinon : Date dans l'index (DatetimeIndex attendu)
    idx = out.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.to_datetime(idx, errors="coerce")
    idx = idx.normalize()

    out = out.copy()
    out.index = idx
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="first")]

    # Remet Date en colonne
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

    # Nettoyage + déduplication sur Date
    out = normalize_dedup_date(df_full)
    out["Date"] = pd.to_datetime(out["Date"]).dt.normalize()
    out = out.sort_values("Date").drop_duplicates(subset=["Date"]).reset_index(drop=True)

    # Série Close (garde-fou si Close est un DataFrame)
    close = out["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    # Rendements journaliers + Buy&Hold (base 1)
    out["Returns"] = close.pct_change().fillna(0.0)
    out["BH"] = (1.0 + out["Returns"]).cumprod()

    # --- stratégie (fenêtre) ---
    strat = normalize_dedup_date(df_strat_slice)
    strat["Date"] = pd.to_datetime(strat["Date"]).dt.normalize()
    strat = strat.sort_values("Date").drop_duplicates(subset=["Date"])

    # Position : priorise Position, sinon Signal (shifté d’un jour)
    if "Position" in strat.columns:
        pos_s = strat.set_index("Date")["Position"].astype(float)
    elif "Signal" in strat.columns:
        pos_s = strat.set_index("Date")["Signal"].shift(1).fillna(0.0).astype(float)
    else:
        pos_s = pd.Series(dtype=float)

    out_i = out.set_index("Date")

    # Snap start/end sur les dates réellement présentes dans out_i
    start_ts = pd.Timestamp(start_d).normalize()
    end_ts   = pd.Timestamp(end_d).normalize()

    dates = out_i.index
    start_ts_eff = dates[dates.get_indexer([start_ts], method="nearest")][0]
    end_ts_eff   = dates[dates.get_indexer([end_ts], method="nearest")][0]
    if end_ts_eff < start_ts_eff:
        start_ts_eff, end_ts_eff = end_ts_eff, start_ts_eff

    active = (out_i.index >= start_ts_eff) & (out_i.index <= end_ts_eff)

    # Positions alignées sur l’index complet (0 hors fenêtre par défaut)
    pos_aligned = pos_s.reindex(out_i.index).fillna(0.0)

    # 1) Performance relative de la stratégie (base 1) sur la fenêtre uniquement
    r = out_i["Returns"]
    strat_rel = pd.Series(1.0, index=out_i.index)

    strat_rel.loc[active] = (1.0 + r.loc[active] * pos_aligned.loc[active]).cumprod()
    strat_rel.loc[active] /= strat_rel.loc[start_ts_eff]  # ancre à 1 à l’entrée

    # 2) Ancrage sur la valeur BH à l’entrée
    bh_start = float(out_i.loc[start_ts_eff, "BH"])
    strategy_window = bh_start * strat_rel

    # 3) Construction de la courbe finale (BH avant, stratégie pendant, BH scalé après)
    out_i["Strategy"] = out_i["BH"]
    out_i.loc[active, "Strategy"] = strategy_window.loc[active]

    strat_end = float(out_i.loc[end_ts_eff, "Strategy"])
    bh_end = float(out_i.loc[end_ts_eff, "BH"])
    scale = strat_end / bh_end if bh_end != 0 else 1.0

    after = out_i.index > end_ts_eff
    out_i.loc[after, "Strategy"] = out_i.loc[after, "BH"] * scale

    out = out_i.reset_index()
    return out, start_ts_eff, end_ts_eff
