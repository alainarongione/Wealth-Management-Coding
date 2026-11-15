import plotly.graph_objects as go
from shiny import module, ui, render, reactive
from shinywidgets import output_widget, render_plotly

from core.theme import vbox, tab_header, STATUS_STYLE, icon

from core import benchmarks as B
from core import housing as H

RATE_NOW, RATE_DATE = H.latest_mortgage_rate()
METRICS = {
    "Take-home in U.S.-average dollars": "Take-home pay after taxes, adjusted for local prices",
    "State tax": "State income tax at your income",
    "Cost of living (US=100)": "Cost of living (BEA Regional Price Parity)",
}


@module.ui
def location_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Where to practice"),
            ui.input_select("metric", "Color the map by", METRICS),
            ui.p("Uses the attending income, spouse income and filing status from Tab 1.",
                 class_="small text-muted"),
            ui.hr(),
            ui.h5("Rent vs. buy"),
            ui.output_ui("home_defaults"),
            ui.input_numeric("price", "Home price ($)", 450000, step=25000),
            ui.input_numeric("rent", "Comparable rent ($/month)", 2600, step=100),
            ui.input_numeric("rate", f"30-yr mortgage rate (%), FRED {RATE_DATE}",
                             round(RATE_NOW, 2), step=0.125),
            ui.input_slider("years", "Years you'll stay", 2, 30, 7),
            ui.input_slider("growth", "Home price growth (%/yr)", 0.0, 6.0, 3.5, step=0.5),
            ui.input_slider("ret", "Return on invested savings (%/yr)", 2.0, 10.0, 6.0, step=0.5),
            width=320,
        ),
        tab_header('Where to Practice & Home',
                   'Where should this doctor practice, and should they buy a home?',
                   'map', 'Doctors can often choose their city. Taxes and prices make the same salary worth very different amounts.'),
        ui.layout_columns(
            vbox("Your state's rank (of 51)", ui.output_text("rank_box"),
                         ui.output_text("rank_sub")),
            vbox("Best state for your take-home", ui.output_text("best_box"),
                         ui.output_text("best_sub")),
            vbox("Buying beats renting after", ui.output_text("be_box"),
                         ui.output_text("be_sub")),
        ),
        ui.card(ui.card_header("Same paycheck, 51 different results"), output_widget("state_map"),
                ui.output_ui("map_note")),
        ui.layout_columns(
            ui.card(ui.card_header("Top 10 states for your situation"), ui.output_table("top10")),
            ui.card(ui.card_header("Rent vs. buy: physician mortgage vs. conventional loan"),
                    output_widget("rvb_plot"), ui.output_ui("rvb_note")),
            col_widths=[5, 7],
        ),
        ui.card(ui.card_header("30-year mortgage rates since 1971 (FRED MORTGAGE30US)"),
                output_widget("rate_plot")),
        ui.p("Sources: Tax Foundation, State Individual Income Tax Rates and Brackets 2026; BEA "
             "Regional Price Parities by state, 2023; Freddie Mac Primary Mortgage Market Survey "
             "via FRED (MORTGAGE30US); 2026 IRS federal brackets. Physician mortgages typically "
             "allow 0-5% down with no PMI, often at a slightly higher rate (+0.25% assumed). Ignores "
             "local income taxes and the mortgage-interest deduction.",
             class_="text-muted small"),
    )


@module.server
def location_server(input, output, session, profile, summary):

    @reactive.calc
    def table():
        p = profile()
        return H.state_comparison(p.expected_attending_income, p.spouse_income, p.filing_status)

    @render.ui
    def home_defaults():
        p = profile()
        return ui.p(f"For {B.STATES.get(p.state, p.state)} (cost of living "
                    f"{B.rpp(p.state):.0f}% of U.S.).", class_="small text-muted")

    @render.text
    def rank_box():
        t, p = table(), profile()
        return f"#{int(t.loc[t['state'] == p.state, 'Rank'].iloc[0])}"

    @render.text
    def rank_sub():
        t, p = table(), profile()
        row = t[t["state"] == p.state].iloc[0]
        return f"{row['State']}: ${row['Take-home in U.S.-average dollars']:,.0f} real take-home"

    @render.text
    def best_box():
        return table().iloc[0]["State"]

    @render.text
    def best_sub():
        t, p = table(), profile()
        gain = t.iloc[0]["Take-home in U.S.-average dollars"] - \
            t.loc[t["state"] == p.state, "Take-home in U.S.-average dollars"].iloc[0]
        return f"+${gain:,.0f}/yr in buying power vs. your state"

    @render_plotly
    def state_map():
        t = table()
        col = input.metric()
        fig = go.Figure(go.Choropleth(
            locations=t["state"], z=t[col], locationmode="USA-states",
            colorscale="RdYlGn_r" if col != "Take-home in U.S.-average dollars" else "RdYlGn",
            text=t["State"], colorbar=dict(title=""),
            hovertemplate="%{text}: %{z:,.0f}<extra></extra>"))
        p = profile()
        fig.add_trace(go.Scattergeo(
            locations=[p.state], locationmode="USA-states", mode="markers",
            marker=dict(size=14, color="black", symbol="star"), name="You", hoverinfo="skip"))
        fig.update_layout(geo=dict(scope="usa"), height=430, showlegend=False,
                          margin=dict(l=0, r=0, t=10, b=0))
        return fig

    @render.ui
    def map_note():
        t = table()
        hi, lo = t.iloc[0], t.iloc[-1]
        return ui.p(f"The same {profile().specialty.lower()} household keeps "
                    f"${hi['Take-home in U.S.-average dollars']:,.0f} of buying power in "
                    f"{hi['State']} vs. ${lo['Take-home in U.S.-average dollars']:,.0f} in "
                    f"{lo['State']}. Physicians can often choose where to practice, and this gap "
                    f"compounds for 30 years. (Physician pay also varies by region; not modeled.)",
                    class_="small")

    @render.table
    def top10():
        t = table().head(10)
        return t.assign(**{
            "State tax": t["State tax"].map("${:,.0f}".format),
            "Take-home": t["Take-home"].map("${:,.0f}".format),
            "Cost of living (US=100)": t["Cost of living (US=100)"].map("{:.1f}".format),
            "Take-home in U.S.-average dollars":
                t["Take-home in U.S.-average dollars"].map("${:,.0f}".format),
        })[["Rank", "State", "State tax", "Take-home", "Cost of living (US=100)",
            "Take-home in U.S.-average dollars"]]

    @reactive.calc
    def rvb():
        kw = dict(price=input.price() or 0, rent_month=input.rent() or 0, years=input.years(),
                  home_growth=input.growth() / 100, invest_return=input.ret() / 100)
        rate = (input.rate() or 0) / 100
        doc = H.rent_vs_buy(rate=rate + 0.0025, down_pct=0.05, **kw)
        conv = H.rent_vs_buy(rate=rate, down_pct=0.20, **kw)
        return doc, conv

    @render_plotly
    def rvb_plot():
        doc, conv = rvb()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=doc["year"], y=doc["buy_minus_rent"],
                                 name="Physician mortgage (5% down, no PMI)",
                                 line=dict(color="#0e7490", width=3)))
        fig.add_trace(go.Scatter(x=conv["year"], y=conv["buy_minus_rent"],
                                 name="Conventional (20% down)", line=dict(color="#10b981", width=3)))
        fig.add_hline(y=0, line_color="gray", annotation_text="Renting and buying equal")
        fig.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis_title="Years after buying",
                          yaxis_title="Buy minus rent: net worth ($)",
                          legend=dict(orientation="h", y=-0.25))
        return fig

    @render.ui
    def rvb_note():
        doc, conv = rvb()
        price = input.price() or 0
        return ui.p(f"Physician mortgage: ${price * 0.05:,.0f} down, about "
                    f"${doc['first_year_cost'].iloc[0]:,.0f}/mo all-in. Conventional: "
                    f"${price * 0.20:,.0f} down, ${conv['first_year_cost'].iloc[0]:,.0f}/mo. "
                    f"Buying usually loses if you move within a few years (closing and selling "
                    f"costs), which matters for residents who may relocate for fellowship.",
                    class_="small")

    @render.text
    def be_box():
        y = H.break_even_year(rvb()[0])
        return f"{y} years" if y else "Not within stay"

    @render.text
    def be_sub():
        y = H.break_even_year(rvb()[1])
        return f"Conventional loan: {y} years" if y else "Conventional loan: not within stay"

    @render_plotly
    def rate_plot():
        h = H.mortgage_history()
        fig = go.Figure(go.Scatter(x=h["date"].dt.strftime("%Y-%m-%d"), y=h["value"],
                                   line=dict(color="#14b8a6")))
        fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10),
                          yaxis_title="Rate (%)")
        return fig

    @reactive.effect
    def _publish():
        t, p = table(), profile()
        row = t[t["state"] == p.state].iloc[0]
        doc, _ = rvb()
        new = {"rank": int(row["Rank"]), "best_state": t.iloc[0]["State"],
               "real_take_home": float(row["Take-home in U.S.-average dollars"]),
               "break_even": H.break_even_year(doc), "price": input.price() or 0}
        with reactive.isolate():
            summary.set({**summary(), "location": new})
