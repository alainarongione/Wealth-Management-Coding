"""Taxes, take-home pay, student loan strategies and goal checks."""
import math

from core import tax_rules as T


# ---------- Taxes ----------

def federal_income_tax(taxable, status):
    tax, lower = 0.0, 0.0
    for top, rate in T.BRACKETS[status]:
        if taxable > lower:
            tax += (min(taxable, top) - lower) * rate
        lower = top
    return tax


def payroll_tax(wages, status):
    """wages = list of each earner's wages."""
    ss = sum(min(w, T.SS_WAGE_BASE) for w in wages) * T.SS_RATE
    medicare = sum(wages) * T.MEDICARE_RATE
    extra = max(0, sum(wages) - T.ADDL_MEDICARE_THRESHOLD[status]) * T.ADDL_MEDICARE_RATE
    return ss + medicare + extra


# ---------- Student loans ----------

def rap_monthly_payment(agi, dependents):
    """Repayment Assistance Plan: 1%-10% of AGI depending on income band."""
    if agi <= 10_000:
        base = T.RAP_MIN_PAYMENT * 12
    else:
        pct = min(10, math.ceil((agi - 10_000) / 10_000)) / 100
        base = agi * pct
    return max(T.RAP_MIN_PAYMENT, base / 12 - T.RAP_DEPENDENT_CREDIT * dependents)


def amortized_payment(balance, rate, years):
    """Fixed yearly payment that pays off balance in `years`."""
    if balance <= 0:
        return 0.0
    if rate == 0:
        return balance / years
    return balance * rate / (1 - (1 + rate) ** -years)


def run_loan(balance, rate, pay_rule, max_years=30, forgive_after=None):
    """Year-by-year loan simulation.

    pay_rule(t, balance) -> (yearly payment, on_rap). Under RAP, interest the
    payment doesn't cover is waived (no negative amortization).
    """
    bal, total, schedule = float(balance), 0.0, []
    for t in range(max_years):
        if bal <= 1:
            break
        interest = bal * rate
        pay, on_rap = pay_rule(t, bal)
        pay = min(pay, bal + interest)
        if on_rap and pay < interest:
            bal = bal  # unpaid interest is waived
        else:
            bal = bal + interest - pay
        total += pay
        schedule.append(pay)
        if forgive_after and t + 1 == forgive_after:
            return {"years": t + 1, "total": total, "forgiven": max(bal, 0), "schedule": schedule}
    return {"years": len(schedule), "total": total, "forgiven": 0.0, "schedule": schedule}


def household_agi(p, t, pretax_rate, status):
    """Adjusted gross income in year t (training vs attending)."""
    md = p.current_income if t < p.training_years_left else p.expected_attending_income
    md_pretax = min(md * pretax_rate, T.LIMIT_401K_403B_457B)
    spouse = p.spouse_income if status == "Married filing jointly" else 0
    return md - md_pretax + spouse


def loan_strategies(p, rate, pretax_rate, status, dependents, nonprofit):
    """Compare ways to repay the student loans."""
    bal, train = p.student_loans, p.training_years_left
    rap = lambda t: rap_monthly_payment(household_agi(p, t, pretax_rate, status), dependents) * 12
    out = {}

    std = amortized_payment(bal, rate, 10)
    out["Standard 10-year plan"] = run_loan(bal, rate, lambda t, b: (std, False))

    def aggressive(t, b):
        if t < train:
            return rap(t), True
        years_left = max(1, 3 - (t - train))
        return amortized_payment(b, rate, years_left), False
    out["RAP in training, then pay off in 3 years"] = run_loan(bal, rate, aggressive)

    if nonprofit:
        out["PSLF: RAP payments for 10 years, rest forgiven"] = run_loan(
            bal, rate, lambda t, b: (rap(t), True), forgive_after=T.PSLF_YEARS)
    return out


# ---------- One year of cash flow ----------

def cash_flow(p, t, pretax_rate, status, state_rate, monthly_expenses, loan_payment_yearly):
    md = p.current_income if t < p.training_years_left else p.expected_attending_income
    spouse = p.spouse_income if status == "Married filing jointly" else 0
    gross = md + spouse
    pretax = min(md * pretax_rate, T.LIMIT_401K_403B_457B)
    deduction = T.STANDARD_DEDUCTION[status]
    fed = federal_income_tax(max(0, gross - pretax - deduction), status)
    fica = payroll_tax([md, spouse], status)
    state = max(0, gross - pretax) * state_rate
    take_home = gross - pretax - fed - fica - state
    living = monthly_expenses * 12
    leftover = take_home - living - loan_payment_yearly
    return {"gross": gross, "pretax": pretax, "federal": fed, "fica": fica, "state": state,
            "take_home": take_home, "loans": loan_payment_yearly, "living": living,
            "leftover": leftover, "agi": gross - pretax}