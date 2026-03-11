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