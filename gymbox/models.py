from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class ClassTarget:
    date: str
    class_name: str
    time: str
    club_name: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WeeklyClassTarget:
    weekday: str
    class_name: str
    time: str
    location: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BookingResult:
    booked: bool
    reason: Optional[str] = None
    matched_class: Optional[dict] = None
    target: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)