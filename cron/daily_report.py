# cron/daily_report.py
# SCRIPT A EXECUTER PAR CRON (Feature 6)

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------
# PATHS (portable: marche sur n'importe quelle machine)
# ---------------------------------------------------------
CRON_DIR = Path(__file__).resolve().parent           # .../cron
PROJECT_ROOT = CRON_DIR.parent                       # .../ (racine projet)
DATA_DIR = CRON_DIR / "data"                         # .../cron/data
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Pour importer modules/...
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from modules.strategy_single import compute_metrics
except ImportError:
    print("ERROR: cannot import modules.strategy_single.compute_metrics")
    print("Make sure you run from the project root OR sys.path is correct.")
    raise

# ---------------------------------------------------------
# PARAMETRES
# ---------------------------------------------------------
TICKER = os.environ.get("REPORT_TICKER", "AAPL")  # override possible: REPORT_TICKER=MSFT
TODAY = date.today().isoformat()

# 1 fichier par jour (ecrase a chaque run du meme jour)
OUTPUT_FILE = DATA_DIR / f"daily_report_{TICKER}_{TODAY}.txt"

# Ancien format (legacy) a supprimer pour eviter d'avoir "2 fichiers"
LEGACY_FILE = DATA_DIR / f"daily_report_{TICKER}.txt"


def _flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    yfinance peut renvoyer un DataFrame avec colonnes MultiIndex (ex: ('Close','AAPL')).
    On le remet en colonnes simples: Open/High/Low/Close/Adj Close/Volume.
    """
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    return df


def _cleanup_error_files() -> None:
    """
    Nettoie les rapports ERROR pour éviter d'accumuler des fichiers inutiles dans l'UI.
    On supprime tous les daily_report_ERROR_{TICKER}_*.txt
    """
    pattern_prefix = f"daily_report_ERROR_{TICKER}_"
    for p in DATA_DIR.glob(f"{pattern_prefix}*.txt"):
        try:
            p.unlink()
        except Exception:
            pass


def generate_report() -> None:
    # Nettoyage legacy (sinon tu accumules)
    if LEGACY_FILE.exists():
        try:
            LEGACY_FILE.unlink()
        except Exception:
            pass

    # Nettoyage des fichiers ERROR (sinon tu as un "error" en trop dans la liste)
    _cleanup_error_files()

    try:
        # auto_adjust=False pour garder OHLC cohérents
        df = yf.download(
            TICKER,
            period="1y",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )

        if df is None or df.empty:
            raise ValueError("No data returned by yfinance (empty dataframe).")

        df = _flatten_yf_columns(df)

        required_cols = {"Open", "Close"}
        if not required_cols.issubset(set(df.columns)):
            raise ValueError(
                f"Missing required columns in yfinance data: {required_cols} not found. "
                f"Got: {list(df.columns)}"
            )

        # Close doit etre 1D quoi qu'il arrive
        close_series = df["Close"]
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]
        close_1d = pd.to_numeric(close_series, errors="coerce").to_numpy().reshape(-1)

        # On retire les NaN éventuels (sécurité)
        close_1d = close_1d[~pd.isna(close_1d)]
        if close_1d.size < 30:
            raise ValueError("Not enough valid Close points to compute metrics.")

        df_strat_base = pd.DataFrame({"Strategy": close_1d})
        metrics = compute_metrics(df_strat_base, column="Strategy")

        latest = df.iloc[-1]

        # Ecriture UTF-8, mode "w" => ecrase le fichier du jour a chaque run
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"DAILY REPORT - {TICKER} - {TODAY}\n")
            f.write("=" * 40 + "\n")
            f.write(f"Latest Open : {float(latest['Open']):.2f}\n")
            f.write(f"Latest Close: {float(latest['Close']):.2f}\n")
            f.write(f"Annualized Volatility (1y): {float(metrics['Volatility (ann.)']) * 100:.2f} %\n")
            f.write(f"Max Drawdown (1y): {abs(float(metrics['Max Drawdown'])) * 100:.2f} %\n")
            f.write("=" * 40 + "\n")

        # Sécurité: si un fichier ERROR du jour existe encore (ex: run précédent planté), on le supprime
        err_file_today = DATA_DIR / f"daily_report_ERROR_{TICKER}_{TODAY}.txt"
        if err_file_today.exists():
            try:
                err_file_today.unlink()
            except Exception:
                pass

        print(f"OK: report written to {OUTPUT_FILE}")

    except Exception as e:
        # En cas d'erreur: on ecrit un fichier erreur du jour (ecrase)
        err_file = DATA_DIR / f"daily_report_ERROR_{TICKER}_{TODAY}.txt"
        with open(err_file, "w", encoding="utf-8") as f:
            f.write(f"ERROR generating report for {TICKER} ({TODAY})\n")
            f.write(str(e) + "\n")

        print(f"ERROR generating report: {e}")


if __name__ == "__main__":
    generate_report()
