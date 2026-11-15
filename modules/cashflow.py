import pandas as pd
import plotly.graph_objects as go
from shiny import module, ui, render, reactive
from shinywidgets import output_widget, render_plotly

from core import tax_rules as T
from core.cashflow_math import loan_strategies, cash_flow
from core.benchmarks import STATES
STRATEGIES = ["Standard 10-year plan", "RAP in training, then pay off in 3 years",
              "PSLF: RAP payments for 10 years, rest forgiven"]


@module.ui
def cashflow_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Which year?"),
            ui.input_radio_buttons("view", None, ["Today", "First attending year"]),
            ui.output_ui("from_profile"),
            ui.h5("Taxes"),
            ui.input_slider("pretax", "403(b)/401(k) contribution (% of pay)", 0, 30, 8),
            ui.h5("Spending"),
            ui.input_numeric("att_expenses", "Monthly spending as attending ($)", 9000, step=500),
            ui.h5("Student loans"),
            ui.input_numeric("loan_rate", "Loan interest rate (%)", 7.0, step=0.25),
            ui.input_select("strategy", "Loan plan to use", STRATEGIES),
            ui.h5("Goals"),
            ui.input_numeric("ef_months", "Emergency fund target (months of spending)", 6),
            ui.input_numeric("house_amt", "House down payment needed ($)", 120000, step=10000),
            ui.input_numeric("house_years", "Buy house in how many years?", 4, min=1),
            width=340,
        ),
        ui.layout_columns(
            ui.value_box("Gross pay / month", ui.output_text("gross_box")),
            ui.value_box("Take-home / month", ui.output_text("takehome_box")),
            ui.value_box("Total tax rate", ui.output_text("taxrate_box")),
            ui.value_box("Left to save / month", ui.output_text("left_box")),
        ),
        ui.card(ui.card_header("Goals dashboard"), ui.output_ui("goals")),
        ui.card(ui.card_header("Where every dollar goes (per year)"), output_widget("sankey")),
        ui.card(ui.card_header("Student loan options"), ui.output_table("loan_table"),
        ui.output_ui("loan_note")),
        ui.card(ui.card_header(f"Where to save, in order ({T.TAX_YEAR} IRS limits)"),
                ui.output_table("accounts_table"), ui.output_ui("roth_note")),
        ui.p(f"Sources: IRS Rev. Proc. 2025-32 (tax brackets, standard deduction); IRS Notice "
             f"2025-67 / IR-2025-111 (retirement and IRA limits, Roth phase-outs); IRS Rev. Proc. "
             f"2025-19 (HSA); SSA 2026 wage base; StudentAid.gov (RAP, PSLF); Tax Foundation 2026 "
             f"state brackets. Simplified estimate: ignores itemized deductions, credits and "
             f"local taxes.", class_="text-muted small"),
    )


@module.server
def cashflow_server(input, output, session, profile, results, summary):

    @render.ui
    def from_profile():
        p = profile()
        return ui.div(
            ui.h5("From the profile (Tab 1)"),
            ui.p(f"{STATES.get(p.state, p.state)} · {p.filing_status} · {p.children} children · "
                 f"{'PSLF-eligible employer' if p.nonprofit else 'Not PSLF-eligible'}",
                 class_="small text-muted"),
        )

    @reactive.calc
    def year():
        p = profile()
        return 0 if input.view() == "Today" else p.training_years_left

    @reactive.calc
    def loans():
        p = profile()
        return loan_strategies(p, (input.loan_rate() or 0) / 100, input.pretax() / 100,
                               profile().filing_status, profile().children, profile().nonprofit)

    # Only offer PSLF when the employer qualifies
    @reactive.effect
    def _update_strategies():
        names = list(loans().keys())
        with reactive.isolate():
            current = input.strategy()
        ui.update_select("strategy", choices=names,
                         selected=current if current in names else names[0])

    @reactive.calc
    def chosen():
        plans = loans()
        name = input.strategy() if input.strategy() in plans else list(plans)[0]
        return name, plans[name]

    @reactive.calc
    def cf():
        p, t = profile(), year()
        _, plan = chosen()
        loan_pay = plan["schedule"][t] if t < len(plan["schedule"]) else 0
        expenses = p.monthly_expenses if t < p.training_years_left else (input.att_expenses() or 0)
        return cash_flow(p, t, input.pretax() / 100, profile().filing_status,
                         profile().state, expenses, loan_pay)

    # ----- headline numbers -----
    @render.text
    def gross_box():
        return f"${cf()['gross'] / 12:,.0f}"

    @render.text
    def takehome_box():
        return f"${cf()['take_home'] / 12:,.0f}"

    @render.text
    def taxrate_box():
        c = cf()
        return f"{(c['federal'] + c['fica'] + c['state']) / c['gross']:.0%}" if c["gross"] else "—"

    @render.text
    def left_box():
        return f"${cf()['leftover'] / 12:,.0f}"

    # ----- Sankey -----
    @render_plotly
    def sankey():
        c = cf()
        labels = ["Gross pay", "Federal income tax", "Social Security & Medicare", "State tax",
                  "403(b)/401(k) (pre-tax)", "Take-home pay", "Student loans",
                  "Living expenses", "Left to save/invest"]
        left = max(0, c["leftover"])
        living = min(c["living"], max(0, c["take_home"] - c["loans"]))
        src = [0, 0, 0, 0, 0, 5, 5, 5]
        tgt = [1, 2, 3, 4, 5, 6, 7, 8]
        val = [c["federal"], c["fica"], c["state"], c["pretax"], c["take_home"],
               c["loans"], living, left]
        fig = go.Figure(go.Sankey(
            node=dict(label=[f"{l}<br>${v:,.0f}" for l, v in zip(labels, [c["gross"]] + val)],
                      pad=18, thickness=16),
            link=dict(source=src, target=tgt, value=val)))
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
        return fig

    # ----- loans -----
    @render.table
    def loan_table():
        p = profile()
        t_att = p.training_years_left
        rows = []
        for name, r in loans().items():
            s = r["schedule"]
            rows.append({
                "Plan": name,
                "Payment now ($/mo)": f"${s[0] / 12:,.0f}" if s else "$0",
                "Payment as attending ($/mo)": f"${s[t_att] / 12:,.0f}" if t_att < len(s) else "$0",
                "Total paid": f"${r['total']:,.0f}",
                "Done in": f"{r['years']} yrs",
                "Forgiven (tax-free)": f"${r['forgiven']:,.0f}",
            })
        return pd.DataFrame(rows)

    @render.ui
    def loan_note():
        plans = loans()
        best = min(plans, key=lambda k: plans[k]["total"])
        msg = f"Cheapest option: <b>{best}</b>."
        if profile().nonprofit and profile().filing_status == "Married filing jointly" and profile().spouse_income > 0:
            msg += (" Note: filing jointly adds your spouse's income to the RAP payment, "
                    "which shrinks PSLF forgiveness.")
        if not profile().nonprofit:
            msg += " PSLF requires a nonprofit or government employer."
        return ui.p(ui.HTML(msg), class_="small")

    # ----- accounts -----
    @render.table
    def accounts_table():
        return pd.DataFrame([
            {"Order": 1, "Account": "403(b)/401(k) up to employer match",
             f"{T.TAX_YEAR} limit": f"${T.LIMIT_401K_403B_457B:,} (shared)",
             "Why": "Free money from the employer", "Best to hold": "Bonds"},
            {"Order": 2, "Account": "HSA (if on a high-deductible plan)",
             f"{T.TAX_YEAR} limit": f"${T.LIMIT_HSA['Self-only']:,} self / ${T.LIMIT_HSA['Family']:,} family",
             "Why": "Tax-free in, tax-free growth, tax-free for medical bills",
             "Best to hold": "Stocks"},
            {"Order": 3, "Account": "Roth IRA (backdoor if income is too high)",
             f"{T.TAX_YEAR} limit": f"${T.LIMIT_IRA:,} per spouse",
             "Why": "Tax-free growth forever", "Best to hold": "Stocks"},
            {"Order": 4, "Account": "Rest of 403(b)/401(k)",
             f"{T.TAX_YEAR} limit": f"${T.LIMIT_401K_403B_457B:,} (+${T.CATCHUP_50_PLUS:,} at 50+)",
             "Why": "Pre-tax saves 32-35% for attendings", "Best to hold": "Bonds"},
            {"Order": 5, "Account": "457(b) (many hospitals offer one)",
             f"{T.TAX_YEAR} limit": f"${T.LIMIT_401K_403B_457B:,} (separate limit)",
             "Why": "Doubles pre-tax space. Non-governmental 457(b) is exposed to the hospital's creditors",
             "Best to hold": "Bonds / balanced"},
            {"Order": 6, "Account": "Taxable brokerage", f"{T.TAX_YEAR} limit": "No limit",
             "Why": "Everything else", "Best to hold": "Broad stock index funds (tax-efficient)"},
        ])

    @render.ui
    def roth_note():
        lo, hi = T.ROTH_PHASEOUT[profile().filing_status]
        agi = cf()["agi"]
        if agi >= hi:
            msg = (f"Income ${agi:,.0f} is above the Roth IRA limit (${hi:,}), so use the "
                   f"<b>backdoor Roth</b>: contribute to a traditional IRA, then convert. "
                   f"Watch the pro-rata rule if you already have pre-tax IRA money.")
        elif agi >= lo:
            msg = f"Income ${agi:,.0f} is in the Roth phase-out (${lo:,}-${hi:,}): only a partial direct Roth is allowed."
        else:
            msg = f"Income ${agi:,.0f} is below ${lo:,}, so a direct Roth IRA contribution works."
        return ui.p(ui.HTML(msg), class_="small")

    # ----- goals -----
    @reactive.calc
    def goal_list():
        """Each goal as (title, status, detail, fix)."""
        p, c = profile(), cf()
        out = []

        # Emergency fund
        need = (input.ef_months() or 0) * c["living"] / 12
        have = p.savings
        st = "On track" if have >= need else ("Behind" if have >= need / 2 else "At risk")
        fix = "" if have >= need else f"Save ${(need - have) / 12:,.0f}/mo for a year to close the gap."
        out.append(("Emergency fund", st, f"${have:,.0f} saved of ${need:,.0f} needed.", fix))

        # Student loans
        plans = loans()
        name, plan = chosen()
        best = min(plans, key=lambda k: plans[k]["total"])
        saving = plan["total"] - plans[best]["total"]
        st = "On track" if saving < 1000 else "Behind"
        fix = "" if saving < 1000 else f"Switching to '{best}' saves ${saving:,.0f}."
        out.append(("Student loans", st, f"Debt-free at age {p.age + plan['years']} with '{name}'.", fix))

        # House down payment
        yrs = input.house_years() or 1
        projected = p.savings
        for t in range(yrs):
            exp = p.monthly_expenses if t < p.training_years_left else (input.att_expenses() or 0)
            loan_pay = plan["schedule"][t] if t < len(plan["schedule"]) else 0
            projected += max(0, cash_flow(p, t, input.pretax() / 100, p.filing_status,
                                          p.state, exp, loan_pay)["leftover"])
        target = input.house_amt() or 0
        st = "On track" if projected >= target else ("Behind" if projected >= target * 0.7 else "At risk")
        fix = "" if projected >= target else f"Need ${(target - projected) / (yrs * 12):,.0f}/mo more, or wait longer."
        out.append((f"House in {yrs} yrs", st,
                    f"Projected ${projected:,.0f} of ${target:,.0f} (if all leftover cash is saved).", fix))

        r = results()
        # Retirement (from Tab 2)
        prob = r.get("prob")
        if prob is None:
            out.append(("Retirement", "Behind", "Open Tab 2 to run the projection.", ""))
        else:
            st = "On track" if prob >= 0.8 else ("Behind" if prob >= 0.6 else "At risk")
            fix = "" if prob >= 0.8 else "In Tab 2: raise the attending savings rate or retire later."
            out.append(("Retirement", st, f"{prob:.0%} chance of reaching the goal (Tab 2).", fix))

        # Savings plan from Tab 2: can the monthly budget actually support it?
        if "save_att" in r:
            t_att = p.training_years_left
            lp = plan["schedule"][t_att] if t_att < len(plan["schedule"]) else 0
            first = cash_flow(p, t_att, input.pretax() / 100, p.filing_status, p.state,
                              input.att_expenses() or 0, lp)
            planned = r["save_att"] * (p.expected_attending_income + p.spouse_income)
            available = first["leftover"] + first["pretax"]
            st = ("On track" if available >= planned else
                  ("Behind" if available >= planned * 0.8 else "At risk"))
            fix = "" if available >= planned else (
                f"Cut attending spending by ${(planned - available) / 12:,.0f}/mo or lower the "
                f"savings rate in Tab 2.")
            out.append(("Savings plan (Tab 2)", st,
                        f"Tab 2 assumes ${planned / 12:,.0f}/mo saved as an attending; the budget "
                        f"frees ${available / 12:,.0f}/mo (incl. 403(b)).", fix))

        # Disability insurance: the physician's biggest unprotected asset
        if p.disability_insurance:
            out.append(("Income protection", "On track", "Own-occupation disability insurance in place.", ""))
        else:
            out.append(("Income protection", "At risk",
                        "No own-occupation disability insurance: a career-ending injury would "
                        "erase most of this client's wealth (see Tab 1 human capital).",
                        "Get quotes during training, when premiums are lowest."))
        return out

    @render.ui
    def goals():
        colors = {"On track": "success", "Behind": "warning", "At risk": "danger"}
        cards = [ui.div(ui.h6(title), ui.span(st, class_=f"badge bg-{colors[st]} mb-2"),
                        ui.p(detail, class_="small mb-1"),
                        ui.p(ui.tags.i(fix), class_="small text-muted") if fix else None,
                        class_="p-2")
                 for title, st, detail, fix in goal_list()]
        return ui.layout_columns(*cards, col_widths=[4] * len(cards))

    # Share headline numbers with the client report (write-only, so no loops)
    @reactive.effect
    def _publish():
        p, c = profile(), cf()
        name, plan = chosen()
        new = {"take_home_month": c["take_home"] / 12, "leftover_month": c["leftover"] / 12,
               "tax_rate": (c["federal"] + c["fica"] + c["state"]) / c["gross"] if c["gross"] else 0,
               "view": input.view(), "loan_plan": name,
               "best_plan": min(loans(), key=lambda k: loans()[k]["total"]), "debt_free_age": p.age + plan["years"],
               "loan_total": plan["total"], "forgiven": plan["forgiven"],
               "goals": goal_list()}
        with reactive.isolate():
            summary.set({**summary(), "cash": new})
