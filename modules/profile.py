from shiny import module, ui, render, reactive
from core.profile_store import (ClientProfile, list_profiles, save_profile,
                                load_profile, delete_profile)

SPECIALTIES = ["Internal Medicine", "Family Medicine", "Pediatrics", "Emergency Medicine",
               "Anesthesiology", "Cardiology", "Orthopedic Surgery", "General Surgery",
               "Psychiatry", "Radiology"]
STAGES = ["Medical Student", "Resident", "Fellow", "Attending", "Near Retirement"]
NUM_FIELDS = ["age", "training_years_left", "current_income", "expected_attending_income",
              "spouse_income", "savings", "retirement_accounts", "student_loans",
              "monthly_expenses", "target_retire_age"]


@module.ui
def profile_ui():
    d = ClientProfile()
    return ui.layout_sidebar(
        ui.sidebar(
            ui.h5("Saved clients"),
            ui.input_select("saved", None, choices=list_profiles()),
            ui.input_action_button("load", "Load"),
            ui.input_action_button("delete", "Delete"),
            ui.hr(),
            ui.input_action_button("save", "Save current client"),
        ),
        ui.layout_columns(
            ui.value_box("Net worth", ui.output_text("net_worth")),
            ui.value_box("Savings rate", ui.output_text("savings_rate")),
            ui.value_box("Debt / income", ui.output_text("debt_ratio")),
        ),
        ui.layout_columns(
            ui.card(
                ui.card_header("Who"),
                ui.input_text("name", "Name", d.name),
                ui.input_numeric("age", "Age", d.age),
                ui.input_text("state", "State", d.state),
                ui.input_numeric("target_retire_age", "Target retirement age", d.target_retire_age),
            ),
            ui.card(
                ui.card_header("Career"),
                ui.input_select("specialty", "Specialty", SPECIALTIES, selected=d.specialty),
                ui.input_select("career_stage", "Career stage", STAGES, selected=d.career_stage),
                ui.input_numeric("training_years_left", "Training years left", d.training_years_left),
                ui.input_numeric("current_income", "Current income ($)", d.current_income),
                ui.input_numeric("expected_attending_income", "Attending income ($)",
                                 d.expected_attending_income),
            ),
            ui.card(
                ui.card_header("Money"),
                ui.input_numeric("spouse_income", "Spouse income ($)", d.spouse_income),
                ui.input_numeric("savings", "Savings ($)", d.savings),
                ui.input_numeric("retirement_accounts", "Retirement accounts ($)", d.retirement_accounts),
                ui.input_numeric("student_loans", "Student loans ($)", d.student_loans),
                ui.input_numeric("monthly_expenses", "Monthly expenses ($)", d.monthly_expenses),
            ),
        ),
    )


@module.server
def profile_server(input, output, session, profile):

    @reactive.effect
    def _sync():
        nums = {f: (input[f]() or 0) for f in NUM_FIELDS}
        profile.set(ClientProfile(name=input.name(), state=input.state(),
                                  specialty=input.specialty(),
                                  career_stage=input.career_stage(), **nums))

    @reactive.effect
    @reactive.event(input.save)
    def _save():
        save_profile(profile())
        ui.update_select("saved", choices=list_profiles())
        ui.notification_show("Saved")

    @reactive.effect
    @reactive.event(input.load)
    def _load():
        if not input.saved():
            return
        p = load_profile(input.saved())
        ui.update_text("name", value=p.name)
        ui.update_text("state", value=p.state)
        ui.update_select("specialty", selected=p.specialty)
        ui.update_select("career_stage", selected=p.career_stage)
        for f in NUM_FIELDS:
            ui.update_numeric(f, value=getattr(p, f))
        ui.notification_show("Loaded")

    @reactive.effect
    @reactive.event(input.delete)
    def _delete():
        if not input.saved():
            return
        delete_profile(input.saved())
        ui.update_select("saved", choices=list_profiles())
        ui.notification_show("Deleted")

    @render.text
    def net_worth():
        p = profile()
        return f"${p.savings + p.retirement_accounts - p.student_loans:,.0f}"

    @render.text
    def savings_rate():
        p = profile()
        income = p.current_income + p.spouse_income
        return f"{(income - p.monthly_expenses * 12) / income:.0%}" if income > 0 else "—"

    @render.text
    def debt_ratio():
        p = profile()
        income = p.current_income + p.spouse_income
        return f"{p.student_loans / income:.1f}x" if income > 0 else "—"