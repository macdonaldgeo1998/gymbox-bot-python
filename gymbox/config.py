import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GymboxConfig:
    email: str
    password: str
    default_club: str
    headless: bool
    slow_mo: int
    classes_path: str
    classes_by_day_path: str
    booking_history_path: str


def _parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config() -> GymboxConfig:
    email = os.environ.get("GYMBOX_EMAIL")
    password = os.environ.get("GYMBOX_PASSWORD")
    default_club = os.environ.get("GYMBOX_DEFAULT_CLUB", "Gymbox Elephant & Castle")

    if not email or not password:
        raise RuntimeError("Missing GYMBOX_EMAIL or GYMBOX_PASSWORD")

    return GymboxConfig(
        email=email,
        password=password,
        default_club=default_club,
        headless=_parse_bool(os.environ.get("GYMBOX_HEADLESS"), True),
        slow_mo=int(os.environ.get("GYMBOX_SLOW_MO", "0")),
        classes_path=os.environ.get("CLASSES_PATH", "data/classes.json"),
        classes_by_day_path=os.environ.get("CLASSES_BY_DAY_PATH", "data/classes_by_day.json"),
        booking_history_path=os.environ.get("BOOKING_HISTORY_PATH", "data/booking_history.json"),
    )