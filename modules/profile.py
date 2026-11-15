import numpy as np
import plotly.graph_objects as go
from shiny import module, ui, render, reactive
from shinywidgets import output_widget, render_plotly

from core import benchmarks as B
from core import risk as R
from core.cashflow_math import cash_flow
from core.profile_store import (ClientProfile, list_profiles, save_profile,
                                load_profile, delete_profile)

STAGES = ["Medical Student", "Resident", "Fellow", "Attending", "Near Retirement"]
STATUSES = ["Married filing jointly", "Single"]
NUM_FIELDS = ["age", "children", "target_retire_age", "training_years_left", "current_income",
              "expected_attending_income", "spouse_income", "savings", "retirement_accounts",
              "home_equity", "student_loans", "other_debt", "monthly_expenses"]
TEXT_FIELDS = ["name"]
SELECT_FIELDS = ["sex", "state", "filing_status", "specialty", "career_stage", "practice_type"]
BOOL_FIELDS = ["nonprofit", "disability_insurance"]
RISK_FIELDS = [f"risk_q{i}" for i in range(1, 6)]
STATE_CHOICES = {k: f"{v} ({k})" for k, v in sorted(B.STATES.items(), key=lambda kv: kv[1])}


def money(x):
    return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"


@module.ui
def profile_ui():
    d = ClientProfile()
    quiz = [ui.input_radio_buttons(f"risk_q{i + 1}", q,
                                   {str(j + 1): a for j, a in enumerate(answers)},
                                   selected=str(getattr(d, f"risk_q{i + 1}")))
            for i, (q, answers) in enumerate(R.RISK_QUESTIONS)]
    return ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Saved clients"),
            ui.input_select("saved", None, choices=list_profiles()),
            ui.input_action_button("load", "Load", class_="btn-sm"),
            ui.input_action_button("delete", "Delete", class_="btn-sm btn-outline-danger"),
            ui.hr(),
            ui.input_action_button("save", "Save current client", class_="btn-primary"),
            ui.hr(),
            ui.p("Everything entered here flows into every other tab.", class_="small text-muted"),
            width=260,
        ),
        ui.layout_columns(
            ui.value_box("Net worth", ui.output_text("net_worth"), ui.output_text("nw_pct_txt")),
            ui.value_box("Savings rate (after tax)", ui.output_text("savings_rate"),
                         ui.output_text("savings_sub")),
            ui.value_box("Debt / income", ui.output_text("debt_ratio")),
            ui.value_box("Time horizon", ui.output_text("horizon"), ui.output_text("horizon_sub")),
            ui.value_box("Human capital", ui.output_text("hc_box"), ui.output_text("hc_sub")),
            col_widths=[3, 2, 2, 2, 3],
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("Who"),
                ui.input_text("name", "Name", d.name),
                ui.input_numeric("age", "Age", d.age, min=20, max=90),
                ui.input_select("sex", "Sex (for life-expectancy tables)", ["Female", "Male"],
                                selected=d.sex),
                ui.input_select("state", "State where you practice", STATE_CHOICES,
                                selected=d.state),
                ui.input_select("filing_status", "Tax filing status", STATUSES,
                                selected=d.filing_status),
                ui.input_numeric("children", "Children", d.children, min=0),
                ui.input_numeric("target_retire_age", "Target retirement age", d.target_retire_age),
            ),
            ui.card(
                ui.card_header("Career"),
                ui.input_select("specialty", "Specialty", B.specialties(), selected=d.specialty),
                ui.input_select("career_stage", "Career stage", STAGES, selected=d.career_stage),
                ui.input_select("practice_type", "Practice type", R.PRACTICE_TYPES,
                                selected=d.practice_type),
                ui.input_checkbox("nonprofit", "Employer is nonprofit / government (PSLF-eligible)",
                                  d.nonprofit),
                ui.input_checkbox("disability_insurance",
                                  "Has own-occupation disability insurance", d.disability_insurance),
                ui.input_numeric("training_years_left", "Training years left", d.training_years_left,
                                 min=0),
                ui.input_numeric("current_income", "Current income ($/yr)", d.current_income),
                ui.input_numeric("expected_attending_income", "Expected attending income ($/yr)",
                                 d.expected_attending_income),
                ui.input_action_button("use_avg", "Use Medscape average for this specialty",
                                       class_="btn-sm btn-outline-secondary"),
            ),
            ui.card(
                ui.card_header("Money"),
                ui.input_numeric("spouse_income", "Spouse income ($/yr)", d.spouse_income),
                ui.input_numeric("savings", "Cash savings ($)", d.savings),
                ui.input_numeric("retirement_accounts", "Retirement + investment accounts ($)",
                                 d.retirement_accounts),
                ui.input_numeric("home_equity", "Home equity ($)", d.home_equity),
                ui.input_numeric("student_loans", "Student loans ($)", d.student_loans),
                ui.input_numeric("other_debt", "Other debt: car, cards ($)", d.other_debt),
                ui.input_numeric("monthly_expenses", "Monthly spending ($)", d.monthly_expenses),
            ),
            col_widths=[4, 4, 4],
        ),
        ui.card(
            ui.card_header("How you compare: absolute numbers vs. the right peer group"),
            ui.layout_columns(output_widget("peer_plot"), ui.output_ui("peer_text"),
                              col_widths=[7, 5]),
        ),
        ui.card(
            ui.card_header("Risk tolerance (what you can stand) vs. risk capacity "
                           "(what your finances can absorb)"),
            ui.layout_columns(
                ui.div(*quiz),
                ui.div(output_widget("risk_plot"), ui.output_ui("risk_text")),
                col_widths=[5, 7],
            ),
        ),
        ui.layout_columns(
            ui.card(ui.card_header("Lifetime balance sheet: human capital becomes financial wealth"),
                    output_widget("hc_plot"), ui.output_ui("hc_text")),
            ui.card(ui.card_header("How long the money must last (SSA life table)"),
                    output_widget("life_plot"), ui.output_ui("life_text")),
            col_widths=[7, 5],
        ),
        ui.p("Sources: Federal Reserve 2025 Survey of Consumer Finances (net worth by age); "
             "Medscape Physician Compensation and Wealth & Debt Reports 2026; AAMC Class of 2025 "
             "debt data; SSA 2023 period life table; BEA Regional Price Parities 2023. "
             "Human capital = present value of after-tax earnings x chance of being alive, "
             "discounted at 2% real + an income-risk premium.", class_="text-muted small"),
    )


@module.server
def profile_server(input, output, session, profile):

    @reactive.effect
    def _sync():
        vals = {f: (input[f]() or 0) for f in NUM_FIELDS}
        vals.update({f: input[f]() for f in TEXT_FIELDS + SELECT_FIELDS})
        vals.update({f: bool(input[f]()) for f in BOOL_FIELDS})
        vals.update({f: int(input[f]() or 2) for f in RISK_FIELDS})
        profile.set(ClientProfile(**vals))

    @reactive.effect
    @reactive.event(input.use_avg)
    def _use_avg():
        ui.update_numeric("expected_attending_income", value=B.specialty_pay(input.specialty()))

    @reactive.effect
    @reactive.event(input.save)
    def _save():
        save_profile(profile())
        ui.update_select("saved", choices=list_profiles())
        ui.notification_show(f"Saved {profile().name}")

    @reactive.effect
    @reactive.event(input.load)
    def _load():
        if not input.saved():
            return
        p = load_profile(input.saved())
        ui.update_text("name", value=p.name)
        for f in SELECT_FIELDS:
            ui.update_select(f, selected=getattr(p, f))
        for f in NUM_FIELDS:
            ui.update_numeric(f, value=getattr(p, f))
        for f in BOOL_FIELDS:
            ui.update_checkbox(f, value=getattr(p, f))
        for f in RISK_FIELDS:
            ui.update_radio_buttons(f, selected=str(getattr(p, f)))
        ui.notification_show(f"Loaded {p.name}")

    @reactive.effect
    @reactive.event(input.delete)
    def _delete():
        if not input.saved():
            return
        delete_profile(input.saved())
        ui.update_select("saved", choices=list_profiles())
        ui.notification_show("Deleted")

    @reactive.calc
    def hc():
        return R.human_capital(profile())

    @reactive.calc
    def peers():
        p = profile()
        scf_pct, group, row = B.scf_percentile(p.age, p.net_worth)
        doc_pct = B.physician_networth_percentile(p.net_worth, p.sex)
        return scf_pct, group, row, doc_pct

    # ----- headline numbers -----
    @render.text
    def net_worth():
        return money(profile().net_worth)

    @render.text
    def nw_pct_txt():
        scf_pct, group, _, _ = peers()
        return f"{B.ordinal(scf_pct)} percentile, U.S. households {group}"

    @reactive.calc
    def this_year():
        p = profile()
        return cash_flow(p, 0, 0.0, p.filing_status, p.state, p.monthly_expenses, 0.0)

    @render.text
    def savings_rate():
        c = this_year()
        return f"{c['leftover'] / c['gross']:.0%}" if c["gross"] > 0 else "—"

    @render.text
    def savings_sub():
        c = this_year()
        return f"${c['leftover'] / 12:,.0f}/mo left after taxes and spending"

    @render.text
    def debt_ratio():
        p = profile()
        income = p.household_income
        return f"{(p.student_loans + p.other_debt) / income:.1f}x" if income > 0 else "—"

    @render.text
    def horizon():
        p = profile()
        return f"{max(0, p.target_retire_age - p.age)} yrs to retire"

    @render.text
    def horizon_sub():
        p = profile()
        return f"Plan for money to last to age {B.planning_age(p.age, p.sex)}"

    @render.text
    def hc_box():
        return money(hc())

    @render.text
    def hc_sub():
        p = profile()
        fin = max(0.0, p.savings + p.retirement_accounts)
        total = hc() + fin
        return f"{hc() / total:.0%} of total wealth is future paychecks" if total > 0 else ""

    # ----- peers -----
    @render_plotly
    def peer_plot():
        p = profile()
        scf_pct, group, row, doc_pct = peers()
        pts = [10, 25, 50, 75, 90, 95]
        vals = [row[f"p{x}"] for x in pts]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[f"{x}th" for x in pts], y=vals, name=f"U.S. households {group}",
                             marker_color="#93c5fd",
                             hovertemplate="%{x} percentile: $%{y:,.0f}<extra></extra>"))
        fig.add_hline(y=p.net_worth, line_color="#dc2626", line_width=3,
                      annotation_text=f"{p.name}: {money(p.net_worth)}")
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10),
                          yaxis_title="Net worth ($)", xaxis_title="Percentile (SCF 2025)",
                          title=dict(text=f"Net worth vs. households aged {group}", x=0.01,
                                     font=dict(size=13)))
        return fig

    @render.ui
    def peer_text():
        p = profile()
        scf_pct, group, row, doc_pct = peers()
        avg_pay = B.specialty_pay(p.specialty)
        pay_gap = p.expected_attending_income / avg_pay - 1
        col = B.rpp(p.state)
        real_pay = p.expected_attending_income / (col / 100)
        stage_note = (" Most physicians in that survey are attendings, so trainees naturally "
                      "rank low here; the gap closes fast after training."
                      if p.career_stage in R.TRAINING_STAGES else "")
        items = [
            ui.tags.li(ui.HTML(f"<b>All U.S. households aged {group}</b>: {B.ordinal(scf_pct)} "
                               f"percentile (median {money(row['p50'])}).")),
            ui.tags.li(ui.HTML(f"<b>Practicing physicians</b> ({p.sex.lower()}): about the "
                               f"{B.ordinal(doc_pct)} percentile. 63% of physicians report $1M+.{stage_note}")),
            ui.tags.li(ui.HTML(f"<b>Pay vs. {p.specialty}</b>: expected {money(p.expected_attending_income)} "
                               f"is {abs(pay_gap):.0%} {'above' if pay_gap >= 0 else 'below'} the "
                               f"Medscape 2026 average of {money(avg_pay)}.")),
            ui.tags.li(ui.HTML(f"<b>Cost of living in {B.STATES.get(p.state, p.state)}</b>: prices are "
                               f"{col:.1f}% of the U.S. average, so that pay buys what "
                               f"{money(real_pay)} buys nationally.")),
            ui.tags.li(ui.HTML(f"<b>Student debt</b>: {B.debt_position(p.student_loans)}")),
        ]
        return ui.tags.ul(*items, class_="small")

    # ----- risk -----
    @reactive.calc
    def rec():
        return R.recommended_equity(profile(), hc=hc())

    @render_plotly
    def risk_plot():
        r = rec()
        fig = go.Figure(go.Bar(
            y=["Risk capacity", "Risk tolerance"], x=[r["capacity"], r["tolerance"]],
            orientation="h", marker_color=["#0f766e", "#7c3aed"],
            text=[f"{r['capacity']}/100", f"{r['tolerance']}/100"], textposition="inside"))
        fig.update_layout(height=170, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(range=[0, 100], title="0 = very cautious / fragile, "
                                                           "100 = aggressive / sturdy"))
        return fig

    @render.ui
    def risk_text():
        p, r = profile(), rec()
        _, parts = R.capacity_score(p)
        rows = "".join(f"<tr><td>{k}</td><td>{v:.0f} / 20</td></tr>" for k, v in parts.items())
        return ui.div(
            ui.p(R.mismatch_message(r["tolerance"], r["capacity"]), class_="small"),
            ui.HTML(f"<table class='table table-sm small'><thead><tr><th>Capacity parts</th>"
                    f"<th></th></tr></thead><tbody>{rows}</tbody></table>"),
            ui.p(ui.HTML(f"Recommended mix: <b>{r['equity']}% stocks</b> (details in Tab 2)."),
                 class_="small"),
        )

    # ----- human capital -----
    @render_plotly
    def hc_plot():
        p = profile()
        years = max(1, p.target_retire_age - p.age)
        contrib = [(p.current_income if t < p.training_years_left else p.expected_attending_income)
                   * (0.05 if t < p.training_years_left else 0.20) for t in range(years)]
        ages, fw, h = R.balance_sheet_path(p, contrib)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ages, y=fw, stackgroup="w", name="Financial wealth",
                                 line=dict(color="#2563eb")))
        fig.add_trace(go.Scatter(x=ages, y=h, stackgroup="w", name="Human capital (future pay)",
                                 line=dict(color="#f59e0b")))
        fig.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Age",
                          yaxis_title="Today's dollars", legend=dict(orientation="h", y=-0.25))
        return fig

    @render.ui
    def hc_text():
        p = profile()
        prem, stab = R.INCOME_RISK[p.practice_type]
        return ui.p(
            f"{p.name}'s biggest asset is future paychecks ({money(hc())}). An "
            f"{p.practice_type.split(' (')[0].lower()} physician's pay behaves like a bond "
            f"(stability {stab:.0%}), so the investment account can hold more stocks early. "
            f"Compare: a tenured professor (very bond-like), a startup founder (stock-like, "
            f"so hold fewer stocks) and a 26-year-old athlete (large but short, so save hard now). "
            f"Without disability insurance, this asset is unprotected.",
            class_="small")

    # ----- longevity -----
    @render_plotly
    def life_plot():
        p = profile()
        s = B.survival_curve(p.age, p.sex)
        plan = B.planning_age(p.age, p.sex)
        fig = go.Figure(go.Scatter(x=s.index, y=s.values * 100, line=dict(color="#0f766e", width=3),
                                   hovertemplate="Age %{x}: %{y:.0f}% chance alive<extra></extra>"))
        fig.add_vline(x=p.target_retire_age, line_dash="dot", annotation_text="Retire")
        fig.add_vline(x=plan, line_dash="dash", line_color="#dc2626",
                      annotation_text=f"Plan to {plan}")
        fig.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Age",
                          yaxis_title="Chance still alive (%)")
        return fig

    @render.ui
    def life_text():
        p = profile()
        le = B.life_expectancy(p.age, p.sex)
        plan = B.planning_age(p.age, p.sex)
        yrs = plan - p.target_retire_age
        return ui.p(f"Average life expectancy at {p.age}: {le:.0f}. But 1 in 4 people like "
                    f"{p.name} live past {plan}, so retirement savings must last about {yrs} "
                    f"years, not {max(0, le - p.target_retire_age):.0f}. Physicians tend to "
                    f"outlive the general population, so this is conservative.", class_="small")
