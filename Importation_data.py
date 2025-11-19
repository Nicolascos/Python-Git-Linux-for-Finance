import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from datetime import datetime

def get_yields_table():
    url = "https://www.boursorama.com/bourse/taux/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Erreur lors du chargement des taux Boursorama : {e}")

    soup = BeautifulSoup(r.text, "html.parser")
    tables = soup.find_all("table")

    target = None
    for t in tables:
        txt = t.get_text(separator=" ").lower()
        if "france" in txt and "2a" in txt and "10a" in txt:
            target = t
            break

    if target is None:
        raise RuntimeError("Impossible de trouver la table des taux France dans la page.")

    df = pd.read_html(str(target))[0]
    return df


def get_france_yields():
    df = get_yields_table()

    # Filtre de la ligne France (nettoyage)
    fr = df[df.iloc[:, 0].str.lower().str.strip() == "france"].copy()

    if fr.empty:
        raise RuntimeError("La ligne 'France' n’a pas été trouvée dans le tableau.")

    # Renommage standardisé
    fr.columns = ["Pays", "2A", "5A", "7A", "10A", "15A", "20A", "30A"]

    # Nettoyage des taux : "2,15%" → 2.15
    for col in fr.columns[1:]:
        fr[col] = (
            fr[col]
            .astype(str)
            .str.replace("%", "")
            .str.replace(",", ".")
            .astype(float)
        )

    return fr


def refresh_loop():
    while True:
        print(f"\n=== Refresh @ {datetime.now().strftime('%H:%M:%S')} ===")
        try:
            df = get_france_yields()
            print(df)
        except Exception as e:
            print(f"Erreur : {e}")

        time.sleep(5 * 60)  # rafraîchissement toutes les 5 minutes


if __name__ == "__main__":
    refresh_loop()
