import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from datetime import datetime

def get_yields_table():
    url = "https://www.boursorama.com/bourse/taux/"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    tables = soup.find_all("table")

    # Chercher la table des taux souverains
    target = None
    for t in tables:
        txt = t.get_text(separator=" ").lower()
        if "france" in txt and "2a" in txt and "10a" in txt:
            target = t
            break

    df = pd.read_html(str(target))[0]

    return df

def get_france_yields():
    df = get_yields_table()

    # On garde uniquement la ligne France
    fr = df[df.iloc[:,0].str.lower() == "france"].copy()

    # On renomme proprement
    fr.columns = ["Pays", "2A", "5A", "7A", "10A", "15A", "20A", "30A"]

    # Remplacement des virgules par des points
    for col in fr.columns[1:]:
        fr[col] = fr[col].str.replace("%", "").str.replace(",", ".").astype(float)

    return fr


def refresh_loop():
    while True:
        print(f"\n=== Refresh @ {datetime.now().strftime('%H:%M:%S')} ===")

        df = get_france_yields()
        print(df)

        time.sleep(5 * 60)  # 5 minutes

if __name__ == "__main__":
    refresh_loop()