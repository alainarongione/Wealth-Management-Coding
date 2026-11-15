"""Downloadable client report: one page that pulls the key result from every tab."""
import datetime as dt
import html

from shiny import module, ui, render, reactive

from core import benchmarks as B
from core import risk as R

CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:860px;
margin:24px auto;color:#1f2937;line-height:1.45;padding:0 16px}
h1{margin-bottom:0}h2{border-bottom:2px solid #e5e7eb;padding-bottom:4px;margin-top:28px}
.sub{color:#6b7280;margin-top:4px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.kpi{border:1px solid #e5e7eb;border-radius:8px;padding:10px}.kpi b{display:block;font-size:20px}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #e5e7eb;padding:6px;
text-align:left;font-size:14px}.ok{color:#15803d}.warn{color:#b45309}.bad{color:#b91c1c}
.disc{font-size:12px;color:#6b7280;border-top:1px solid #e5e7eb;margin-top:30px;padding-top:8px}
@media print{body{margin:0}}
"""


def money(x):
    return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"


def build_report(p, results, summary):
    e = html.escape
    rec = R.recommended_equity(p)
    hc = R.human_capital(p)
    scf_pct, group, _ = B.scf_percentile(p.age, p.net_worth)
    doc_pct = B.physician_networth_percentile(p.net_worth, p.sex)
    plan_age = B.planning_age(p.age, p.sex)
    cash = summary.get("cash", {})
    events = summary.get("events", {})
    loc = summary.get("location", {})

    def kpi(label, value):
        return f"<div class='kpi'>{e(label)}<b>{e(value)}</b></div>"

    actions = []
    if not p.disability_insurance:
        actions.append("Buy own-occupation disability insurance now; future paychecks "
                       f"({money(hc)}) are the largest asset and are unprotected.")
    if p.monthly_expenses > 0 and p.savings < 3 * p.monthly_expenses:
        actions.append("Build the emergency fund to at least 3-6 months of spending.")
    if cash.get("best_plan") and p.student_loans > 0:
        if cash["best_plan"] == cash["loan_plan"]:
            actions.append(f"Student loans: stay on '{cash['loan_plan']}', the cheapest option "
                           f"(debt-free by age {cash['debt_free_age']}).")
        else:
            actions.append(f"Student loans: switch from '{cash['loan_plan']}' to "
                           f"'{cash['best_plan']}', the cheapest option.")
    actions.append(f"Invest {rec['equity']}% stocks / {100 - rec['equity']}% bonds today in "
                   f"low-cost index funds, getting safer each year on the glide path.")
    if loc.get("break_even"):
        actions.append(f"Only buy a home if staying at least {loc['break_even']} years "
                       f"(physician mortgage break-even).")
    if "prob" in results and results["prob"] < 0.8:
        actions.append("Raise the attending savings rate or retire a little later to push the "
                       "retirement odds above 80%.")

    goal_rows = "".join(
        f"<tr><td>{e(t)}</td><td class='{ {'On track': 'ok', 'Behind': 'warn'}.get(s, 'bad') }'>"
        f"{e(s)}</td><td>{e(d)}</td></tr>" for t, s, d, _ in cash.get("goals", []))

    port = ""
    if "prob" in results:
        prob_txt = f"{results['prob']:.0%}"
        port = (f"<div class='grid'>{kpi('Chance of reaching retirement goal', prob_txt)}"
                f"{kpi('Typical portfolio at retirement', money(results['median']))}"
                f"{kpi('Unlucky case (1 in 10)', money(results['p10']))}</div>"
                f"<p>Goal: {money(results['goal'])} (25 x {money(results['ret_spend'])}/yr spending). "
                f"Savings rate {results['save_train']:.0%} in training, {results['save_att']:.0%} "
                f"as an attending. Fee: {e(results['fee_label'])}. {e(results['style'])}.</p>")
    else:
        port = "<p>Open the Portfolio tab to run the projection.</p>"

    ev = ""
    if events:
        names = ", ".join(events["events"]) or "none selected"
        ev = (f"<p>Events modeled: {e(names)}. Chance of reaching the goal moves from "
              f"{events['base_prob']:.0%} to <b>{events['events_prob']:.0%}</b>.</p>")

    loc_html = ""
    if loc:
        loc_html = (f"<p>{e(B.STATES.get(p.state, p.state))} ranks #{loc['rank']} of 51 for this "
                    f"household's after-tax, cost-of-living-adjusted pay "
                    f"({money(loc['real_take_home'])}/yr). Best: {e(loc['best_state'])}.</p>")

    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>MD Wealth plan: {e(p.name)}</title><style>{CSS}</style></head><body>
<h1>MD Wealth plan for {e(p.name)}</h1>
<p class='sub'>{e(p.specialty)} · {e(p.career_stage)} · age {p.age} · {e(B.STATES.get(p.state, p.state))}
 · prepared {dt.date.today():%B %d, %Y}</p>

<h2>1. Where you stand</h2>
<div class='grid'>{kpi('Net worth', money(p.net_worth))}
{kpi('Human capital (future pay)', money(hc))}
{kpi('Years to retirement', str(max(0, p.target_retire_age - p.age)))}
{kpi(f'Percentile vs. U.S. households {group}', B.ordinal(scf_pct))}
{kpi('Percentile vs. practicing physicians', B.ordinal(doc_pct))}
{kpi('Plan for money to last to', f'age {plan_age}')}</div>
<p>Risk tolerance {rec['tolerance']}/100, risk capacity {rec['capacity']}/100.
{e(R.mismatch_message(rec['tolerance'], rec['capacity']))}</p>

<h2>2. Recommended portfolio</h2>
<p><b>{rec['equity']}% stocks / {100 - rec['equity']}% bonds</b> today. Built from the age rule
({rec['base']:.0f}), risk tolerance ({rec['tol_adj']:+.0f}) and bond-like human capital
({rec['hc_adj']:+.0f}){', capped by risk capacity' if rec['capped'] else ''}.</p>
{port}

<h2>3. Life events</h2>{ev or '<p>Open the Life Events tab to test events.</p>'}

<h2>4. Cash flow and goals</h2>
<p>Take-home pay {money(cash.get('take_home_month', 0))}/month ({e(cash.get('view', ''))}),
total tax rate {cash.get('tax_rate', 0):.0%}, left to save {money(cash.get('leftover_month', 0))}/month.</p>
<table><tr><th>Goal</th><th>Status</th><th>Detail</th></tr>{goal_rows}</table>

<h2>5. Where to practice and home</h2>{loc_html or '<p>Open the Location tab.</p>'}

<h2>Next steps</h2><ol>{''.join(f'<li>{e(a)}</li>' for a in actions)}</ol>

<p class='disc'>Educational tool only. Not financial, tax, legal or investment advice. Projections use
historical data (CRSP via WRDS, Fama-French, FRED) and simplified 2026 tax rules; actual results will
differ. Consult a licensed professional before acting.</p>
</body></html>"""


@module.ui
def report_ui():
    return ui.div(
        ui.layout_columns(
            ui.p("A one-page summary of every tab, ready to send to the client. Download it, "
                 "open it in a browser, and print to PDF if needed."),
            ui.download_button("download", "Download client report (HTML)", class_="btn-primary"),
            col_widths=[8, 4],
        ),
        ui.card(ui.output_ui("preview")),
        class_="p-3",
    )


@module.server
def report_server(input, output, session, profile, results, summary):

    @reactive.calc
    def doc():
        return build_report(profile(), results(), summary())

    @render.ui
    def preview():
        return ui.tags.iframe(srcdoc=doc(), style="width:100%;height:900px;border:0")

    @render.download(filename=lambda: f"MD_Wealth_{profile().name.replace(' ', '_')}.html")
    def download():
        yield doc()
