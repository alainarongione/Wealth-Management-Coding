"""Loads the cached CSV files in data/ into one table of monthly returns."""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
BOND_DURATION = 7.5  # typical duration of a 10-year Treasury bond


def _monthly(df, col):
    df = df.copy()
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
    return df.groupby("month")[col].last()


def load_returns():
    """Monthly returns for stocks, bonds and cash, plus inflation (all decimals)."""
    # Stocks: CRSP value-weighted market return (WRDS)
    stocks = _monthly(pd.read_csv(DATA / "crsp_stock_monthly.csv"), "vwretd")

    # Cash: Fama-French risk-free rate (WRDS)
    cash = _monthly(pd.read_csv(DATA / "ff_factors_monthly.csv"), "rf")
    if cash.abs().max() > 0.05:  # stored in percent -> convert to decimal
        cash = cash / 100

    # Bonds: estimated from the 10-year Treasury yield (FRED GS10)
    # return = last month's yield / 12  -  duration x change in yield
    y = _monthly(pd.read_csv(DATA / "fred_GS10.csv"), "value") / 100
    bonds = y.shift(1) / 12 - BOND_DURATION * (y - y.shift(1))

    # Inflation: change in CPI (FRED CPIAUCSL)
    cpi = _monthly(pd.read_csv(DATA / "fred_CPIAUCSL.csv"), "value")
    inflation = cpi.pct_change()

    df = pd.concat({"stocks": stocks, "bonds": bonds, "cash": cash,
                    "inflation": inflation}, axis=1).dropna()
    return df