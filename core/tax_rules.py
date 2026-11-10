"""2026 tax and contribution rules, looked up from official sources (Nov 2026).

Sources:
- Federal brackets and standard deduction: IRS Revenue Procedure 2025-32
  (IRS news release, Oct 9 2025).
- 401(k)/403(b)/457(b), IRA limits and Roth IRA phase-outs: IRS Notice 2025-67
  (IRS news release IR-2025-111, Nov 13 2025).
- HSA limits: IRS Revenue Procedure 2025-19.
- Social Security wage base: Social Security Administration, 2026 contribution
  and benefit base (Federal Register, Nov 3 2025).
- Repayment Assistance Plan (RAP) and PSLF: StudentAid.gov; One Big Beautiful
  Bill Act (P.L. 119-21). RAP opened July 1 2026.
Update these numbers each year.
"""

TAX_YEAR = 2026

# Federal income tax brackets: (top of bracket, rate)
BRACKETS = {
    "Married filing jointly": [(24_800, 0.10), (100_800, 0.12), (211_400, 0.22),
                               (403_550, 0.24), (512_450, 0.32), (768_700, 0.35),
                               (float("inf"), 0.37)],
    "Single": [(12_400, 0.10), (50_400, 0.12), (105_700, 0.22), (201_775, 0.24),
               (256_225, 0.32), (640_600, 0.35), (float("inf"), 0.37)],
}
STANDARD_DEDUCTION = {"Married filing jointly": 32_200, "Single": 16_100}

# Payroll (FICA) taxes
SS_RATE, SS_WAGE_BASE = 0.062, 184_500
MEDICARE_RATE, ADDL_MEDICARE_RATE = 0.0145, 0.009
ADDL_MEDICARE_THRESHOLD = {"Married filing jointly": 250_000, "Single": 200_000}

# Account contribution limits
LIMIT_401K_403B_457B = 24_500
CATCHUP_50_PLUS = 8_000
CATCHUP_60_TO_63 = 11_250
LIMIT_IRA = 7_500
LIMIT_HSA = {"Self-only": 4_400, "Family": 8_750}
ROTH_PHASEOUT = {"Married filing jointly": (242_000, 252_000), "Single": (153_000, 168_000)}

# Student loans
PSLF_YEARS = 10                 # 120 qualifying monthly payments
RAP_DEPENDENT_CREDIT = 50       # $ per dependent per month
RAP_MIN_PAYMENT = 10            # $ per month