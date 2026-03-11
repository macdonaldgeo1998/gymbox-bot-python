import os
import sys
import time
from datetime import date

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


def run_once(run_date: str | None = None, class_date: str | None = None) -> None:
    service = get_gymbox_service()
    effective_run_date = run_date or date.today().isoformat()

    print("Running scheduled Gymbox bookings...")
    print(f"Run date: {effective_run_date}")

    if class_date:
        print(f"Explicit class date mode: {class_date}")
        targets = service.get_targets_for_class_date(class_date)
        results = service.run_scheduled_bookings_for_class_date(class_date)
    else:
        print("Run-date mode")
        targets = service.get_targets_for_run_date(effective_run_date)
        results = service.run_scheduled_bookings(run_date=effective_run_date)

    print("Targets:", [t.to_dict() for t in targets])
    print(f"Results count: {len(results)}")

    if not results:
        print("No booking targets for this run.")
        return

    for result in results:
        print(result)


if __name__ == "__main__":
    # If supplied, treat first CLI arg as explicit class date, e.g.
    # python -m app.worker 2026-03-12
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