"""About, methods and data sources (cited inside the app, as the assignment requires)."""
from shiny import ui

from core.theme import tab_header

SOURCES = [
    ("CRSP value-weighted market return (monthly)", "WRDS: crsp.msi (vwretd)",
     "Stock returns for backtests, Monte Carlo and crash replays"),
    ("Fama-French factors (monthly)", "WRDS: ff.factors_monthly",
     "Risk-free (T-bill) rate for cash returns and Sharpe ratios"),
    ("10-year Treasury yield GS10, CPI (CPIAUCSL)", "FRED, Federal Reserve Bank of St. Louis",
     "Bond returns (yield + duration x yield change) and inflation"),
    ("30-year mortgage rate MORTGAGE30US", "Freddie Mac PMMS via FRED",
     "Rent vs. buy and mortgage-rate history"),
    ("2025 Survey of Consumer Finances (released Oct 9 2026)",
     "Federal Reserve Board; age-band percentiles from the public microdata (EfficientDollar)",
     "Net worth percentile vs. U.S. households of the same age"),
    ("Physician Compensation Report 2026; Physician Wealth & Debt Report 2026",
     "Medscape (5,916 U.S. physicians, Sep-Dec 2025), via Becker's Hospital Review",
     "Pay by specialty; physician net worth distribution"),
    ("Medical school debt, Class of 2025", "AAMC Graduation Questionnaire",
     "Debt vs. other new physicians"),
    ("2023 period life table", "Social Security Administration, Office of the Chief Actuary",
     "Life expectancy, planning age, mortality-weighted human capital"),
    ("State Individual Income Tax Rates and Brackets, 2026", "Tax Foundation",
     "State income tax in Cash Flow and the where-to-practice map"),
    ("Regional Price Parities by state, 2023", "U.S. Bureau of Economic Analysis",
     "Cost-of-living adjustment"),
    ("2026 federal brackets, standard deduction", "IRS Rev. Proc. 2025-32", "Federal income tax"),
    ("2026 401(k)/403(b)/457(b), IRA limits, Roth phase-outs", "IRS Notice 2025-67 (IR-2025-111)",
     "Account limits and Roth eligibility"),
    ("2026 HSA limits", "IRS Rev. Proc. 2025-19", "Account limits"),
    ("2026 Social Security wage base", "Social Security Administration", "Payroll tax"),
    ("Repayment Assistance Plan, PSLF", "StudentAid.gov; One Big Beautiful Bill Act (P.L. 119-21)",
     "Student loan strategies"),
]

ASSUMPTIONS = [
    "Returns are real (after inflation). Bond returns are estimated from 10-year Treasury yields "
    "with a 7.5-year duration, not a bond index.",
    "Monte Carlo resamples 12-month blocks of 1953-2024 history, so it assumes the future "
    "looks like a reshuffled past. The out-of-sample check in Tab 2 shows how fragile "
    "'optimal' mixes are.",
    "Retirement goal = 25x yearly spending (4% rule).",
    "Human capital uses 65% of gross pay after tax, SSA survival odds, and a 2% real discount "
    "rate plus 1-3% for income risk by practice type.",
    "Taxes are simplified: standard deduction, no credits, no local income tax.",
    "Medscape surveys are self-reported and skew toward attendings; SCF percentiles are for "
    "households, not individuals.",
]


def about_ui():
    rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in SOURCES)
    return ui.div(
        tab_header("Sources & Methods", "Where every number comes from, and what we assumed.", "info"),
        ui.h3("MD Wealth: built for physicians"),
        ui.p("Physicians start earning 7-15 years late, carry $200k+ of student debt, then see "
             "one of the largest income jumps of any profession. Their biggest asset for most of "
             "their career is their future paychecks. Every tab is built around that path."),
        ui.div(ui.strong("Not financial advice. "),
               "MD Wealth is an educational tool built for a class project. It does not provide "
               "investment, tax, legal or financial advice. Consult a licensed professional.",
               class_="alert alert-warning"),
        ui.h4("Data sources"),
        ui.HTML(f"<table class='table table-sm small'><thead><tr><th>Data</th><th>Source</th>"
                f"<th>Used for</th></tr></thead><tbody>{rows}</tbody></table>"),
        ui.h4("Key assumptions"),
        ui.tags.ul(*[ui.tags.li(a, class_="small") for a in ASSUMPTIONS]),
        class_="p-3",
    )
