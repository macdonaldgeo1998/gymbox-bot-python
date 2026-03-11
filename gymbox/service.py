from datetime import date as dt_date

from gymbox.booking_logic import (
    find_matching_class,
    make_booking_key,
    pick_targets_for_day,
    weekly_targets_for_class_date,
    weekly_targets_to_run_targets,
)
from gymbox.client import GymboxBrowserClient
from gymbox.exceptions import NoMatchingClassError
from gymbox.models import BookingResult, ClassTarget
from gymbox.storage import load_targets, load_weekly_targets, record_booking_attempt


class GymboxService:
    def __init__(
        self,
        email: str,
        password: str,
        default_club: str,
        headless: bool = True,
        slow_mo: int = 0,
        classes_path: str = "data/classes.json",
        classes_by_day_path: str = "data/classes_by_day.json",
        booking_history_path: str = "data/booking_history.json",
    ):
        self.email = email
        self.password = password
        self.default_club = default_club
        self.headless = headless
        self.slow_mo = slow_mo
        self.classes_path = classes_path
        self.classes_by_day_path = classes_by_day_path
        self.booking_history_path = booking_history_path

    def _client(self) -> GymboxBrowserClient:
        return GymboxBrowserClient(
            email=self.email,
            password=self.password,
            default_club=self.default_club,
            headless=self.headless,
            slow_mo=self.slow_mo,
        )

    def fetch_timetable(self, club_name: str | None = None, date: str | None = None):
        with self._client() as client:
            client.login()
            return client.fetch_timetable(club_name=club_name, date=date)

    def book_target(self, target: ClassTarget) -> BookingResult:
        effective_club = target.club_name or self.default_club

        with self._client() as client:
            client.login()
            classes = client.fetch_timetable(club_name=effective_club, date=target.date)
            match = find_matching_class(
                classes=classes,
                class_name=target.class_name,
                time=target.time,
                club_name=effective_club,
            )

            if not match:
                raise NoMatchingClassError(
                    f"No matching class found for {target.class_name} at {target.time} on {target.date} in {effective_club}"
                )

            booked = client.book_class(match)
            result = BookingResult(
                booked=booked,
                reason=None if booked else "Booking attempt returned false",
                matched_class={
                    "name": match.name,
                    "time": match.time,
                    "date": match.date,
                    "location": match.location,
                    "raw_text": match.raw_text,
                },
                target=target.to_dict(),
            )

            record_booking_attempt(
                self.booking_history_path,
                make_booking_key(target),
                result.to_dict(),
            )

            return result

    def book_matching_class(
        self,
        date: str,
        class_name: str,
        time: str,
        club_name: str | None = None,
    ) -> BookingResult:
        target = ClassTarget(
            date=date,
            class_name=class_name,
            time=time,
            club_name=club_name or self.default_club,
        )
        return self.book_target(target)

    def get_targets_for_class_date(self, class_date: str) -> list[ClassTarget]:
        dated_targets = pick_targets_for_day(load_targets(self.classes_path), class_date)
        weekly_targets = weekly_targets_for_class_date(
            load_weekly_targets(self.classes_by_day_path),
            class_date,
        )
        return dated_targets + weekly_targets

    def run_scheduled_bookings_for_class_date(self, class_date: str) -> list[dict]:
        targets = self.get_targets_for_class_date(class_date)

        results: list[dict] = []
        for target in targets:
            try:
                result = self.book_target(target)
                results.append(result.to_dict())
            except Exception as exc:
                results.append(
                    BookingResult(
                        booked=False,
                        reason=str(exc),
                        matched_class=None,
                        target=target.to_dict(),
                    ).to_dict()
                )

        return results

    def get_targets_for_run_date(self, run_date: str) -> list[ClassTarget]:
        weekly_targets = weekly_targets_to_run_targets(
            load_weekly_targets(self.classes_by_day_path),
            run_date,
        )

        all_dated_targets = load_targets(self.classes_path)
        target_dates = {target.date for target in weekly_targets}

        dated_targets = [
            target for target in all_dated_targets
            if target.date in target_dates
        ]

        return dated_targets + weekly_targets

    def run_scheduled_bookings(self, run_date: str | None = None) -> list[dict]:
        if run_date is None:
            run_date = dt_date.today().isoformat()

        targets = self.get_targets_for_run_date(run_date)

        results: list[dict] = []
        for target in targets:
            try:
                result = self.book_target(target)
                results.append(result.to_dict())
            except Exception as exc:
                results.append(
                    BookingResult(
                        booked=False,
                        reason=str(exc),
                        matched_class=None,
                        target=target.to_dict(),
                    ).to_dict()
                )

        return results