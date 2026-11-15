"""Where-to-practice comparison (taxes x cost of living) and rent vs. buy with a physician
mortgage."""
from pathlib import Path

import numpy as np
import pandas as pd

from core import tax_rules as T
from core.benchmarks import STATES, rpp, state_income_tax
from core.cashflow_math import federal_income_tax, payroll_tax

DATA = Path(__file__).resolve().parent.parent / "data"


def latest_mortgage_rate():
    """Latest weekly 30-year fixed rate from FRED (MORTGAGE30US), in percent, and its date."""
    df = pd.read_csv(DATA / "fred_MORTGAGE30US.csv").dropna()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    return float(df["value"].iloc[-1]), str(df["date"].iloc[-1])


def mortgage_history():
    df = pd.read_csv(DATA / "fred_MORTGAGE30US.csv")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna()


def state_comparison(md_income, spouse_income, status):
    """Take-home pay in every state, and what it is worth after local prices (BEA RPP)."""
    spouse = spouse_income if status == "Married filing jointly" else 0
    gross = md_income + spouse
    fed = federal_income_tax(max(0, gross - T.STANDARD_DEDUCTION[status]), status)
    fica = payroll_tax([md_income, spouse], status)
    rows = []
    for code, name in STATES.items():
        st = state_income_tax(gross, code, status)
        take = gross - fed - fica - st
        price = rpp(code)
        rows.append({"state": code, "State": name, "State tax": st,
                     "Take-home": take, "Cost of living (US=100)": price,
                     "Take-home in U.S.-average dollars": take / (price / 100)})
    df = pd.DataFrame(rows).sort_values("Take-home in U.S.-average dollars", ascending=False)
    df["Rank"] = np.arange(1, len(df) + 1)
    return df


def rent_vs_buy(price, rent_month, years, rate, down_pct, closing_pct=0.03, sell_pct=0.06,
                prop_tax=0.011, maint=0.01, insurance=0.0035, pmi=0.0, home_growth=0.035,
                rent_growth=0.03, invest_return=0.06):
    """Year-by-year net worth of buying minus renting (nominal $).

    Whoever has the lower housing cost each year invests the difference, and the renter
    invests the down payment + closing costs on day one. Buyer's net worth = home value
    - loan - selling costs + their side investments. Mortgage interest deduction ignored
    (most physician households take the standard deduction).
    """
    loan = price * (1 - down_pct)
    m_rate = rate / 12
    n = 360
    pay_m = loan * m_rate / (1 - (1 + m_rate) ** -n) if m_rate > 0 else loan / n
    bal, home = loan, price
    renter = price * (down_pct + closing_pct)
    owner = 0.0
    rent = rent_month * 12
    out = []
    for y in range(1, years + 1):
        interest_paid = 0.0
        for _ in range(12):
            i = bal * m_rate
            interest_paid += i
            bal = max(0.0, bal - (pay_m - i))
        own_cost = pay_m * 12 + home * (prop_tax + maint + insurance)
        if pmi and bal > 0.8 * price:
            own_cost += loan * pmi
        diff = own_cost - rent
        renter = renter * (1 + invest_return) + max(0.0, diff)
        owner = owner * (1 + invest_return) + max(0.0, -diff)
        home *= 1 + home_growth
        rent *= 1 + rent_growth
        owner_nw = home * (1 - sell_pct) - bal + owner
        out.append({"year": y, "buy_minus_rent": owner_nw - renter, "owner_nw": owner_nw,
                    "renter_nw": renter, "monthly_payment": pay_m, "first_year_cost": None})
    df = pd.DataFrame(out)
    df.loc[0, "first_year_cost"] = (pay_m * 12 + price * (prop_tax + maint + insurance)) / 12
    return df


def break_even_year(df):
    pos = df[df["buy_minus_rent"] > 0]
    return int(pos["year"].iloc[0]) if len(pos) else None
