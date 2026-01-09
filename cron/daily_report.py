# cron/daily_report.py
# SCRIPT A EXECUTER PAR CRON (Feature 6)

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------
# PATHS (portable, multi-machine safe)
# ---------------------------------------------------------
CRON_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CRON_DIR.parent
DATA_DIR = CRON_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Permet l'import des modules du projet lors d'une exécution par cron
sys.path.insert(0, str(PROJECT_ROOT))

from modules.strategy_single import compute_metrics

# ---------------------------------------------------------
# TICKERS DU PROJET (SOURCE UNIQUE)
# ---------------------------------------------------------
ticker_dict = {
    "Actions US": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "Indices": ["^GSPC", "^DJI", "^IXIC"],
}

# Liste unique et triée des tickers à traiter
ALL_TICKERS = sorted({t for group in ticker_dict.values() for t in group})
TODAY = date.today().isoformat()

# ---------------------------------------------------------
# Utils
# ---------------------------------------------------------
def flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Aplatissement des colonnes MultiIndex retournées par yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    return df


def generate_report_for_ticker(ticker: str):
    # Fichiers de sortie (OK / erreur) spécifiques au ticker
    output_file = DATA_DIR / f"daily_report_{ticker}_{TODAY}.txt"
    error_file = DATA_DIR / f"daily_report_ERROR_{ticker}_{TODAY}.txt"

    try:
        # Téléchargement des données sur 1 an
        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            auto_adjust=False,
            progress=False,
        )

        # Validation des données reçues
        if df is None or df.empty:
            raise ValueError("No data returned by yfinance.")

        df = flatten_yf_columns(df)

        if not {"Open", "Close"}.issubset(df.columns):
            raise ValueError("Missing Open/Close columns.")

        # Série de clôture utilisée pour le calcul des métriques
        close_series = df["Close"]
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]

        df_strat = pd.DataFrame({"Strategy": close_series.values})
        metrics = compute_metrics(df_strat, column="Strategy")

        # Dernière observation disponible
        latest = df.iloc[-1]

        # Écriture du rapport journalier
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"DAILY REPORT — {ticker} — {TODAY}\n")
            f.write("=" * 45 + "\n")
            f.write(f"Latest Open  : {float(latest['Open']):.2f}\n")
            f.write(f"Latest Close : {float(latest['Close']):.2f}\n")
            f.write(f"Volatility (ann.) : {metrics['Volatility (ann.)']*100:.2f} %\n")
            f.write(f"Max Drawdown     : {abs(metrics['Max Drawdown'])*100:.2f} %\n")
            f.write("=" * 45 + "\n")

        print(f"[OK] {ticker}")

    except Exception as e:
        # Écriture d'un fichier d'erreur dédié (robustesse cron)
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(f"ERROR generating report for {ticker} ({TODAY})\n")
            f.write(str(e) + "\n")

        print(f"[ERROR] {ticker}: {e}")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    print(f"Generating daily reports for {len(ALL_TICKERS)} tickers…")
    for tkr in ALL_TICKERS:
        generate_report_for_ticker(tkr)
    print("Done.")
