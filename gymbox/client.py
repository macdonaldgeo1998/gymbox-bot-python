from dataclasses import dataclass
from typing import List, Optional
import datetime as dt
import re

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PWTimeout,
    Page,
    Locator,
)


@dataclass
class GymboxClass:
    name: str
    time: str          # HH:mm
    date: str          # YYYY-MM-DD
    location: str
    raw_text: str


class GymboxBrowserClient:
    def __init__(
        self,
        email: str,
        password: str,
        base_url: str = "https://my.gymbox.com",
        headless: bool = True,
        slow_mo: int = 0,
        default_club: str = "Gymbox Elephant & Castle",
    ):
        self.email = email
        self.password = password
        self.base_url = base_url.rstrip("/")
        self.headless = headless
        self.slow_mo = slow_mo
        self.default_club = default_club

        self.logged_in = False
        self._p = None
        self._browser = None
        self._ctx = None
        self._page: Optional[Page] = None

    def __enter__(self):
        self._p = sync_playwright().start()
        self._browser = self._p.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
        )
        self._ctx = self._browser.new_context()
        self._page = self._ctx.new_page()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._ctx:
            self._ctx.close()
        if self._browser:
            self._browser.close()
        if self._p:
            self._p.stop()

    @staticmethod
    def _to_24h(t12: str) -> str:
        cleaned = re.sub(r"\s+", "", t12.upper())
        return dt.datetime.strptime(cleaned, "%I:%M%p").strftime("%H:%M")

    @staticmethod
    def _to_12h(hhmm: str) -> str:
        return dt.datetime.strptime(hhmm, "%H:%M").strftime("%I:%M %p").lstrip("0")

    @staticmethod
    def _club_display_name(club_name: Optional[str], default_club: str) -> str:
        club = (club_name or default_club).strip()
        if not club.lower().startswith("gymbox "):
            club = f"Gymbox {club}"
        return club

    @staticmethod
    def _regex_escape_spaces(text: str) -> str:
        parts = re.split(r"\s+", text.strip())
        return r"\s+".join(re.escape(p) for p in parts if p)

    @staticmethod
    def _norm_text(s: str) -> str:
        s = s.strip().lower()
        s = s.replace("&", "and")
        s = re.sub(r"[^a-z0-9]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @staticmethod
    def _weeks_ahead_of_current_week(
        iso_date: str,
        today: Optional[dt.date] = None,
    ) -> int:
        """
        Returns how many 'next week' clicks are needed to reach the week
        containing iso_date, assuming the timetable initially opens on the
        current week.
        """
        if today is None:
            today = dt.date.today()

        target_date = dt.datetime.strptime(iso_date, "%Y-%m-%d").date()

        current_week_monday = today - dt.timedelta(days=today.weekday())
        target_week_monday = target_date - dt.timedelta(days=target_date.weekday())

        return max(0, (target_week_monday - current_week_monday).days // 7)

    def _extract_button_text(self, btn: Locator) -> str:
        for fn in (
            lambda: btn.get_attribute("aria-label"),
            lambda: btn.text_content(timeout=2000),
            lambda: btn.inner_text(timeout=2000),
        ):
            try:
                txt = fn()
                if txt:
                    return re.sub(r"\s+", " ", txt).strip()
            except Exception:
                pass
        return ""

    def _safe_click(self, locator: Locator, timeout: int = 10000) -> bool:
        try:
            locator.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass

        try:
            locator.click(timeout=timeout)
            return True
        except Exception:
            return False

    def login(self) -> None:
        page = self._page
        assert page is not None

        page.goto(f"{self.base_url}/login-register", wait_until="domcontentloaded")

        page.get_by_role("textbox", name="Email *").fill(self.email)
        page.get_by_role("textbox", name="Password *").fill(self.password)
        page.get_by_role("button", name="Login").click()

        try:
            page.get_by_role("button", name="Back").click(timeout=5000)
        except PWTimeout:
            pass

        page.wait_for_load_state("networkidle")
        self.logged_in = True

    def _ensure_logged_in(self) -> None:
        if not self.logged_in:
            self.login()

    def _return_to_classes(self) -> None:
        page = self._page
        assert page is not None

        try:
            page.get_by_role("link", name="Classes").click(timeout=5000)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        try:
            page.get_by_role("button", name="Back").click(timeout=5000)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        try:
            page.wait_for_load_state("networkidle")
        except Exception:
            pass

    def _open_booking_page(self, club_name: Optional[str]) -> None:
        page = self._page
        assert page is not None

        club = self._club_display_name(club_name, self.default_club)

        try:
            book_btn = page.get_by_role("button", name="Book a class")
            if book_btn.count() > 0:
                book_btn.first.click(timeout=5000)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1200)
                return
        except Exception:
            pass

        try:
            classes_link = page.get_by_role("link", name="Classes")
            if classes_link.count() > 0:
                classes_link.first.click(timeout=5000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        try:
            back_btn = page.get_by_role("button", name="Back")
            if back_btn.count() > 0:
                back_btn.first.click(timeout=5000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        try:
            club_text = page.get_by_text(club, exact=False)
            if club_text.count() > 0:
                club_text.first.click(timeout=5000)
                page.wait_for_timeout(800)
                page.get_by_role("button", name="Book a class").click(timeout=10000)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1200)
                return
        except Exception:
            pass

        page.goto(self.base_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        try:
            page.get_by_role("button", name="Back").click(timeout=5000)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        page.get_by_text(club, exact=False).first.click(timeout=10000)
        page.wait_for_timeout(800)
        page.get_by_role("button", name="Book a class").click(timeout=10000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)

    def _navigate_to_target_week(self, iso_date: str) -> None:
        page = self._page
        assert page is not None

        week_jumps = self._weeks_ahead_of_current_week(iso_date)

        if week_jumps == 0:
            return

        for jump_index in range(week_jumps):
            try:
                next_btn = page.get_by_role("button", name="Arrow right")
                next_btn.first.click(timeout=5000)
                page.wait_for_timeout(1000)
                page.wait_for_load_state("networkidle")
            except Exception as exc:
                raise RuntimeError(
                    f"Could not move timetable to target week for {iso_date} "
                    f"(failed on jump {jump_index + 1} of {week_jumps})"
                ) from exc

    def _click_date_or_weekday(self, iso_date: str) -> None:
        page = self._page
        assert page is not None

        d = dt.datetime.strptime(iso_date, "%Y-%m-%d")
        month = d.strftime("%B")
        day = str(d.day)
        weekday = d.strftime("%A")

        candidates = [
            f"{month} {day},",
            f"{month} {day}",
            f"{weekday} {day}",
        ]

        for text in candidates:
            try:
                page.get_by_text(text, exact=False).click(timeout=4000)
                page.wait_for_timeout(1000)
                return
            except PWTimeout:
                continue

        raise RuntimeError(f"Could not select exact timetable date for {iso_date}")

    def _class_buttons(self) -> List[Locator]:
        page = self._page
        assert page is not None

        buttons = page.get_by_role("button")
        count = buttons.count()
        return [buttons.nth(i) for i in range(count)]

    def _parse_class_button(
        self,
        btn: Locator,
        date: str,
        location: str,
    ) -> Optional[GymboxClass]:
        flat_txt = self._extract_button_text(btn)
        if not flat_txt:
            return None

        if flat_txt in {
            "Next",
            "Back",
            "Filter",
            "Book a class",
            "Book now",
            "Close",
            "Done",
        }:
            return None

        time_match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)", flat_txt, flags=re.I)
        if not time_match:
            return None

        start_12 = time_match.group(1)
        start_24 = self._to_24h(start_12)

        class_name = flat_txt[:time_match.start()].strip(" ,|-")
        if not class_name:
            return None

        return GymboxClass(
            name=class_name,
            time=start_24,
            date=date,
            location=location,
            raw_text=flat_txt,
        )

    def fetch_timetable(
        self,
        club_name: Optional[str] = None,
        date: Optional[str] = None,
    ) -> List[GymboxClass]:
        self._ensure_logged_in()

        page = self._page
        assert page is not None

        target_club = self._club_display_name(club_name, self.default_club)
        date = date or dt.date.today().isoformat()

        self._open_booking_page(target_club)
        self._navigate_to_target_week(date)
        self._click_date_or_weekday(date)

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)

        classes: List[GymboxClass] = []

        for btn in self._class_buttons():
            parsed = self._parse_class_button(btn, date=date, location=target_club)
            if parsed:
                classes.append(parsed)

        deduped: List[GymboxClass] = []
        seen = set()

        for c in classes:
            key = (
                self._norm_text(c.name),
                c.time,
                c.date,
                self._norm_text(c.location),
            )
            if key not in seen:
                seen.add(key)
                deduped.append(c)

        return deduped

    def _find_matching_class_button(self, gym_class: GymboxClass) -> Optional[Locator]:
        class_name_pattern = self._regex_escape_spaces(gym_class.name)
        start_time_pattern = self._regex_escape_spaces(self._to_12h(gym_class.time))
        loose_pattern = re.compile(
            rf"{class_name_pattern}.*{start_time_pattern}",
            re.I,
        )

        for btn in self._class_buttons():
            flat_txt = self._extract_button_text(btn)
            if not flat_txt:
                continue

            if loose_pattern.search(flat_txt):
                return btn

        return None

    def book_class(self, gym_class: GymboxClass) -> bool:
        page = self._page
        assert page is not None

        btn = self._find_matching_class_button(gym_class)
        if btn is None:
            raise RuntimeError(
                f"Could not find class button for {gym_class.name} at {gym_class.time} on {gym_class.date}"
            )

        btn.scroll_into_view_if_needed(timeout=3000)
        btn.click(timeout=10000)

        page.wait_for_timeout(1000)

        try:
            page.get_by_role("button", name=re.compile(r"next", re.I)).click(timeout=4000)
            page.wait_for_timeout(500)
        except PWTimeout:
            pass

        try:
            page.get_by_role("button", name=re.compile(r"book now", re.I)).click(timeout=7000)
            page.wait_for_timeout(1000)
        except PWTimeout:
            pass

        success_patterns = [
            r"you have been successfully entered",
            r"booking confirmed",
            r"booked",
            r"cancel",
            r"waiting list",
        ]

        for pattern in success_patterns:
            try:
                page.get_by_text(re.compile(pattern, re.I)).first.wait_for(timeout=6000)
                self._return_to_classes()
                return True
            except PWTimeout:
                pass

        try:
            refreshed_btn = self._find_matching_class_button(gym_class)
            if refreshed_btn:
                txt = self._extract_button_text(refreshed_btn).lower()
                if any(x in txt for x in ["booked", "cancel", "waiting list"]):
                    self._return_to_classes()
                    return True
        except Exception:
            pass

        return False

    def book(self, gym_class: GymboxClass) -> bool:
        return self.book_class(gym_class)