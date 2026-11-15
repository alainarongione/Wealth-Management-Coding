"""The one client profile shared by every tab, plus save / load / delete (JSON files)."""
import json
from dataclasses import dataclass, asdict, fields
from pathlib import Path

PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles"
PROFILE_DIR.mkdir(exist_ok=True)


@dataclass
class ClientProfile:
    # Who
    name: str = "Dr. Maya Chen"
    age: int = 31
    sex: str = "Female"
    state: str = "PA"
    filing_status: str = "Married filing jointly"
    children: int = 0
    target_retire_age: int = 60
    # Career
    specialty: str = "Internal Medicine"
    career_stage: str = "Resident"
    practice_type: str = "Employed (hospital / academic)"
    nonprofit: bool = True               # PSLF-eligible employer
    disability_insurance: bool = False   # own-occupation disability insurance
    training_years_left: int = 1
    current_income: float = 68000
    expected_attending_income: float = 307000
    spouse_income: float = 55000
    # Money
    savings: float = 8000
    retirement_accounts: float = 6000
    home_equity: float = 0
    student_loans: float = 240000
    other_debt: float = 7000
    monthly_expenses: float = 4500
    # Risk tolerance quiz answers (1 = cautious .. 4 = aggressive)
    risk_q1: int = 3
    risk_q2: int = 3
    risk_q3: int = 3
    risk_q4: int = 2
    risk_q5: int = 3

    def risk_answers(self):
        return [self.risk_q1, self.risk_q2, self.risk_q3, self.risk_q4, self.risk_q5]

    @property
    def net_worth(self):
        return (self.savings + self.retirement_accounts + self.home_equity
                - self.student_loans - self.other_debt)

    @property
    def household_income(self):
        spouse = self.spouse_income if self.filing_status == "Married filing jointly" else 0
        return self.current_income + spouse


def _file_for(name: str) -> Path:
    safe = "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    return PROFILE_DIR / f"{safe or 'client'}.json"


def list_profiles() -> list[str]:
    return sorted(p.stem for p in PROFILE_DIR.glob("*.json"))


def save_profile(p: ClientProfile) -> None:
    _file_for(p.name).write_text(json.dumps(asdict(p), indent=2))


def load_profile(stem: str) -> ClientProfile:
    """Loads a saved client. Older files missing newer fields get the defaults."""
    raw = json.loads((PROFILE_DIR / f"{stem}.json").read_text())
    known = {f.name for f in fields(ClientProfile)}
    return ClientProfile(**{k: v for k, v in raw.items() if k in known})


def delete_profile(stem: str) -> None:
    (PROFILE_DIR / f"{stem}.json").unlink(missing_ok=True)
