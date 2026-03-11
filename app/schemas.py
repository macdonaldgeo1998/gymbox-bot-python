from pydantic import BaseModel


class AddTargetRequest(BaseModel):
    date: str
    className: str
    time: str
    clubName: str | None = None


class RunBookingRequest(BaseModel):
    date: str
    className: str
    time: str
    clubName: str | None = None


class SetWeeklyTargetRequest(BaseModel):
    weekday: str
    className: str
    time: str
    location: str