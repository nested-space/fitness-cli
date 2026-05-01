"""
Calendar month layout and activity-day colouring for the wallpaper SVG.

Responsibilities:
- Configure the 5×7 grid of calendar-day-WW-DD elements to represent a
  specific calendar month (porting the logic from set_calendar_month.py).
- Override the fill colour of in-month days that have recorded activity,
  using light yellow for light intensity and yellow for moderate/high.

Element label pattern: calendar-day-WW-DD (week 01–05, day-of-week 01–07,
where 01=Sunday and 07=Saturday).
"""

import calendar
import datetime
import re

from lxml import etree

from fitness_cli.config.settings import (
    COLOUR_ACTIVE_ACTIVITY,
    COLOUR_LIGHT_ACTIVITY,
    COLOUR_WEEKDAY_DEFAULT,
    COLOUR_WEEKEND_DEFAULT,
    OPACITY_WEEKEND_DEFAULT,
)
from fitness_cli.database.models import Intensity
from fitness_cli.svg.svg_editor import INKSCAPE_LABEL_ATTR, set_style_prop

_LABEL_RE = re.compile(r"^calendar-day-(\d{2})-(\d{2})$")


def _get_label(elem: etree._Element) -> str:
    """Return the inkscape:label (or plain label) of an element, or empty string."""
    return elem.get(INKSCAPE_LABEL_ATTR) or elem.get("label") or ""


def to_dow(date: datetime.date) -> int:
    """Return the day-of-week as used in the SVG grid (1=Sunday … 7=Saturday).

    Args:
        date: Any calendar date.

    Returns:
        Integer in the range 1–7 where 1 is Sunday.
    """
    return (date.weekday() + 1) % 7 + 1


def _month_grid(year: int, month: int) -> set[tuple[int, int]]:
    """Return the set of (week, dow) positions that are in-month.

    The grid always starts on Sunday (dow=1) and spans exactly 5 rows.
    Day 1 is placed in the column matching its day-of-week.

    Args:
        year: Four-digit year.
        month: Month number (1–12).

    Returns:
        Set of (week, dow) tuples for in-month days. week is 1–5, dow is 1–7.
    """
    first_day = datetime.date(year, month, 1)
    last_day_num = calendar.monthrange(year, month)[1]
    dow1 = to_dow(first_day)

    in_month: set[tuple[int, int]] = set()
    for day_num in range(1, last_day_num + 1):
        d = datetime.date(year, month, day_num)
        dow = to_dow(d)
        offset = (day_num - 1) + (dow1 - 1)
        week = offset // 7 + 1
        in_month.add((week, dow))
    return in_month


def _date_to_grid(year: int, month: int, date: datetime.date) -> tuple[int, int] | None:
    """Convert a date to its (week, dow) grid position for the given month.

    Args:
        year: The month's year.
        month: The month number (1–12).
        date: The date to convert; must fall within the given month.

    Returns:
        (week, dow) tuple, or None if the date is outside the month.
    """
    if date.year != year or date.month != month:
        return None
    first_day = datetime.date(year, month, 1)
    dow1 = to_dow(first_day)
    dow = to_dow(date)
    offset = (date.day - 1) + (dow1 - 1)
    week = offset // 7 + 1
    return (week, dow)


def set_calendar_month(
    root: etree._Element,
    year: int,
    month: int,
) -> None:
    """Configure the calendar day grid to represent the given month.

    Sets each calendar-day-WW-DD element to be visible or hidden, and applies
    the default weekday/weekend fill colours to visible days.

    Args:
        root: Root element of the parsed SVG.
        year: Four-digit year.
        month: Month number (1–12).
    """
    in_month = _month_grid(year, month)

    for elem in root.iter():
        m = _LABEL_RE.match(_get_label(elem))
        if not m:
            continue

        week = int(m.group(1))
        dow = int(m.group(2))

        if not (1 <= week <= 5 and 1 <= dow <= 7):
            continue

        visible = (week, dow) in in_month
        set_style_prop(elem, "display", "inline" if visible else "none")

        if visible:
            is_weekend = dow in (1, 7)
            fill = COLOUR_WEEKEND_DEFAULT if is_weekend else COLOUR_WEEKDAY_DEFAULT
            opacity = OPACITY_WEEKEND_DEFAULT if is_weekend else "1"
            set_style_prop(elem, "fill", fill)
            set_style_prop(elem, "fill-opacity", opacity)


def set_active_days(
    root: etree._Element,
    year: int,
    month: int,
    active_days: dict[datetime.date, Intensity],
) -> None:
    """Override the fill colour of calendar days that have recorded activity.

    Only in-month days are affected. Days with no entry in active_days retain
    their default weekday/weekend colour from set_calendar_month().

    Args:
        root: Root element of the parsed SVG.
        year: The month's year (must match the month set by set_calendar_month).
        month: The month number (1–12).
        active_days: Mapping of date → intensity for each day with activity.
            Dates outside the given month are silently ignored.
    """
    grid_intensity: dict[tuple[int, int], Intensity] = {}
    for date, intensity in active_days.items():
        pos = _date_to_grid(year, month, date)
        if pos is not None:
            grid_intensity[pos] = intensity

    if not grid_intensity:
        return

    for elem in root.iter():
        m = _LABEL_RE.match(_get_label(elem))
        if not m:
            continue

        week = int(m.group(1))
        dow = int(m.group(2))
        pos = (week, dow)

        if pos not in grid_intensity:
            continue

        colour = (
            COLOUR_LIGHT_ACTIVITY
            if grid_intensity[pos] == Intensity.LIGHT
            else COLOUR_ACTIVE_ACTIVITY
        )
        set_style_prop(elem, "fill", colour)
        set_style_prop(elem, "fill-opacity", "1")
