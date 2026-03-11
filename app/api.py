from fastapi import Depends, FastAPI, HTTPException, Query

from app.deps import get_gymbox_service
from app.schemas import AddTargetRequest, RunBookingRequest, SetWeeklyTargetRequest
from gymbox.config import load_config
from gymbox.exceptions import NoMatchingClassError
from gymbox.models import ClassTarget, WeeklyClassTarget
from gymbox.service import GymboxService
from gymbox.storage import (
    add_target,
    delete_weekly_target,
    load_targets,
    load_weekly_targets,
    set_weekly_target,
)

app = FastAPI(title="Gymbox Bot API")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/table")
def get_table(
    club_name: str | None = Query(default=None),
    date: str | None = Query(default=None),
    service: GymboxService = Depends(get_gymbox_service),
):
    try:
        classes = service.fetch_timetable(club_name=club_name, date=date)
        return [
            {
                "name": c.name,
                "time": c.time,
                "date": c.date,
                "location": c.location,
                "raw_text": c.raw_text,
            }
            for c in classes
        ]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/targets")
def get_targets():
    cfg = load_config()
    return [t.to_dict() for t in load_targets(cfg.classes_path)]


@app.post("/api/targets")
def create_target(payload: AddTargetRequest):
    cfg = load_config()
    target = ClassTarget(
        date=payload.date,
        class_name=payload.className,
        time=payload.time,
        club_name=payload.clubName or cfg.default_club,
    )
    add_target(cfg.classes_path, target)
    return {"ok": True, "target": target.to_dict()}


@app.get("/api/weekly-targets")
def get_weekly_targets():
    cfg = load_config()
    weekly = load_weekly_targets(cfg.classes_by_day_path)
    return {weekday: target.to_dict() for weekday, target in weekly.items()}


@app.post("/api/weekly-targets")
def create_or_update_weekly_target(payload: SetWeeklyTargetRequest):
    cfg = load_config()
    target = WeeklyClassTarget(
        weekday=payload.weekday,
        class_name=payload.className,
        time=payload.time,
        location=payload.location,
    )
    set_weekly_target(cfg.classes_by_day_path, target)
    return {"ok": True, "target": target.to_dict()}


@app.delete("/api/weekly-targets/{weekday}")
def remove_weekly_target(weekday: str):
    cfg = load_config()
    deleted = delete_weekly_target(cfg.classes_by_day_path, weekday)
    if not deleted:
        raise HTTPException(status_code=404, detail="Weekly target not found")
    return {"ok": True}


@app.post("/api/run-booking")
def run_booking(
    payload: RunBookingRequest,
    service: GymboxService = Depends(get_gymbox_service),
):
    try:
        result = service.book_matching_class(
            date=payload.date,
            class_name=payload.className,
            time=payload.time,
            club_name=payload.clubName,
        )
        return result.to_dict()
    except NoMatchingClassError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/run-scheduled")
def run_scheduled(
    date: str | None = None,
    service: GymboxService = Depends(get_gymbox_service),
):
    try:
        return service.run_scheduled_bookings(today=date)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))