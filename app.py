from shiny import App, ui, reactive
from core.profile_store import ClientProfile
from modules.profile import profile_ui, profile_server
from modules.portfolio import portfolio_ui, portfolio_server
from modules.life_events import events_ui, events_server
from modules.cashflow import cashflow_ui, cashflow_server
from modules.location import location_ui, location_server
from modules.report import report_ui, report_server
from modules.about import about_ui

DISCLAIMER = ("Educational tool only. Not financial, tax, legal or investment advice. "
              "Projections are estimates based on historical data.")

app_ui = ui.page_navbar(
    ui.nav_panel("1 · Client Profile", profile_ui("prof")),
    ui.nav_panel("2 · Portfolio", portfolio_ui("port")),
    ui.nav_panel("3 · Life Events", events_ui("events")),
    ui.nav_panel("4 · Cash Flow & Goals", cashflow_ui("cash")),
    ui.nav_panel("5 · Where to Practice & Home", location_ui("loc")),
    ui.nav_panel("Client Report", report_ui("report")),
    ui.nav_panel("About & Sources", about_ui()),
    title="MD Wealth",
    footer=ui.div(DISCLAIMER, class_="text-center small text-muted py-2 border-top"),
)


def server(input, output, session):
    profile = reactive.value(ClientProfile())   # one shared client profile (Tab 1 writes it)
    results = reactive.value({})                # Tab 2 projection, read by Tabs 3 and 4
    summary = reactive.value({})                # headline results from Tabs 3-5 for the report

    ui.modal_show(ui.modal(
        ui.p("MD Wealth helps physicians plan from training to retirement."),
        ui.p(ui.strong(DISCLAIMER)),
        title="Welcome to MD Wealth", easy_close=True, footer=ui.modal_button("I understand"),
    ))

    profile_server("prof", profile=profile)
    portfolio_server("port", profile=profile, results=results)
    events_server("events", profile=profile, results=results, summary=summary)
    cashflow_server("cash", profile=profile, results=results, summary=summary)
    location_server("loc", profile=profile, summary=summary)
    report_server("report", profile=profile, results=results, summary=summary)


app = App(app_ui, server)
