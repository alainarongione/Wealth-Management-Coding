from pathlib import Path

from shiny import App, ui, reactive

from core.theme import LOGO, icon, register_plotly_template
from core.profile_store import ClientProfile
from modules.profile import profile_ui, profile_server
from modules.portfolio import portfolio_ui, portfolio_server
from modules.life_events import events_ui, events_server
from modules.cashflow import cashflow_ui, cashflow_server
from modules.location import location_ui, location_server
from modules.report import report_ui, report_server
from modules.about import about_ui

register_plotly_template()   # one chart style for every figure

DISCLAIMER = ("Educational tool only. Not financial, tax, legal or investment advice. "
              "Projections are estimates based on historical data.")

app_ui = ui.page_navbar(
    ui.nav_panel("Check-up", profile_ui("prof"), icon=icon("stethoscope", 17)),
    ui.nav_panel("Portfolio Rx", portfolio_ui("port"), icon=icon("chart", 17)),
    ui.nav_panel("Stress Test", events_ui("events"), icon=icon("pulse", 17)),
    ui.nav_panel("Cash Flow Vitals", cashflow_ui("cash"), icon=icon("wallet", 17)),
    ui.nav_panel("Where to Practice", location_ui("loc"), icon=icon("map", 17)),
    ui.nav_panel("Client Report", report_ui("report"), icon=icon("file", 17)),
    ui.nav_panel("Sources", about_ui(), icon=icon("info", 17)),
    title=LOGO,
    window_title="MD Wealth · Financial care for physicians",
    header=ui.include_css(Path(__file__).parent / "www" / "styles.css"),
    footer=ui.div(icon("alert", 16), DISCLAIMER, class_="mdw-footer"),
)


def server(input, output, session):
    profile = reactive.value(ClientProfile())   # one shared client profile (Tab 1 writes it)
    results = reactive.value({})                # Tab 2 projection, read by Tabs 3 and 4
    summary = reactive.value({})                # headline results from Tabs 3-5 for the report

    steps = [("stethoscope", "Check-up: who the doctor is and where they stand"),
             ("chart", "Portfolio Rx: the recommended mix and how it could grow"),
             ("pulse", "Stress Test: fellowships, kids, disability, market crashes"),
             ("wallet", "Cash Flow Vitals: every paycheck dollar and every goal"),
             ("map", "Where to Practice: taxes, cost of living and buying a home"),
             ("file", "Client Report: a one-page plan to take home")]
    ui.modal_show(ui.modal(
        ui.div(
            ui.div(icon("heart", 30), class_="mdw-hero-icon"),
            ui.div(
                ui.p("Financial care built for physicians: from residency debt to retirement. "
                     "Start by loading a sample doctor in the Check-up tab."),
                ui.tags.ul(*[ui.tags.li(icon(i, 18), t) for i, t in steps], class_="mdw-steps"),
            ),
            class_="mdw-welcome",
        ),
        ui.div(ui.strong("Disclaimer: "), DISCLAIMER, class_="alert alert-warning mt-3 mb-0"),
        title="Welcome to MD Wealth", easy_close=True, size="l",
        footer=ui.modal_button("Start the check-up", class_="btn-primary"),
    ))

    profile_server("prof", profile=profile)
    portfolio_server("port", profile=profile, results=results)
    events_server("events", profile=profile, results=results, summary=summary)
    cashflow_server("cash", profile=profile, results=results, summary=summary)
    location_server("loc", profile=profile, summary=summary)
    report_server("report", profile=profile, results=results, summary=summary)


app = App(app_ui, server)
