"""Risk tolerance (what the client says), risk capacity (what their finances can absorb),
human capital, and the profile -> portfolio rule (a glide path)."""
import numpy as np

from core.benchmarks import survival_curve

TRAINING_STAGES = ("Medical Student", "Resident", "Fellow")
PRACTICE_TYPES = ["Employed (hospital / academic)", "Private practice (partner)",
                  "Locums / 1099 contractor"]

# Five-question tolerance quiz. Each answer scores 1 (cautious) to 4 (aggressive).
RISK_QUESTIONS = [
    ("If your investments fell 25% in one year, you would…",
     ["Sell everything", "Sell some", "Hold and wait", "Buy more"]),
    ("Your main goal for this money is…",
     ["Keep it safe", "Steady income", "Balanced growth", "Maximum growth"]),
    ("Which one-year range of results would you pick?",
     ["-5% to +8%", "-12% to +18%", "-22% to +30%", "-35% to +45%"]),
    ("Your investing experience is…",
     ["None", "Savings accounts / CDs", "Index funds or a 401(k)", "Individual stocks, options"]),
    ("You open your account and see it dropped $50,000 this month. You feel…",
     ["Panicked", "Worried", "Uneasy but fine", "It's a sale"]),
]

# How safe each job's paycheck is: (income risk premium for discounting, stability 0-1)
INCOME_RISK = {
    "Employed (hospital / academic)": (0.010, 1.0),
    "Private practice (partner)": (0.020, 0.7),
    "Locums / 1099 contractor": (0.030, 0.4),
}
REAL_RISK_FREE = 0.02     # long-run real T-bill/TIPS-like rate
AFTER_TAX_SHARE = 0.65    # rough share of gross pay a physician keeps after all taxes


def tolerance_score(answers):
    """0 (very cautious) .. 100 (very aggressive)."""
    a = [int(x) for x in answers]
    return round((sum(a) - len(a)) / (3 * len(a)) * 100)


def _earnings_path(p):
    """Physician's expected gross earnings each year from now until retirement (today's $)."""
    years = max(0, p.target_retire_age - p.age)
    return np.array([p.current_income if t < p.training_years_left else p.expected_attending_income
                     for t in range(years)], dtype=float)


def human_capital(p, from_year=0):
    """Present value of future after-tax earnings, weighted by the chance of being alive
    (SSA life table) and discounted at a real rate that is higher for riskier paychecks."""
    prem, _ = INCOME_RISK.get(p.practice_type, (0.02, 0.7))
    r = REAL_RISK_FREE + prem
    earn = _earnings_path(p)[from_year:] * AFTER_TAX_SHARE
    surv = survival_curve(p.age + from_year, p.sex).to_numpy()
    surv = np.pad(surv, (0, max(0, len(earn) + 1 - len(surv))))[1:len(earn) + 1]
    disc = (1 + r) ** -np.arange(1, len(earn) + 1)
    return float((earn * surv * disc).sum())


def capacity_score(p):
    """0 (fragile) .. 100 (can absorb big losses). Five parts, 20 points each."""
    years = max(0, p.target_retire_age - p.age)
    ef_months = p.savings / p.monthly_expenses if p.monthly_expenses > 0 else 12
    debt_ratio = p.student_loans / max(1.0, p.expected_attending_income)
    _, stability = INCOME_RISK.get(p.practice_type, (0.02, 0.7))
    parts = {
        "Time until retirement": min(20.0, years * 0.8),
        "Emergency fund": min(20.0, ef_months / 6 * 20),
        "Debt vs. future income": 20.0 * (1 - min(1.0, debt_ratio / 1.5)),
        "Paycheck stability": 8 + 12 * stability,
        "Disability insurance": 20.0 if p.disability_insurance else 6.0,
    }
    return round(sum(parts.values())), parts


def recommended_equity(p, financial_wealth=None, age=None, hc=None):
    """Recommended % in stocks, with the reasons. Rule (a glide path):

        start at 110 - age                     (classic age rule)
        + up to +/-15 from risk tolerance        (what the client can stand)
        + up to +10 for bond-like human capital  (big, safe future paychecks)
        then capped by risk capacity: 50 + 0.45 x capacity  (what they can absorb)
        kept between 20% and 95%, rounded to 5%.
    """
    age = p.age if age is None else age
    fw = max(1.0, (p.savings + p.retirement_accounts) if financial_wealth is None else financial_wealth)
    hc = human_capital(p) if hc is None else hc
    tol = tolerance_score(p.risk_answers())
    cap, _ = capacity_score(p)
    _, stability = INCOME_RISK.get(p.practice_type, (0.02, 0.7))

    base = 110 - age
    tol_adj = (tol - 50) * 0.3
    hc_share = hc / (hc + fw)
    hc_adj = 10 * hc_share * stability
    raw = base + tol_adj + hc_adj
    ceiling = 50 + 0.45 * cap
    final = int(np.clip(min(round(raw / 5) * 5, np.floor(ceiling / 5) * 5), 20, 95))
    return {"equity": final, "base": base, "tol_adj": tol_adj, "hc_adj": hc_adj,
            "raw": raw, "ceiling": ceiling, "tolerance": tol, "capacity": cap,
            "hc_share": hc_share, "capped": raw > ceiling}


def glide_path(p, contributions, real_return=0.04):
    """Recommended stock % for every year until retirement. Financial wealth grows with
    contributions at a modest real return, while human capital is used up."""
    years = max(1, p.target_retire_age - p.age)
    fw = max(0.0, p.savings + p.retirement_accounts)
    out = []
    for t in range(years):
        rec = recommended_equity(p, financial_wealth=fw, age=p.age + t, hc=human_capital(p, t))
        out.append(rec["equity"])
        fw = fw * (1 + real_return) + (contributions[t] if t < len(contributions) else 0)
    return np.array(out, dtype=float)


def balance_sheet_path(p, contributions, real_return=0.04):
    """(ages, financial wealth, human capital) each year: the lifetime balance sheet."""
    years = max(1, p.target_retire_age - p.age)
    fw = max(0.0, p.savings + p.retirement_accounts)
    ages, fws, hcs = [], [], []
    for t in range(years + 1):
        ages.append(p.age + t)
        fws.append(fw)
        hcs.append(human_capital(p, t) if t < years else 0.0)
        fw = fw * (1 + real_return) + (contributions[t] if t < len(contributions) else 0)
    return np.array(ages), np.array(fws), np.array(hcs)


def mismatch_message(tol, cap):
    if tol - cap >= 20:
        return ("Tolerance is higher than capacity: the client is comfortable with risk their "
                "finances can't yet absorb. Build the emergency fund and get disability "
                "insurance before taking more market risk.")
    if cap - tol >= 20:
        return ("Capacity is higher than tolerance: the finances could handle more risk than "
                "the client is comfortable with. The plan respects the comfort level, but "
                "education about long-run returns may help.")
    return "Tolerance and capacity agree, so the recommendation follows both."
