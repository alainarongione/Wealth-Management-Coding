import numpy as np
import plotly.graph_objects as go
from shiny import module, ui, render, reactive
from shinywidgets import output_widget, render_plotly

from core.market_data import load_returns
from core.portfolio_math import simulate, recommended_equity
from core.life_events_math import CRASHES, crash_returns, build_plan

RETS = load_returns()
NAMES = {"fellowship": "Fellowship", "house": "Buy a house", "kids": "Children",
         "parttime": "Go part-time", "disability": "Disability", "jobloss": "Job loss",
         "inheritance": "Inheritance"}


def num(id, label, value, step=None):
    return ui.input_numeric(id, label, value, step=step)


@module.ui
def events_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.accordion(
                ui.accordion_panel(
                    "Planned events",
                    ui.input_checkbox("fel_on", "Do a fellowship", False),
                    num("fel_years", "Extra training years", 3),
                    num("fel_pay", "Fellow salary ($/yr)", 80000, 5000),
                    num("fel_income", "Attending income after fellowship ($/yr)", 550000, 10000),
                    ui.hr(),
                    ui.input_checkbox("house_on", "Buy a house", True),
                    num("house_age", "At age", 35),
                    num("house_down", "Down payment + closing ($)", 120000, 10000),
                    ui.hr(),
                    ui.input_checkbox("kids_on", "Have children", True),
                    num("kids_n", "How many", 2),
                    num("kids_age", "Your age at first child", 33),
                    num("kids_cost", "Cost per child per year ($)", 15000, 1000),
                    ui.hr(),
                    ui.input_checkbox("pt_on", "Go part-time later (burnout)", False),
                    num("pt_age", "At age", 55),
                    ui.input_slider("pt_pct", "Keep this % of income", 20, 90, 60, step=10),
                ),
                ui.accordion_panel(
                    "Unplanned events",
                    ui.input_checkbox("dis_on", "Disability (can't practice)", False),
                    num("dis_age", "At age", 45),
                    ui.input_checkbox("dis_ins", "Has own-occupation disability insurance", True),
                    ui.input_slider("dis_pct", "Insurance pays % of income", 40, 70, 60, step=5),
                    ui.hr(),
                    ui.input_checkbox("job_on", "Job loss / contract not renewed", False),
                    num("job_age", "At age", 40),
                    num("job_months", "Months without pay", 6),
                    ui.hr(),
                    ui.input_checkbox("inh_on", "Inheritance", False),
                    num("inh_age", "At age", 50),
                    num("inh_amt", "Amount ($)", 250000, 25000),
                ),
                ui.accordion_panel(
                    "Replay a market crash",
                    ui.input_select("crash", "Historical crash",
                                    ["None"] + list(CRASHES.keys())),
                    num("crash_age", "Crash starts at age", 59),
                ),
                open=["Planned events"],
            ),
            width=340,
        ),
        ui.layout_columns(
            ui.value_box("Chance of reaching goal: original plan", ui.output_text("base_box")),
            ui.value_box("Chance with these events", ui.output_text("event_box")),
            ui.value_box("Change", ui.output_text("change_box")),
            ui.value_box("Typical portfolio at retirement", ui.output_text("median_box")),
        ),
        ui.card(ui.card_header("Original plan vs. plan with life events (today's dollars)"),
                output_widget("fan_plot"), ui.output_text("plan_note")),
        ui.layout_columns(
            ui.card(ui.card_header("What each event does to the odds"), output_widget("impact_plot")),
            ui.card(ui.card_header("Does timing matter? Same crash, different ages"),
                    output_widget("timing_plot"), ui.output_text("timing_note")),
            col_widths=[6, 6],
        ),
        ui.p("Uses the mix, fees, savings rates and retirement spending from Tab 2. Crashes replay "
             "the real month-by-month returns from CRSP (WRDS) and FRED. Children are born two "
             "years apart. Student loan payments are not included here (see Tab 4).",
             class_="text-muted small"),
    )


@module.server
def events_server(input, output, session, profile, results):

    @reactive.calc
    def settings():
        """Investment settings shared from Tab 2 (with sensible defaults)."""
        r, p = results(), profile()
        return {
            "equity": r.get("equity", recommended_equity(p) / 100),
            "fee": r.get("fee", 0.0005),
            "save_train": r.get("save_train", 0.05),
            "save_att": r.get("save_att", 0.20),
            "goal": r.get("goal", 150000 * 25),
        }

    @reactive.calc
    def active_events():
        ev = {}
        if input.fel_on():
            ev["fellowship"] = {"years": input.fel_years() or 0, "pay": input.fel_pay() or 0,
                                "new_income": input.fel_income() or 0}
        if input.house_on():
            ev["house"] = {"age": input.house_age(), "down": input.house_down() or 0}
        if input.kids_on():
            ev["kids"] = {"n": input.kids_n() or 0, "age": input.kids_age(),
                          "cost": input.kids_cost() or 0}
        if input.pt_on():
            ev["parttime"] = {"age": input.pt_age(), "pct": input.pt_pct() / 100}
        if input.dis_on():
            ev["disability"] = {"age": input.dis_age(),
                                "benefit": input.dis_pct() / 100 if input.dis_ins() else 0.0}
        if input.job_on():
            ev["jobloss"] = {"age": input.job_age(), "months": input.job_months() or 0}
        if input.inh_on():
            ev["inheritance"] = {"age": input.inh_age(), "amount": input.inh_amt() or 0}
        return ev

    def run(ev, crash=None):
        """Simulate one scenario. Same random seed every time, so differences
        between scenarios come only from the events."""
        p, s = profile(), settings()
        contrib, income, years = build_plan(p, ev, s["save_train"], s["save_att"])
        start = max(0.0, p.savings + p.retirement_accounts)
        wealth = simulate(RETS, s["equity"], s["fee"], start, contrib, years, forced=crash)
        return wealth, income, years

    def chance(wealth):
        return float((wealth[:, -1] >= settings()["goal"]).mean())

    @reactive.calc
    def crash_forced():
        if input.crash() == "None":
            return None
        s, p = settings(), profile()
        months = ((input.crash_age() or p.age) - p.age) * 12
        return months, crash_returns(RETS, input.crash(), s["equity"], s["fee"])

    @reactive.calc
    def base():
        return run({})

    @reactive.calc
    def scenario():
        return run(active_events(), crash_forced())

    # ----- headline numbers -----
    @render.text
    def base_box():
        return f"{chance(base()[0]):.0%}"

    @render.text
    def event_box():
        return f"{chance(scenario()[0]):.0%}"

    @render.text
    def change_box():
        d = (chance(scenario()[0]) - chance(base()[0])) * 100
        return f"{d:+.0f} points"

    @render.text
    def median_box():
        return f"${np.median(scenario()[0][:, -1]):,.0f}"

    # ----- fan chart -----
    @render_plotly
    def fan_plot():
        (bw, _, years), (sw, _, _) = base(), scenario()
        ages = profile().age + np.arange(years + 1)
        q = np.percentile(sw, [10, 50, 90], axis=0)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ages, y=q[2], line=dict(width=0), showlegend=False,
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=ages, y=q[0], fill="tonexty", line=dict(width=0),
                                 fillcolor="rgba(234,88,12,0.18)",
                                 name="With events: unlucky to lucky (10th-90th)"))
        fig.add_trace(go.Scatter(x=ages, y=q[1], line=dict(color="rgb(234,88,12)", width=3),
                                 name="With events: typical"))
        fig.add_trace(go.Scatter(x=ages, y=np.median(bw, axis=0),
                                 line=dict(color="gray", width=2, dash="dash"),
                                 name="Original plan: typical"))
        goal = settings()["goal"]
        fig.add_hline(y=goal, line_dash="dot", line_color="green",
                      annotation_text=f"Goal ${goal / 1e6:.1f}M")
        if input.crash() != "None":
            fig.add_vline(x=input.crash_age(), line_color="red", line_dash="dot",
                          annotation_text=input.crash())
        fig.update_layout(xaxis_title="Age", yaxis_title="Portfolio ($)", height=400,
                          margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2))
        return fig

    @render.text
    def plan_note():
        ev = active_events()
        if not ev and input.crash() == "None":
            return "No events selected. Tick some events in the sidebar."
        names = [NAMES[k] for k in ev] + ([input.crash()] if input.crash() != "None" else [])
        return "Included: " + ", ".join(names) + "."

    # ----- impact of each event on its own -----
    @render_plotly
    def impact_plot():
        b = chance(base()[0])
        labels, deltas = [], []
        for key, val in active_events().items():
            labels.append(NAMES[key])
            deltas.append((chance(run({key: val})[0]) - b) * 100)
        if crash_forced() is not None:
            labels.append(input.crash())
            deltas.append((chance(run({}, crash_forced())[0]) - b) * 100)
        fig = go.Figure(go.Bar(
            x=deltas, y=labels, orientation="h",
            marker_color=["#16a34a" if d >= 0 else "#dc2626" for d in deltas],
            text=[f"{d:+.0f}" for d in deltas], textposition="outside"))
        fig.update_layout(xaxis_title="Change in chance of reaching goal (percentage points)",
                          height=360, margin=dict(l=10, r=30, t=10, b=10))
        return fig

    # ----- sequence-of-returns risk -----
    @reactive.calc
    def timing():
        p, s = profile(), settings()
        name = input.crash() if input.crash() != "None" else "2008 financial crisis"
        crash = crash_returns(RETS, name, s["equity"], s["fee"])
        last = p.target_retire_age - int(np.ceil(len(crash) / 12))  # whole crash fits
        ages = list(range(p.age + 1, last + 1, 3))
        if last not in ages:
            ages.append(last)
        probs = [chance(run(active_events(), ((a - p.age) * 12, crash))[0]) for a in ages]
        return name, ages, probs

    @render_plotly
    def timing_plot():
        name, ages, probs = timing()
        fig = go.Figure(go.Scatter(x=ages, y=[x * 100 for x in probs], mode="lines+markers",
                                   line=dict(color="#dc2626", width=3), name=name))
        fig.add_hline(y=chance(run(active_events())[0]) * 100,
                      line_dash="dash", line_color="gray", annotation_text="No crash")
        fig.update_layout(xaxis_title=f"Age when the {name} hits",
                          yaxis_title="Chance of reaching goal (%)", height=360,
                          margin=dict(l=10, r=10, t=10, b=10))
        return fig

    @render.text
    def timing_note():
        name, ages, probs = timing()
        return (f"The same {name} costs more the closer it hits to retirement: "
                f"{probs[0]:.0%} if it hits at {ages[0]} vs {probs[-1]:.0%} at {ages[-1]}. "
                f"This is sequence-of-returns risk. Early on, new savings buy stocks cheaply; "
                f"near retirement, the portfolio is biggest and has no time to recover.")