from shiny import App, ui, reactive
from core.profile_store import ClientProfile
from modules.profile import profile_ui, profile_server
from modules.portfolio import portfolio_ui, portfolio_server
from modules.life_events import events_ui, events_server
from modules.cashflow import cashflow_ui, cashflow_server

app_ui = ui.page_navbar(
    ui.nav_panel("1 · Client Profile", profile_ui("prof")),
    ui.nav_panel("2 · Portfolio", portfolio_ui("port")),
    ui.nav_panel("3 · Life Events", events_ui("events")),
    ui.nav_panel("4 · Cash Flow & Goals", cashflow_ui("cash")),
    title="MD Wealth",
    footer=ui.div("Educational tool only. Not financial advice."),
)


def server(input, output, session):
    profile = reactive.value(ClientProfile())   # one shared client profile
    results = reactive.value({})                # results shared between tabs
    profile_server("prof", profile=profile)
    portfolio_server("port", profile=profile, results=results)
    events_server("events", profile=profile, results=results)
    cashflow_server("cash", profile=profile, results=results)


app = App(app_ui, server)