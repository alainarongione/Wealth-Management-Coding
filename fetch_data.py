"""
Run this ONCE to download data into the data/ folder.
The app only reads the saved CSV files, so the demo never needs WRDS.
Your WRDS password is typed into the terminal, never saved in this code.
"""
from pathlib import Path
import getpass
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(exist_ok=True)


def get_wrds_data():
    import psycopg
    user = input("WRDS username: ")
    pw = getpass.getpass("WRDS password (hidden while typing): ")
    print("Connecting... approve the Duo push on your phone if you get one.")
    conn = psycopg.connect(host="wrds-pgdata.wharton.upenn.edu", port=9737,
                           dbname="wrds", user=user, password=pw, sslmode="require",
                           autocommit=True)

    def save(sql, filename, label):
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                cols = [c.name for c in cur.description]
                df = pd.DataFrame(cur.fetchall(), columns=cols)
            df.to_csv(DATA / filename, index=False)
            print(f"Saved {label}: {len(df)} rows")
        except Exception as e:
            print(f"SKIPPED {label} (no access): {e}")

    # CRSP value-weighted stock market return (monthly)
    save("select date, vwretd from crsp.msi order by date",
         "crsp_stock_monthly.csv", "CRSP stock returns")

    # Fama-French factors (monthly) - includes the risk-free (T-bill) rate
    save("select date, mktrf, smb, hml, rf from ff.factors_monthly order by date",
         "ff_factors_monthly.csv", "Fama-French factors")

    conn.close()


def get_fred_data():
    # Non-WRDS source: Federal Reserve Bank of St. Louis (FRED)
    series = {
        "CPIAUCSL": "Consumer Price Index (inflation)",
        "MORTGAGE30US": "30-year mortgage rate",
        "GS10": "10-year Treasury yield (monthly, used for bond returns)",
    }
    for sid, label in series.items():
        df = pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}")
        df.columns = ["date", "value"]
        df.to_csv(DATA / f"fred_{sid}.csv", index=False)
        print(f"Saved FRED {label}: {len(df)} rows")


if __name__ == "__main__":
    get_fred_data()
    get_wrds_data()
    print("\nDone! Check your data/ folder.")