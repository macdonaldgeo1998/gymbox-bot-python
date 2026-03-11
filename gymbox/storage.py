import json
from pathlib import Path
from typing import Any

from gymbox.models import ClassTarget, WeeklyClassTarget


def load_json(path: str, default: Any):
    file_path = Path(path)
    if not file_path.exists():
        return default

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_targets(path: str) -> list[ClassTarget]:
    """
    Supports both formats:

    Old format:
    {
      "2026-03-12": {
        "className": "Reppin'",
        "time": "13:15",
        "location": "Elephant & Castle"
      }
    }

    New format:
    [
      {
        "date": "2026-03-12",
        "className": "Reppin'",
        "time": "13:15",
        "clubName": "Gymbox Elephant & Castle"
      }
    ]
    """
    raw = load_json(path, [])
    targets: list[ClassTarget] = []

    if isinstance(raw, list):
        for item in raw:
            club_name = item.get("clubName") or item.get("location") or ""
            if club_name and not club_name.lower().startswith("gymbox "):
                club_name = f"Gymbox {club_name}"

            targets.append(
                ClassTarget(
                    date=item["date"],
                    class_name=item["className"],
                    time=item["time"],
                    club_name=club_name,
                )
            )
        return targets
    

    if isinstance(raw, dict):
        for date, item in raw.items():
            club_name = item.get("clubName") or item.get("location") or ""
            if club_name and not club_name.lower().startswith("gymbox "):
                club_name = f"Gymbox {club_name}"
            targets.append(
                ClassTarget(
                    date=date,
                    class_name=item["className"],
                    time=item["time"],
                    club_name=club_name,
                )
            )
        return targets

    raise ValueError(f"Unsupported classes.json format in {path}")


def save_targets(path: str, targets: list[ClassTarget]) -> None:
    payload = [
        {
            "date": t.date,
            "className": t.class_name,
            "time": t.time,
            "clubName": t.club_name,
        }
        for t in targets
    ]
    save_json(path, payload)


def add_target(path: str, target: ClassTarget) -> None:
    targets = load_targets(path)
    targets.append(target)
    save_targets(path, targets)


def delete_target(
    path: str,
    date: str,
    class_name: str,
    time: str,
    club_name: str,
) -> bool:
    targets = load_targets(path)
    original_len = len(targets)

    filtered = [
        t for t in targets
        if not (
            t.date == date
            and t.class_name == class_name
            and t.time == time
            and t.club_name == club_name
        )
    ]

    save_targets(path, filtered)
    return len(filtered) != original_len


def load_weekly_targets(path: str) -> dict[str, WeeklyClassTarget]:
    raw = load_json(path, {})
    result: dict[str, WeeklyClassTarget] = {}

    for weekday, item in raw.items():
        result[weekday] = WeeklyClassTarget(
            weekday=weekday,
            class_name=item["className"],
            time=item["time"],
            location=item["location"],
        )
    return result


def save_weekly_targets(path: str, targets: dict[str, WeeklyClassTarget]) -> None:
    payload = {
        weekday: {
            "className": target.class_name,
            "time": target.time,
            "location": target.location,
        }
        for weekday, target in targets.items()
    }
    save_json(path, payload)


def set_weekly_target(path: str, target: WeeklyClassTarget) -> None:
    targets = load_weekly_targets(path)
    targets[target.weekday] = target
    save_weekly_targets(path, targets)


def delete_weekly_target(path: str, weekday: str) -> bool:
    targets = load_weekly_targets(path)
    existed = weekday in targets
    if existed:
        del targets[weekday]
        save_weekly_targets(path, targets)
    return existed


def load_booking_history(path: str) -> dict[str, Any]:
    return load_json(path, {})


def record_booking_attempt(path: str, booking_key: str, payload: dict) -> None:
    history = load_booking_history(path)
    history[booking_key] = payload
    save_json(path, history)