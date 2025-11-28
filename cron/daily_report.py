# daily_report.py
# SCRIPT À EXÉCUTER PAR CRON (Feature 6)

import yfinance as yf
import pandas as pd
from datetime import date
import os

# Importez la fonction de calcul des métriques de votre module
# Assurez-vous que le chemin d'importation est correct depuis le contexte d'exécution du cron
try:
    from modules.strategy_single import compute_metrics
except ImportError:
    # Fallback pour exécution standalone si modules n'est pas dans le path
    print("Avertissement: modules/strategy_single.py non trouvé. Assurez-vous que le PATH est correct pour cron.")
    exit()

# --- Paramètres ---
TICKER = "AAPL" # Actif par défaut pour le rapport
# Assurez-vous que le dossier 'data/' existe sur la VM
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f"daily_report_{TICKER}.txt")

def generate_report():
    """
    Télécharge les données et génère un rapport de métriques clés
    (prix, volatilité, Max Drawdown) et l'enregistre sur le disque.
    """
    today = date.today()
    
    # 1. Télécharger les données des 365 derniers jours (pour les métriques annualisées)
    try:
        # Période large pour avoir des métriques annualisées stables
        df = yf.download(TICKER, period="1y", interval="1d", progress=False) 
        
        if df.empty:
            raise ValueError("Aucune donnée yfinance récupérée.")
            
        # 2. Calculer les métriques (Volatilité & Max Drawdown)
        # On utilise le prix de clôture comme base (Buy & Hold)
        df_strat_base = pd.DataFrame({"Strategy": df["Close"]})
        metrics = compute_metrics(df_strat_base, column="Strategy") 
        
        # 3. Récupérer les prix quotidiens récents
        latest_data = df.iloc[-1]
        
        # 4. Écrire le rapport
        with open(OUTPUT_FILE, "a") as f:
            f.write(f"\n--- Rapport Quotidien {today} pour {TICKER} ---\n")
            f.write(f"Prix d'ouverture récent: {latest_data['Open']:.2f} $\n")
            f.write(f"Prix de clôture récent: {latest_data['Close']:.2f} $\n")
            f.write(f"Volatilité annualisée (1 an): {metrics['Volatility (ann.)']*100:.2f} %\n")
            f.write(f"Max Drawdown (1 an): {abs(metrics['Max Drawdown'])*100:.2f} %\n")
            f.write("-------------------------------------\n")
            
        print(f"Rapport généré avec succès dans {OUTPUT_FILE}")

    except Exception as e:
        # En cas d'échec du téléchargement ou du calcul
        with open(OUTPUT_FILE, "a") as f:
            f.write(f"\n--- Rapport {today} ---\n")
            f.write(f"Erreur fatale lors de la génération du rapport pour {TICKER}: {e}\n")
        print(f"Échec de la génération du rapport: {e}")


if __name__ == "__main__":
    # Assurez-vous que le dossier 'data' existe
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    generate_report()