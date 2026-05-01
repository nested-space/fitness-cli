"""Tests for calendar month layout and active-day colouring."""

import datetime

from lxml import etree

from fitness_cli.config.settings import (
    COLOUR_ACTIVE_ACTIVITY,
    COLOUR_LIGHT_ACTIVITY,
    COLOUR_WEEKDAY_DEFAULT,
    COLOUR_WEEKEND_DEFAULT,
)
from fitness_cli.database.models import Intensity
from fitness_cli.svg.calendar_svg import set_active_days, set_calendar_month

_NS = "http://www.inkscape.org/namespaces/inkscape"


def _make_calendar_svg(year: int, month: int) -> etree._Element:
    """Build a minimal SVG with all 35 calendar-day-WW-DD elements."""
    root = etree.Element("svg")
    for week in range(1, 6):
        for dow in range(1, 8):
            elem = etree.SubElement(root, "circle")
            label = f"calendar-day-{week:02d}-{dow:02d}"
            elem.set(f"{{{_NS}}}label", label)
            elem.set("style", "display:inline;fill:#242424;fill-opacity:1")
    return root


def _get_style(root: etree._Element, week: int, dow: int) -> str:
    """Helper: retrieve the style string of a specific calendar-day element."""
    label = f"calendar-day-{week:02d}-{dow:02d}"
    for elem in root.iter():
        if elem.get(f"{{{_NS}}}label") == label:
            return elem.get("style", "")
    return ""


class TestSetCalendarMonth:
    """Tests for set_calendar_month()."""

    def test_april_2026_day_one_is_wednesday(self) -> None:
        """April 2026 starts on a Wednesday (dow=4); week-1-dow-4 should be visible."""
        # April 1 2026 is a Wednesday → dow=4
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        style = _get_style(root, 1, 4)
        assert "display:inline" in style

    def test_april_2026_week1_sunday_hidden(self) -> None:
        """Week-1-dow-1 (Sunday before April 1) should be hidden for April 2026."""
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        style = _get_style(root, 1, 1)
        assert "display:none" in style

    def test_weekday_gets_default_fill(self) -> None:
        """A visible weekday gets the default weekday fill colour."""
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        # April 1 2026 is Wednesday (dow=4), in-month
        style = _get_style(root, 1, 4)
        assert COLOUR_WEEKDAY_DEFAULT in style

    def test_saturday_gets_weekend_fill(self) -> None:
        """A visible Saturday (dow=7) gets the weekend fill colour."""
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        # April 4 2026 is Saturday → week=1, dow=7
        style = _get_style(root, 1, 7)
        assert COLOUR_WEEKEND_DEFAULT in style

    def test_hidden_day_has_no_fill_applied(self) -> None:
        """Hidden out-of-month days do not get a fill override."""
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        # Week 1, Sunday (dow=1) is out-of-month for April 2026
        style = _get_style(root, 1, 1)
        assert "display:none" in style

    def test_january_starts_on_thursday_2026(self) -> None:
        """January 2026 starts on Thursday (dow=5); week-1-dow-5 is visible."""
        root = _make_calendar_svg(2026, 1)
        set_calendar_month(root, 2026, 1)
        style = _get_style(root, 1, 5)
        assert "display:inline" in style


class TestSetActiveDays:
    """Tests for set_active_days()."""

    def test_light_activity_sets_light_colour(self) -> None:
        """A light-intensity day gets the light yellow fill."""
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        # April 15 2026 is Wednesday (dow=4)
        active: dict[datetime.date, Intensity] = {datetime.date(2026, 4, 15): Intensity.LIGHT}
        set_active_days(root, 2026, 4, active)
        # April 15: day 15, April 1 is dow=4; offset = 14 + 3 = 17 → week=3, dow=4
        style = _get_style(root, 3, 4)
        assert COLOUR_LIGHT_ACTIVITY in style

    def test_moderate_activity_sets_active_colour(self) -> None:
        """A moderate-intensity day gets the yellow fill."""
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        active: dict[datetime.date, Intensity] = {datetime.date(2026, 4, 15): Intensity.MODERATE}
        set_active_days(root, 2026, 4, active)
        style = _get_style(root, 3, 4)
        assert COLOUR_ACTIVE_ACTIVITY in style

    def test_high_activity_sets_active_colour(self) -> None:
        """A high-intensity day also gets the yellow fill (same as moderate)."""
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        active: dict[datetime.date, Intensity] = {datetime.date(2026, 4, 15): Intensity.HIGH}
        set_active_days(root, 2026, 4, active)
        style = _get_style(root, 3, 4)
        assert COLOUR_ACTIVE_ACTIVITY in style

    def test_date_outside_month_is_ignored(self) -> None:
        """A date from a different month does not change any element."""
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        active: dict[datetime.date, Intensity] = {datetime.date(2026, 5, 1): Intensity.HIGH}
        set_active_days(root, 2026, 4, active)
        # No element should have the active colour
        for week in range(1, 6):
            for dow in range(1, 8):
                style = _get_style(root, week, dow)
                assert COLOUR_ACTIVE_ACTIVITY not in style

    def test_empty_active_days_leaves_defaults(self) -> None:
        """With no active days the calendar remains at default colours."""
        root = _make_calendar_svg(2026, 4)
        set_calendar_month(root, 2026, 4)
        set_active_days(root, 2026, 4, {})
        style = _get_style(root, 1, 4)  # April 1, Wednesday
        assert COLOUR_WEEKDAY_DEFAULT in style
