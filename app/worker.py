import os
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from gymbox.booking_logic import make_booking_key
from gymbox.config import load_config
from gymbox.service import GymboxService


def get_gymbox_service() -> GymboxService:
    cfg = load_config()
    return GymboxService(
        email=cfg.email,
        password=cfg.password,
        default_club=cfg.default_club,
        headless=cfg.headless,
        slow_mo=cfg.slow_mo,
        classes_path=cfg.classes_path,
        classes_by_day_path=cfg.classes_by_day_path,
        booking_history_path=cfg.booking_history_path,
    )


def get_booking_timezone() -> ZoneInfo:
    timezone_name = os.environ["BOOKING_TIMEZONE"].strip()
    return ZoneInfo(timezone_name)


def parse_attempt_times() -> list[datetime.time]:
    raw = os.environ["BOOKING_ATTEMPT_TIMES"].strip()

    times = []
    for part in raw.split(","):
        value = part.strip()
        if not value:
            continue
        parsed = datetime.strptime(value, "%H:%M").time()
        times.append(parsed)

    if not times:
        raise RuntimeError("BOOKING_ATTEMPT_TIMES must contain at least one HH:MM value")

    return sorted(times)


def get_initial_targets(
    service: GymboxService,
    run_date: str,
    class_date: str | None,
):
    if class_date:
        print(f"Explicit class date mode: {class_date}")
        return service.get_targets_for_class_date(class_date)

    print("Run-date mode")
    return service.get_targets_for_run_date(run_date)


def sleep_until(target_dt: datetime, tz: ZoneInfo) -> None:
    while True:
        now = datetime.now(tz)
        remaining = (target_dt - now).total_seconds()

        if remaining <= 0:
            return

        sleep_for = min(remaining, 30)
        print(
            f"Waiting until {target_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} "
            f"({int(remaining)}s remaining)..."
        )
        time.sleep(sleep_for)


def run_attempt(
    service: GymboxService,
    remaining_targets: list,
    attempt_label: str,
) -> tuple[list[dict], list]:
    print(f"\n=== {attempt_label} ===")
    print("Targets in this attempt:", [t.to_dict() for t in remaining_targets])

    results = service.run_booking_targets(remaining_targets)

    print(f"Results count: {len(results)}")
    for result in results:
        print(result)

    booked_keys = {
        make_booking_key(target)
        for target, result in zip(remaining_targets, results)
        if result.get("booked") is True
    }

    still_remaining = [
        target for target in remaining_targets
        if make_booking_key(target) not in booked_keys
    ]

    return results, still_remaining


def run_once(run_date: str | None = None, class_date: str | None = None) -> None:
    service = get_gymbox_service()
    effective_run_date = run_date or date.today().isoformat()

    booking_tz = get_booking_timezone()
    attempt_times = parse_attempt_times()

    print("Running scheduled Gymbox bookings...")
    print(f"Run date: {effective_run_date}")
    print(f"Booking timezone: {booking_tz}")
    print(f"Attempt times: {[t.strftime('%H:%M') for t in attempt_times]}")

    all_targets = get_initial_targets(service, effective_run_date, class_date)

    print("Initial targets:", [t.to_dict() for t in all_targets])

    if not all_targets:
        print("No booking targets for this run.")
        return

    remaining_targets = list(all_targets)
    today_in_booking_tz = datetime.now(booking_tz).date()

    for attempt_time in attempt_times:
        attempt_dt = datetime.combine(today_in_booking_tz, attempt_time, tzinfo=booking_tz)
        now = datetime.now(booking_tz)

        if now < attempt_dt:
            sleep_until(attempt_dt, booking_tz)
        else:
            print(
                f"Current time {now.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                f"is already past {attempt_dt.strftime('%H:%M %Z')}; attempting immediately."
            )

        _, remaining_targets = run_attempt(
            service,
            remaining_targets,
            attempt_label=f"Attempt at {attempt_dt.strftime('%H:%M %Z')}",
        )

        if not remaining_targets:
            print("\nAll targets booked successfully before remaining attempts.")
            return

        print(
            "Targets still not booked after this attempt:",
            [t.to_dict() for t in remaining_targets],
        )

    print("\nFinished all scheduled attempt times.")
    print(
        "Unbooked targets after final attempt:",
        [t.to_dict() for t in remaining_targets],
    )


if __name__ == "__main__":
    class_date = sys.argv[1] if len(sys.argv) > 1 else None

    mode = os.environ.get("WORKER_MODE", "once").strip().lower()

    if mode == "loop":
        interval = int(os.environ.get("WORKER_INTERVAL_SECONDS", "300"))
        while True:
            try:
                run_once(class_date=class_date)
            except Exception as exc:
                print(f"Worker run failed: {exc}")
            time.sleep(interval)
    else:
        run_once(class_date=class_date)