# MD Wealth: Wealth Management for Physicians

A Python Shiny app that takes a physician (or physician family) from
"here is who I am" to "here is what I should do with my money, and what could happen."

Physicians are different from typical households. They start earning late (after 7-15 years
of training), carry $200k+ of student debt, then see one of the largest income jumps of any
profession. For most of their career, their biggest asset is their future paychecks. Every
module is built around that path.

> **Disclaimer:** MD Wealth is an educational tool built for a class project. It is not
> financial, tax, legal or investment advice. The disclaimer also appears in the app (welcome
> pop-up, page footer, About tab and the downloadable report).

## Setup (about 2 minutes)

1. Install Python 3.12 or 3.13 from python.org (on Windows, tick **"Add python.exe to PATH"**).
2. In Positron: **File → Open Folder** and choose this project folder (the one that contains
   `app.py`).
3. Open the Terminal (**Terminal → New Terminal**) and install the packages:
   ```
   pip install -r requirements.txt
   ```
4. Run the app: open `app.py` and click **Run Shiny App** (▶ at the top of the editor), or in
   the Terminal:
   ```
   shiny run --reload app.py
   ```
   Then open http://127.0.0.1:8000 if it doesn't open by itself.
5. In the **Check-up** tab sidebar, choose a saved client (for example *Dr_Maya_Chen*) and
   click **Load**.

All data is already cached in `data/`, so the app needs no WRDS login and no internet
connection. To refresh the market data (optional), run `pip install -r requirements-fetch.txt`
and then `python fetch_data.py`. It asks for your WRDS username and password in the terminal,
and the password is never stored in code.

### Troubleshooting

| Problem | Fix |
|---|---|
| `Error: app.py not found` / `requirements.txt not found` | The Terminal is in the wrong folder. `cd` into the folder that contains `app.py`. |
| `shiny` or `pip` "is not recognized" (Windows) | Use `py -m pip install -r requirements.txt` and `py -m shiny run --reload app.py`. |
| "Python was not found; run without arguments to install from the Microsoft Store" | Use `py` instead of `python`, or turn off the python.exe aliases in Settings → Apps → Advanced app settings → App execution aliases. |
| `DLL load failed ... An Application Control policy has blocked this file` | Windows Smart App Control blocked a package in a virtual environment Positron created. Run `deactivate`, then use your main Python (`py -m shiny run --reload app.py`). |
| `No module named ...` | The packages went to a different Python. Run `py -m pip install -r requirements.txt` with the same command you use to run the app. |
| Browser says "refused to connect" | The app isn't running. Start it and wait for `Application startup complete`, then refresh. |
| `address already in use` | The app is already running in another Terminal. Stop it with Ctrl+C, or add `--port 8001`. |

## What the app does

| Tab | What it shows |
|---|---|
| **1 · Client Profile** | Who the client is (age, state, specialty, career stage, practice type, income, debts). **Absolute** measures: net worth, after-tax savings rate, debt/income, time horizon, human capital. **Relative** measures: net-worth percentile vs. U.S. households of the same age (Fed SCF 2025) and vs. practicing physicians (Medscape 2026), pay vs. specialty average, cost of living, debt vs. other new MDs (AAMC). A 5-question **risk tolerance** quiz vs. a computed **risk capacity** score. **Human capital** (mortality-weighted present value of future pay) and a lifetime balance-sheet chart. **Longevity** from the SSA life table. Save, load and delete clients. |
| **2 · Portfolio** | Turns the profile into a recommended stock/bond mix (age rule + tolerance + human capital, capped by capacity) with a waterfall chart explaining why, and a **glide path** that gets safer with age. Backtest vs. 60/40 and 100% stocks with fees and rebalancing (CRSP, FRED). **In-sample vs. out-of-sample** test of an "optimized" mix. 2,000-path block-bootstrap Monte Carlo fan chart and outcome histogram, with the chance of reaching the retirement goal. |
| **3 · Life Events** | Planned events (fellowship, house, children, going part-time) and unplanned ones (disability with or without insurance, job loss, inheritance, a private-equity buyout of the practice). Replays real crashes (2000, 2008, 2020, 2022) at any age, and shows **sequence-of-returns risk** by sliding the same crash across ages. Shows each event's effect on the odds of reaching the goal. |
| **4 · Cash Flow & Goals** | Monthly take-home pay with 2026 federal, FICA and **state** taxes (the profile's state). Sankey diagram of every dollar. Student-loan strategies (standard, RAP, PSLF). Account priority and asset location with 2026 IRS limits, plus backdoor-Roth logic. Goals dashboard: emergency fund, loans, house, retirement, whether the budget supports Tab 2's savings rate, and disability insurance. |
| **5 · Where to Practice & Home** | U.S. map of after-tax, cost-of-living-adjusted take-home pay for this household in all 50 states + DC, with the client's rank. Rent vs. buy with a **physician mortgage** (5% down, no PMI) vs. a conventional loan, using the latest FRED mortgage rate. |
| **Client Report** | A one-page plan pulling the key result from every tab, with next steps. Download it as HTML and print to PDF. |
| **About & Sources** | Every data source, assumption and the disclaimer. |

Data entered in Tab 1 flows into every other tab. Tab 2's mix, fees, savings rates and history
window drive Tab 3's simulations and Tab 4's goals, and everything feeds the report.

## Sample clients (in `profiles/`)

- **Dr. Maya Chen** (demo persona): 31, internal medicine resident in Pennsylvania, married,
  $240k of loans, nonprofit hospital (PSLF-eligible), no disability insurance.
- **Dr. James Okafor**: 34, orthopedic surgery fellow headed to private practice in Texas, $310k of loans.
- **Dr. Priya Shah**: 41, locums emergency physician in California who wants to retire at 55.

## Data sources

| Data | Source | File |
|---|---|---|
| CRSP value-weighted market return, monthly | WRDS (`crsp.msi`) | `crsp_stock_monthly.csv` |
| Fama-French factors incl. risk-free rate | WRDS (`ff.factors_monthly`) | `ff_factors_monthly.csv` |
| 10-year Treasury yield (GS10, DGS10), CPI (CPIAUCSL), 30-yr mortgage rate (MORTGAGE30US) | FRED, Federal Reserve Bank of St. Louis | `fred_*.csv` |
| Household net worth percentiles by age | Federal Reserve Board, *2025 Survey of Consumer Finances* (released Oct 9 2026); age-band percentiles from the public microdata as tabulated by EfficientDollar | `scf2025_networth_by_age.csv` |
| Physician pay by specialty; physician net worth distribution | Medscape, *Physician Compensation Report 2026* and *Physician Wealth & Debt Report 2026* (5,916 physicians, Sep-Dec 2025), as reported by Becker's Hospital Review | `medscape2026_*.csv` |
| Medical school debt | AAMC, Class of 2025 debt data (Graduation Questionnaire) | `aamc2025_education_debt.csv` |
| Mortality | Social Security Administration, 2023 period life table | `ssa_2023_period_life_table.csv` |
| State income tax brackets | Tax Foundation, *State Individual Income Tax Rates and Brackets, 2026* | `taxfoundation_2026_state_brackets.csv` |
| Cost of living | U.S. Bureau of Economic Analysis, Regional Price Parities by state, 2023 | `bea_rpp_2023_by_state.csv` |
| 2026 federal brackets and standard deduction | IRS Rev. Proc. 2025-32 | `core/tax_rules.py` |
| 2026 401(k)/403(b)/457(b) and IRA limits, Roth phase-outs | IRS Notice 2025-67 (IR-2025-111) | `core/tax_rules.py` |
| 2026 HSA limits | IRS Rev. Proc. 2025-19 | `core/tax_rules.py` |
| 2026 Social Security wage base | Social Security Administration | `core/tax_rules.py` |
| RAP and PSLF rules | StudentAid.gov; One Big Beautiful Bill Act (P.L. 119-21) | `core/tax_rules.py` |

The WRDS and FRED files come from `fetch_data.py`. The benchmark tables (SCF, Medscape, AAMC,
SSA, Tax Foundation, BEA) are small published tables entered by hand from the sources above.
Update all of them yearly.

## Project layout

```
app.py              navbar, shared state, welcome disclaimer
fetch_data.py       one-time download of WRDS + FRED data
core/               all the math (no UI): market data, portfolio, risk & human capital,
                    benchmarks, cash flow & taxes, life events, housing, profile store
modules/            one file per tab (UI + server)
data/               cached CSVs
profiles/           saved clients (JSON)
WRITEUP.md          2-3 page write-up; DEMO_SCRIPT.md pitch plan; CONTRIBUTIONS.md
```

## Known limitations

See `WRITEUP.md`. In short: bond returns are estimated from Treasury yields, the Monte Carlo
assumes the future resembles reshuffled 1953-2024 history, taxes are simplified, Medscape is a
self-reported survey, and regional differences in physician pay are not modeled.
