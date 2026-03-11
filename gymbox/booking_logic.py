import datetime as dt
from typing import Iterable, Optional

from gymbox.client import GymboxClass
from gymbox.models import ClassTarget, WeeklyClassTarget


WEEKDAY_TO_INDEX = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalize_club_name(value: str) -> str:
    normalized = normalize_text(value)
    if normalized.startswith("gymbox "):
        normalized = normalized[len("gymbox "):]
    return normalized


def find_matching_class(
    classes: Iterable[GymboxClass],
    class_name: str,
    time: str,
    club_name: str | None = None,
) -> Optional[GymboxClass]:
    expected_name = normalize_text(class_name)
    expected_time = time
    expected_club = normalize_club_name(club_name) if club_name else None

    for item in classes:
        if normalize_text(item.name) != expected_name:
            continue
        if item.time != expected_time:
            continue
        if expected_club is not None and normalize_club_name(item.location) != expected_club:
            continue
        return item

    return None


def pick_targets_for_day(targets: list[ClassTarget], day: str) -> list[ClassTarget]:
    return [t for t in targets if t.date == day]


def next_weekday_on_or_after(start_date: dt.date, target_weekday: str) -> dt.date:
    if target_weekday not in WEEKDAY_TO_INDEX:
        raise ValueError(f"Unsupported weekday: {target_weekday}")

    target_index = WEEKDAY_TO_INDEX[target_weekday]
    days_ahead = (target_index - start_date.weekday()) % 7
    return start_date + dt.timedelta(days=days_ahead)


def weekly_target_to_next_dated_target(
    weekly_target: WeeklyClassTarget,
    run_date: str,
) -> ClassTarget:
    start = dt.datetime.strptime(run_date, "%Y-%m-%d").date()
    class_date = next_weekday_on_or_after(start, weekly_target.weekday)

    club_name = weekly_target.location
    if not club_name.lower().startswith("gymbox "):
        club_name = f"Gymbox {club_name}"

    return ClassTarget(
        date=class_date.isoformat(),
        class_name=weekly_target.class_name,
        time=weekly_target.time,
        club_name=club_name,
    )


def weekly_targets_to_run_targets(
    weekly_targets: dict[str, WeeklyClassTarget],
    run_date: str,
) -> list[ClassTarget]:
    return [
        weekly_target_to_next_dated_target(target, run_date)
        for target in weekly_targets.values()
    ]


def weekly_targets_for_class_date(
    weekly_targets: dict[str, WeeklyClassTarget],
    class_date: str,
) -> list[ClassTarget]:
    parsed = dt.datetime.strptime(class_date, "%Y-%m-%d")
    weekday = parsed.strftime("%A")

    target = weekly_targets.get(weekday)
    if not target:
        return []

    club_name = target.location
    if not club_name.lower().startswith("gymbox "):
        club_name = f"Gymbox {club_name}"

    return [
        ClassTarget(
            date=class_date,
            class_name=target.class_name,
            time=target.time,
            club_name=club_name,
        )
    ]


def make_booking_key(target: ClassTarget) -> str:
    return f"{target.date}|{target.club_name}|{target.class_name}|{target.time}"