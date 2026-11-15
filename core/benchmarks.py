"""Peer benchmarks, mortality, state taxes and cost of living (all cached CSVs in data/).

Sources (see README "Data sources" for full citations):
- Household net worth percentiles by age: Federal Reserve Board, 2025 Survey of
  Consumer Finances (released Oct 9 2026), percentiles computed from the public
  microdata (via EfficientDollar's SCF tables). 2025 dollars.
- Physician net worth distribution and pay by specialty: Medscape Physician Wealth &
  Debt Report 2026 and Physician Compensation Report 2026 (5,916 full-time U.S.
  physicians surveyed Sep-Dec 2025), as reported by Becker's Hospital Review.
- Medical school debt: AAMC Graduation Questionnaire, Class of 2025.
- Mortality: Social Security Administration, 2023 period life table (Office of the
  Chief Actuary, Actuarial Life Table).
- State income tax brackets: Tax Foundation, "State Individual Income Tax Rates and
  Brackets, 2026" (as of Jan 1 2026).
- Cost of living: U.S. Bureau of Economic Analysis, Regional Price Parities by
  state, 2023 (all items; U.S. = 100).
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def ordinal(x):
    n = int(round(x))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ---------- loaders (cached) ----------

@lru_cache(None)
def scf_table():
    return pd.read_csv(DATA / "scf2025_networth_by_age.csv")


@lru_cache(None)
def specialty_table():
    return pd.read_csv(DATA / "medscape2026_comp_by_specialty.csv")


@lru_cache(None)
def physician_networth_table():
    return pd.read_csv(DATA / "medscape2026_physician_networth.csv")


@lru_cache(None)
def aamc_debt():
    df = pd.read_csv(DATA / "aamc2025_education_debt.csv")
    return dict(zip(df["measure"], df["value"]))


@lru_cache(None)
def life_table():
    return pd.read_csv(DATA / "ssa_2023_period_life_table.csv").set_index("age")


@lru_cache(None)
def state_brackets():
    return pd.read_csv(DATA / "taxfoundation_2026_state_brackets.csv")


@lru_cache(None)
def rpp_table():
    return pd.read_csv(DATA / "bea_rpp_2023_by_state.csv").set_index("state")["rpp_all_items"]


def specialties():
    return specialty_table()["specialty"].tolist()


def specialty_pay(specialty):
    t = specialty_table()
    row = t[t["specialty"] == specialty]
    return float(row["avg_comp"].iloc[0]) if len(row) else float(t["avg_comp"].median())


# ---------- relative position ----------

def scf_percentile(age, net_worth):
    """Percentile of net worth among all U.S. households whose head is the same age band.

    Linear interpolation between the published percentile points (10/25/50/75/90/95).
    Returns (percentile, age_group_label, row) with percentile clipped to 1..99.
    """
    t = scf_table()
    row = t[(t["age_lo"] <= age) & (t["age_hi"] >= age)].iloc[0]
    pcts = np.array([10, 25, 50, 75, 90, 95])
    vals = row[["p10", "p25", "p50", "p75", "p90", "p95"]].to_numpy(dtype=float)
    if net_worth <= vals[0]:
        pct = max(1.0, 10 * (1 - (vals[0] - net_worth) / (abs(vals[0]) + 50_000)))
    elif net_worth >= vals[-1]:
        pct = min(99.0, 95 + 4 * (net_worth - vals[-1]) / vals[-1])
    else:
        pct = float(np.interp(net_worth, vals, pcts))
    return pct, row["age_group"], row


def physician_networth_percentile(net_worth, sex=None):
    """Percentile of net worth among practicing U.S. physicians (Medscape 2026, all ages).

    The survey reports buckets; we assume people are spread evenly inside each bucket.
    """
    t = physician_networth_table()
    col = {"Male": "pct_men", "Female": "pct_women"}.get(sex, "pct_all")
    share = t[col].to_numpy(dtype=float)
    share = share / share.sum() * 100
    lows = t["bucket_low"].to_numpy(dtype=float)
    highs = t["bucket_high"].fillna(10_000_000).to_numpy(dtype=float)
    below = 0.0
    for lo, hi, s in zip(lows, highs, share):
        if net_worth < hi or hi == highs[-1]:
            if lo == 0 and net_worth < 0:
                return 1.0
            frac = min(1.0, max(0.0, (net_worth - lo) / (hi - lo)))
            return float(np.clip(below + frac * s, 1, 99))
        below += s
    return 99.0


def debt_position(student_loans):
    d = aamc_debt()
    med = d["median_debt_indebted"]
    if student_loans <= 0:
        return f"No education debt, like {100 - d['pct_graduates_with_debt']:.0f}% of 2025 MD graduates."
    if student_loans >= 300_000:
        where = f"in the top {d['pct_with_300k_or_more']:.0f}% of borrowers (over $300k)"
    elif student_loans >= 200_000:
        where = f"among the {d['pct_with_200k_or_more']:.0f}% who owe $200k+"
    else:
        where = "below the typical borrower"
    return (f"${student_loans:,.0f} vs. a ${med:,.0f} median for indebted 2025 MD graduates: "
            f"{where}.")


# ---------- mortality ----------

def survival_curve(age, sex):
    """Probability of being alive at each future age, given alive today."""
    lt = life_table()
    col = "female_lives" if sex == "Female" else "male_lives"
    age = int(np.clip(age, lt.index.min(), lt.index.max()))
    lives = lt[col]
    s = lives.loc[age:] / lives.loc[age]
    return s


def life_expectancy(age, sex):
    s = survival_curve(age, sex)
    return age + float(s.iloc[1:].sum()) + 0.5


def planning_age(age, sex, chance=0.25):
    """Age the plan should last to: the age you still have a `chance` of being alive at."""
    s = survival_curve(age, sex)
    over = s[s >= chance]
    return int(over.index.max()) if len(over) else age


# ---------- state taxes and cost of living ----------

def state_income_tax(income, state, status):
    """2026 state income tax on wage income (simplified: standard deduction only,
    no local taxes, credits or exemptions)."""
    b = state_brackets()
    b = b[(b["state"] == state) & (b["status"] == status)]
    if b.empty:
        return 0.0
    taxable = max(0.0, income - float(b["standard_deduction"].iloc[0]))
    starts = b["bracket_start"].to_numpy(dtype=float)
    rates = b["rate"].to_numpy(dtype=float)
    tops = np.append(starts[1:], np.inf)
    return float(sum(max(0.0, min(taxable, hi) - lo) * r
                     for lo, hi, r in zip(starts, tops, rates) if taxable > lo))


def rpp(state):
    return float(rpp_table().get(state, 100.0))
