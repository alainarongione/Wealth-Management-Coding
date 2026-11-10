import json
from dataclasses import dataclass, asdict
from pathlib import Path

PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles"
PROFILE_DIR.mkdir(exist_ok=True)


@dataclass
class ClientProfile:
    name: str = "Dr. Maya Chen"
    age: int = 31
    state: str = "PA"
    specialty: str = "Internal Medicine"
    career_stage: str = "Resident"
    training_years_left: int = 1
    current_income: float = 68000
    expected_attending_income: float = 300000
    spouse_income: float = 55000
    savings: float = 8000
    retirement_accounts: float = 0
    student_loans: float = 240000
    monthly_expenses: float = 4500
    target_retire_age: int = 60


def _file_for(name: str) -> Path:
    safe = "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    return PROFILE_DIR / f"{safe or 'client'}.json"


def list_profiles() -> list[str]:
    return sorted(p.stem for p in PROFILE_DIR.glob("*.json"))


def save_profile(p: ClientProfile) -> None:
    _file_for(p.name).write_text(json.dumps(asdict(p), indent=2))


def load_profile(stem: str) -> ClientProfile:
    return ClientProfile(**json.loads((PROFILE_DIR / f"{stem}.json").read_text()))


def delete_profile(stem: str) -> None:
    (PROFILE_DIR / f"{stem}.json").unlink(missing_ok=True)