import numpy as np
import pandas as pd
import plotly.graph_objects as go
from shiny import module, ui, render, reactive
from shinywidgets import output_widget, render_plotly

from core.market_data import load_returns
from core.portfolio_math import (backtest, stats, yearly_contributions, simulate,
                                 cash_real, in_vs_out_of_sample)
from core import risk as R

RETS = load_returns()
FIRST, LAST = RETS.index[0].year + 1, RETS.index[-1].year
FEES = {"0.0005": "0.05% (index fund)", "0.003": "0.30% (robo-advisor)",
        "0.01": "1.00% (typical advisor)"}


@module.ui
def portfolio_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Your mix"),
            ui.output_ui("rec_text"),
            ui.input_slider("equity", "Stocks today (%)", 0, 100, 80, step=5),
            ui.input_radio_buttons("style", "Over time", ["Glide path (safer with age)",
                                                          "Fixed mix"]),
            ui.input_select("fee", "Annual fee", FEES),
            ui.input_select("rebalance", "Rebalancing", ["Annual", "Monthly", "Never"]),
            ui.input_slider("period", "Historical period", FIRST, LAST, [FIRST, LAST], sep=""),
            ui.hr(),
            ui.h5("Projection"),
            ui.input_slider("save_train", "Savings rate in training (% of gross pay)", 0, 30, 5),
            ui.input_slider("save_att", "Savings rate as attending (% of gross pay)", 0, 50, 20),
            ui.input_numeric("ret_spend", "Retirement spending ($/yr, today's dollars)",
                             150000, step=10000),
            width=330,
        ),
        ui.layout_columns(
            ui.value_box("Your mix", ui.output_text("mix_box")),
            ui.value_box("Real return per year (history)", ui.output_text("cagr_box")),
            ui.value_box("Worst 12 months (history)", ui.output_text("worst_box")),
            ui.value_box("Chance of reaching retirement goal", ui.output_text("prob_box")),
        ),
        ui.layout_columns(
            ui.card(ui.card_header("Why this mix? From profile to portfolio"),
                    output_widget("why_plot"), ui.output_ui("why_text")),
            ui.card(ui.card_header("Glide path: stock share at each age"),
                    output_widget("glide_plot"), ui.output_ui("glide_text")),
            col_widths=[6, 6],
        ),
        ui.card(
            ui.card_header("Backtest: what $10,000 would have grown to (after inflation and fees)"),
            output_widget("bt_plot"),
            ui.output_table("bt_table"),
        ),
        ui.card(
            ui.card_header("Honesty check: does a mix that looked best in the past keep winning? "
                           "(in-sample vs. out-of-sample)"),
            ui.output_table("oos_table"), ui.output_ui("oos_note"),
        ),
        ui.card(
            ui.card_header("Projection: 2,000 possible futures"),
            output_widget("fan_plot"),
            ui.output_text("fan_note"),
            output_widget("hist_plot"),
        ),
        ui.p("Sources: CRSP value-weighted market return and Fama-French risk-free rate (WRDS); "
             "10-year Treasury yield GS10 and CPI (FRED, Federal Reserve Bank of St. Louis). "
             "Bond returns are estimated from yield changes (duration 7.5). "
             "Sharpe ratio = return above T-bills per unit of risk. Projections resample 12-month "
             "blocks of real history (block bootstrap), so crashes and recoveries stay together. "
             "Past returns do not guarantee future results.",
             class_="text-muted small"),
    )


@module.server
def portfolio_server(input, output, session, profile, results):

    @reactive.calc
    def rec():
        return R.recommended_equity(profile())

    # When the client profile changes, move the slider to the recommended mix
    @reactive.effect
    def _set_recommended():
        ui.update_slider("equity", value=rec()["equity"])

    @reactive.calc
    def contributions():
        p = profile()
        years = max(1, p.target_retire_age - p.age)
        return yearly_contributions(p, years, input.save_train() / 100, input.save_att() / 100)

    @reactive.calc
    def weights():
        """Stock weight for every year until retirement (in %)."""
        p = profile()
        years = max(1, p.target_retire_age - p.age)
        if input.style() == "Fixed mix":
            return np.full(years, float(input.equity()))
        path = R.glide_path(p, contributions())
        # shift the whole path if the user moved the slider away from the recommendation
        return np.clip(path + (input.equity() - path[0]), 0, 100)

    @reactive.calc
    def history():
        start, end = input.period()
        years = RETS.index.year
        return RETS[(years >= start) & (years <= end)]

    @reactive.calc
    def curves():
        r, fee, rb, e = history(), float(input.fee()), input.rebalance(), input.equity()
        return {
            f"Your mix ({e}/{100 - e})": backtest(r, e / 100, fee, rb),
            "60/40 benchmark": backtest(r, 0.60, fee, rb),
            "100% stocks": backtest(r, 1.00, fee, rb),
        }

    @reactive.calc
    def sim():
        p = profile()
        years = max(1, p.target_retire_age - p.age)
        contrib = contributions()
        start = max(0.0, p.savings + p.retirement_accounts)
        wealth = simulate(history(), weights() / 100, float(input.fee()),
                          start, contrib, years)
        goal = (input.ret_spend() or 0) * 25  # 4% rule: need 25x yearly spending
        return wealth, goal, years

    @render.ui
    def rec_text():
        p, r = profile(), rec()
        return ui.p(
            ui.HTML(f"Recommended for {p.name}: <b>{r['equity']}% stocks</b> today, "
                    "getting safer each year (see the glide path). Move the slider to try "
                    "other mixes."),
            class_="small",
        )

    @render_plotly
    def why_plot():
        r = rec()
        steps = [("Age rule (110 - age)", r["base"]), ("Risk tolerance", r["tol_adj"]),
                 ("Human capital", r["hc_adj"])]
        measures = ["absolute", "relative", "relative"]
        if r["capped"]:
            steps.append(("Capped by risk capacity", r["ceiling"] - r["raw"]))
            measures.append("relative")
        steps.append(("Recommended (rounded)", r["equity"]))
        measures.append("total")
        fig = go.Figure(go.Waterfall(
            x=[s[0] for s in steps], y=[s[1] for s in steps], measure=measures,
            text=[f"{s[1]:+.0f}" if m == "relative" else f"{s[1]:.0f}%"
                  for s, m in zip(steps, measures)],
            decreasing=dict(marker=dict(color="#dc2626")),
            increasing=dict(marker=dict(color="#16a34a")),
            totals=dict(marker=dict(color="#2563eb"))))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                          yaxis_title="% in stocks", showlegend=False)
        return fig

    @render.ui
    def why_text():
        r = rec()
        cap = (f" The total ({r['raw']:.0f}%) was cut to {r['ceiling']:.0f}% because risk capacity "
               f"is {r['capacity']}/100: losses would hurt more than the client's comfort "
               f"suggests." if r["capped"] else " Risk capacity did not bind.")
        return ui.p(f"Tolerance {r['tolerance']}/100 moves the mix by {r['tol_adj']:+.0f} points. "
                    f"Human capital is {r['hc_share']:.0%} of total wealth and bond-like, adding "
                    f"{r['hc_adj']:+.0f}.{cap}", class_="small")

    @render_plotly
    def glide_plot():
        p = profile()
        w = weights()
        ages = p.age + np.arange(len(w))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ages, y=w, stackgroup="m", name="Stocks",
                                 line=dict(color="#2563eb")))
        fig.add_trace(go.Scatter(x=ages, y=100 - w, stackgroup="m", name="Bonds",
                                 line=dict(color="#94a3b8")))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Age",
                          yaxis=dict(title="% of portfolio", range=[0, 100]),
                          legend=dict(orientation="h", y=-0.25))
        return fig

    @render.ui
    def glide_text():
        w = weights()
        if input.style() == "Fixed mix":
            return ui.p(f"Fixed mix: {w[0]:.0f}% stocks every year.", class_="small")
        return ui.p(f"Stocks fall from {w[0]:.0f}% now to {w[-1]:.0f}% at retirement as future "
                    f"paychecks are used up and savings grow, so there's less time to recover "
                    f"from a crash.", class_="small")

    @reactive.calc
    def oos():
        return in_vs_out_of_sample(history(), input.equity() / 100, float(input.fee()),
                                   input.rebalance())

    @render.table
    def oos_table():
        return oos()[0]

    @render.ui
    def oos_note():
        _, best, split = oos()
        return ui.p(f"We picked the mix with the best Sharpe ratio using only data up to {split} "
                    f"({best:.0%} stocks), then tested it on years it had never seen. If it no "
                    f"longer wins, the 'optimal' mix was partly luck. That's why this app uses a "
                    f"simple, explainable rule instead of an optimizer fit to the past.",
                    class_="small")

    @render.text
    def mix_box():
        e = input.equity()
        return f"{e}% stocks / {100 - e}% bonds"

    @render.text
    def cagr_box():
        return f"{stats(list(curves().values())[0])['cagr']:.1%}"

    @render.text
    def worst_box():
        return f"{stats(list(curves().values())[0])['worst12']:.1%}"

    @render.text
    def prob_box():
        wealth, goal, _ = sim()
        return f"{(wealth[:, -1] >= goal).mean():.0%}"

    @render_plotly
    def bt_plot():
        fig = go.Figure()
        for name, v in curves().items():
                        fig.add_trace(go.Scatter(x=v.index.strftime("%Y-%m-%d"), y=10000 * v.to_numpy(), name=name, mode="lines"))
        fig.update_layout(yaxis_type="log", yaxis_title="Value ($, today's dollars)",
                          height=380, margin=dict(l=10, r=10, t=10, b=10),
                          legend=dict(orientation="h", y=-0.15))
        return fig

    @render.table
    def bt_table():
        rows = []
        cr = cash_real(history())
        for name, v in curves().items():
            s = stats(v, cr)
            rows.append({"Portfolio": name,
                         "Real return / yr": f"{s['cagr']:.1%}",
                         "Volatility": f"{s['vol']:.1%}",
                         "Sharpe ratio": f"{s['sharpe']:.2f}",
                         "Worst 12 months": f"{s['worst12']:.1%}",
                         "Biggest drop (peak to bottom)": f"{s['maxdd']:.1%}"})
        return pd.DataFrame(rows)

    @render_plotly
    def fan_plot():
        wealth, goal, years = sim()
        ages = profile().age + np.arange(years + 1)
        q = np.percentile(wealth, [10, 25, 50, 75, 90], axis=0)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ages, y=q[4], line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=ages, y=q[0], fill="tonexty", line=dict(width=0),
                                 fillcolor="rgba(37,99,235,0.15)",
                                 name="Unlucky to lucky (10th-90th percentile)"))
        fig.add_trace(go.Scatter(x=ages, y=q[3], line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=ages, y=q[1], fill="tonexty", line=dict(width=0),
                                 fillcolor="rgba(37,99,235,0.35)",
                                 name="Middle half (25th-75th)"))
        fig.add_trace(go.Scatter(x=ages, y=q[2], line=dict(color="rgb(37,99,235)", width=3),
                                 name="Typical (median)"))
        fig.add_hline(y=goal, line_dash="dash", line_color="green",
                      annotation_text=f"Retirement goal ${goal / 1e6:.1f}M")
        fig.update_layout(xaxis_title="Age", yaxis_title="Portfolio ($, today's dollars)",
                          height=380, margin=dict(l=10, r=10, t=10, b=10),
                          legend=dict(orientation="h", y=-0.2))
        return fig

    @render.text
    def fan_note():
        wealth, goal, _ = sim()
        p = profile()
        final = wealth[:, -1]
        return (f"At age {p.target_retire_age}: typical outcome ${np.median(final):,.0f}; "
                f"unlucky outcome (1 in 10) ${np.percentile(final, 10):,.0f}. "
                f"Goal = 25 x yearly retirement spending (the 4% rule). "
                f"Contributions are the savings rates above times gross pay; Tab 4 checks whether "
                f"the monthly budget can actually support them after loans and taxes.")

    @render_plotly
    def hist_plot():
        wealth, goal, _ = sim()
        final = wealth[:, -1] / 1e6
        cap = np.percentile(final, 98)
        fig = go.Figure(go.Histogram(x=np.minimum(final, cap), nbinsx=40,
                                     marker_color="#93c5fd", name="Outcomes"))
        fig.add_vline(x=goal / 1e6, line_color="green", line_dash="dash",
                      annotation_text="Goal")
        fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis_title="Portfolio at retirement ($M, today's dollars)",
                          yaxis_title="Number of futures", showlegend=False)
        return fig
                
                
    # Share the projection with the other tabs (Tab 4 goals dashboard)
    @reactive.effect
    def _publish():
        wealth, goal, _ = sim()
        new = {"prob": float((wealth[:, -1] >= goal).mean()), "goal": goal,
               "median": float(np.median(wealth[:, -1])),
               "p10": float(np.percentile(wealth[:, -1], 10)),
               "equity": input.equity() / 100, "weights": weights() / 100,
               "fee": float(input.fee()), "fee_label": FEES[input.fee()],
               "save_train": input.save_train() / 100,
               "save_att": input.save_att() / 100,
               "ret_spend": input.ret_spend() or 0, "style": input.style(),
               "period": tuple(input.period())}
        with reactive.isolate():
            results.set({**results(), **new})