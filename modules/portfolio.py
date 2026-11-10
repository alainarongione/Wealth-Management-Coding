import numpy as np
import pandas as pd
import plotly.graph_objects as go
from shiny import module, ui, render, reactive
from shinywidgets import output_widget, render_plotly

from core.market_data import load_returns
from core.portfolio_math import (recommended_equity, backtest, stats,
                                 yearly_contributions, simulate)

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
            ui.input_slider("equity", "Stocks (%)", 0, 100, 85, step=5),
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
        ui.card(
            ui.card_header("Backtest: what $10,000 would have grown to (after inflation and fees)"),
            output_widget("bt_plot"),
            ui.output_table("bt_table"),
        ),
        ui.card(
            ui.card_header("Projection: 2,000 possible futures"),
            output_widget("fan_plot"),
            ui.output_text("fan_note"),
        ),
        ui.p("Sources: CRSP value-weighted market return and Fama-French risk-free rate (WRDS); "
             "10-year Treasury yield GS10 and CPI (FRED, Federal Reserve Bank of St. Louis). "
             "Bond returns are estimated from yield changes (duration 7.5). "
             "Past returns do not guarantee future results.",
             class_="text-muted small"),
    )


@module.server
def portfolio_server(input, output, session, profile, results):

    # When the client profile changes, move the slider to the recommended mix
    @reactive.effect
    def _set_recommended():
        ui.update_slider("equity", value=recommended_equity(profile()))

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
        contrib = yearly_contributions(p, years, input.save_train() / 100,
                                       input.save_att() / 100)
        start = max(0.0, p.savings + p.retirement_accounts)
        wealth = simulate(history(), input.equity() / 100, float(input.fee()),
                          start, contrib, years)
        goal = (input.ret_spend() or 0) * 25  # 4% rule: need 25x yearly spending
        return wealth, goal, years

    @render.ui
    def rec_text():
        p = profile()
        return ui.p(
            f"Recommended for {p.name}: {recommended_equity(p)}% stocks. "
            "A physician's future paychecks are large and steady, like a big bond, "
            "so the investment account can carry more stocks early in a career. "
            "Move the slider to try other mixes.",
            class_="small",
        )

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
        for name, v in curves().items():
            s = stats(v)
            rows.append({"Portfolio": name,
                         "Real return / yr": f"{s['cagr']:.1%}",
                         "Volatility": f"{s['vol']:.1%}",
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
                f"Student loan payments are not included yet; they are handled in Tab 4.")
                
                
    # Share the projection with the other tabs (Tab 4 goals dashboard)
    @reactive.effect
    def _publish():
        wealth, goal, _ = sim()
        results.set({"prob": float((wealth[:, -1] >= goal).mean()), "goal": goal,
                 "median": float(np.median(wealth[:, -1])),
                 "equity": input.equity() / 100, "fee": float(input.fee()),
                 "save_train": input.save_train() / 100,
                 "save_att": input.save_att() / 100})