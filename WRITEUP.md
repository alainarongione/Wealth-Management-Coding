# MD Wealth: Wealth Management for Physicians

*Final project write-up · Section 001, Group 5*

## 1. Target client

MD Wealth is built for **physicians and physician families**, from medical school through
retirement. Their financial lives differ from a typical household's in four ways that drive
every design choice in the app:

1. **Late start, huge jump.** A physician earns little until about age 30-35 (residents earn
   roughly $65-85k), then income jumps four- to eight-fold. Medscape's 2026 report puts average
   pay at $386,000, from $266,000 (pediatrics) to $611,000 (orthopedics).
2. **Heavy early debt.** The median indebted 2025 MD graduate owes $215,000 (AAMC), so most
   residents have negative net worth. Comparing them with "Americans aged 30-34" makes them
   look like failures. Comparing them with other physicians, and counting their human capital,
   gives the true picture.
3. **Human capital dominates.** For our demo client, future paychecks are worth about $3.6
   million and financial assets are almost zero. That asset is bond-like (stable demand,
   employed contracts), which supports more stock risk early. It is also fragile: one
   career-ending injury erases it, which makes own-occupation disability insurance essential.
4. **Choices other households don't face.** PSLF vs. refinancing, fellowship vs. starting
   practice, where to practice (state taxes and cost of living differ hugely), physician
   mortgages, 403(b) + 457(b) stacking, backdoor Roth IRAs, and private-equity buyouts of
   practices.

**Peer groups.** We compare each client to (a) U.S. households of the same age band (Federal
Reserve SCF 2025), (b) practicing physicians (Medscape Wealth & Debt Report 2026), (c) their
specialty's average pay, and (d) other new MDs' debt (AAMC Class of 2025).

**Geography.** The client's state drives state income tax (Tax Foundation 2026 brackets) and
cost of living (BEA Regional Price Parities). Tab 5 maps both across all states.

## 2. What each module does

**Module 1: Client Profile.** The client enters age, sex, state, filing status, children,
specialty, career stage, practice type, PSLF eligibility, disability insurance, incomes,
assets, debts and spending. Profiles can be saved, loaded and deleted (JSON files).

- *Absolute measures:* net worth, after-tax savings rate, debt/income, years to retirement,
  planning horizon, human capital.
- *Relative measures:* net-worth percentile vs. same-age households and vs. physicians, pay
  vs. specialty average, cost-of-living-adjusted pay, debt vs. AAMC.
- *Risk tolerance vs. capacity:* tolerance comes from a 5-question quiz (0-100). Capacity
  (0-100) is computed from five 20-point parts: time to retirement, emergency fund, debt vs.
  future income, paycheck stability (employed > private practice > locums), and disability
  insurance. The app explains any mismatch between the two.
- *Human capital:* the present value of future after-tax pay. Each year is weighted by the
  SSA probability of being alive and discounted at 2% real plus a 1-3% income-risk premium by
  practice type. A lifetime balance-sheet chart shows human capital turning into financial
  wealth.
- *Longevity:* SSA 2023 survival curve. We plan to the age the client still has a 25% chance
  of reaching (91 for our demo client), not average life expectancy (82).

**Module 2: Portfolio.** The profile maps to a stock/bond mix through a transparent rule:

  start at 110 − age, add ±15 for tolerance, add up to +10 for bond-like human capital
  (scaled by paycheck stability), cap at 50 + 0.45 × capacity, and keep between 20% and 95%.

A waterfall chart shows each step. Re-running the rule each year, as human capital is used up
and savings grow, gives a **glide path**. The mix is backtested monthly from 1953 to 2024
against 60/40 and 100% stocks, after inflation, with fees (0.05%, 0.30%, 1.00%) and annual,
monthly or no rebalancing. We report real CAGR, volatility, Sharpe ratio, worst 12 months and
maximum drawdown.

For the *in-sample vs. out-of-sample* test, we choose the best-Sharpe mix using only the first
half of the chosen period, then score it, our rule and 60/40 on the unseen second half. In
our default run the "optimized" mix had the lowest out-of-sample Sharpe. That is why we use a
rule rather than an optimizer.

Uncertainty is shown as a fan chart (10th-90th and 25th-75th percentile bands) and a histogram
from 2,000 block-bootstrap paths that resample 12-month blocks of real history, so crashes and
recoveries stay together. The headline number is a probability (the chance of reaching 25×
retirement spending), not a single point estimate.

**Module 3: Life Events.**
- *Planned:* fellowship (extra low-paid years, higher pay after), buying a house, children
  (cost per child for 18 years), going part-time.
- *Unplanned:* disability with or without insurance, job loss, inheritance, and a
  private-equity buyout of the practice (an up-front payout taxed as capital gains, then a pay
  cut). The buyout is the physician version of an IPO.

Every scenario uses the same random seed, so differences come only from the events. A bar
chart isolates each event's effect on the odds. Real crashes (2000-02, 2007-09, 2020, 2022)
can be replayed month by month at any age. A timing chart slides the same crash across ages to
show **sequence-of-returns risk**: the 2008 crash costs the demo client far more near
retirement than early in her career.

**Module 4: Cash Flow, Tax & Goals.**
- Monthly gross pay to take-home pay using 2026 federal brackets, FICA (with the 2026 wage
  base and Additional Medicare Tax) and the profile state's 2026 brackets.
- A Sankey diagram shows where every dollar goes.
- Student loans: standard 10-year vs. RAP in training then aggressive payoff vs. PSLF
  (RAP payments for 10 years, remainder forgiven tax-free), with total paid and amount forgiven.
- Account priority and asset location (403(b) match → HSA → Roth/backdoor Roth → rest of
  403(b) → 457(b) → taxable), with 2026 IRS limits and Roth phase-out logic.
- Goals dashboard: emergency fund, loans, house down payment, retirement odds from Tab 2,
  whether the budget can actually fund Tab 2's savings rate, and income protection. Each
  "behind" goal shows the specific change that closes the gap.

**Module 5 (extra): Where to Practice & Home.**
- A choropleth map of after-tax, cost-of-living-adjusted take-home pay for this household in
  every state. For the demo client, South Dakota beats California by about $91,000 a year in
  buying power.
- Rent vs. buy comparing a **physician mortgage** (5% down, no PMI, +0.25% rate) with a 20%-down
  conventional loan, using the latest FRED 30-year rate (7.18%, Nov 5 2026). The model invests
  the cost difference so both paths are compared on net worth. It also shows the break-even
  holding period, which matters for residents who may move for fellowship.

**Client Report (extra).** A downloadable one-page HTML plan (printable to PDF) that pulls every
tab's headline result and lists prioritized next steps.

## 3. Data sources

WRDS: CRSP monthly value-weighted market return (`crsp.msi`) and Fama-French monthly factors
including the risk-free rate (`ff.factors_monthly`).

Non-WRDS:
- FRED: GS10 and DGS10 Treasury yields, CPIAUCSL, MORTGAGE30US.
- Federal Reserve 2025 SCF.
- Medscape 2026 compensation and wealth reports.
- AAMC Class of 2025 debt data.
- SSA 2023 period life table.
- Tax Foundation 2026 state brackets.
- BEA 2023 Regional Price Parities.
- IRS Rev. Proc. 2025-32, Notice 2025-67 and Rev. Proc. 2025-19.
- SSA 2026 wage base.
- StudentAid.gov and P.L. 119-21 for RAP and PSLF.

All data is cached as CSV in `data/`, so the demo needs no live connection. The WRDS password
is typed at the terminal and never stored. Sources are cited in each tab, the About tab and the
README.

## 4. Key assumptions

- **Returns.** All returns are real. Stocks = CRSP VW index. Bonds are estimated as last
  month's 10-year yield/12 minus 7.5 × the change in yield. Cash = Fama-French RF. The window
  is 1953-2024 (limited by GS10), adjustable with a slider.
- **Retirement goal.** 25× desired yearly spending (the 4% rule).
- **Savings.** Contributions = savings rate × gross household pay. The training and attending
  rates are set separately. Tab 4 checks whether the budget supports them.
- **Human capital.** 65% of gross pay kept after tax, flat real pay as an attending, SSA
  survival, discount rate 2% real + 1/2/3% for employed/partner/locums.
- **Taxes.** Standard deduction only. No credits, local income taxes or itemizing.
- **PE buyout.** 25% tax on the payout.
- **Physician mortgage.** 5% down, no PMI, +0.25% rate. Closing costs 3%, selling costs 6%,
  property tax 1.1%, maintenance 1%, insurance 0.35%.

## 5. Known limitations

- The bootstrap assumes the future resembles reshuffled U.S. history from one of the best-
  performing markets of the century. It ignores valuations and international diversification.
- Bond returns are an approximation, not a bond index. Credit risk and TIPS are not modeled.
- Medscape data is self-reported and skews toward attendings. The physician net-worth
  distribution covers all ages, so trainees naturally rank low. SCF percentiles are for
  households, and the percentile points are interpolated.
- Regional differences in physician pay are not modeled, only taxes and prices. The state map
  ignores local income taxes (e.g., New York City, Philadelphia).
- The loan model simplifies RAP (no spouse-income exclusion through separate filing, no
  employer loan help). Pre-RAP repayment history is not tracked.
- The risk-capacity weights and the allocation rule are judgment calls. They are transparent
  and explained in the app, but not estimated from data.
- The app models one client at a time and does not track real accounts over time.

**Next steps:** connect real accounts through an aggregator, model specialty-specific
disability and malpractice risk, add region-specific physician pay (e.g., MGMA or Doximity
by metro), and add a "practice like" feature using hospital-system 13F data.
