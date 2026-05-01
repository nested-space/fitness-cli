#!/usr/bin/env python3
"""
set_calendar_month.py
Configures the 5x7 grid of Calendar-WW-DD objects in an Inkscape SVG to
represent a specific calendar month.

Grid layout
-----------
  Rows    01–05  = weeks 1–5
  Columns 01–07  = Sun, Mon, Tue, Wed, Thu, Fri, Sat

Rules applied
-------------
  1. Weekend dots (col 01 = Sun, col 07 = Sat) → fill #000000, fill-opacity 0.116777
  2. Weekday dots (col 02–06)                  → fill #242424, fill-opacity 1
  3. Out-of-month dots                         → display:none
  4. In-month dots                             → display:inline

Usage
-----
  python set_calendar_month.py <input.svg> <output.svg> <year> <month>

Example
-------
  python set_calendar_month.py in.svg out.svg 2026 4   # April 2026
"""

import calendar
import datetime
import re
import sys
from pathlib import Path

try:
    from lxml import etree
    LXML = True
except ImportError:
    import xml.etree.ElementTree as etree
    LXML = False


# ---------------------------------------------------------------------------
# Colour / style constants
# ---------------------------------------------------------------------------

WEEKEND_FILL    = "#000000"
WEEKEND_OPACITY = "0.116777"   # matches existing weekend style in the SVG
WEEKDAY_FILL    = "#242424"
WEEKDAY_OPACITY = "1"


def _set_style_prop(style: str, prop: str, value: str) -> str:
    """Set (or insert) a single CSS property inside an inline style string."""
    pattern = re.compile(
        r'(?<![a-z-])' + re.escape(prop) + r'\s*:[^;]*', re.IGNORECASE
    )
    replacement = f"{prop}:{value}"
    if pattern.search(style):
        return pattern.sub(replacement, style)
    style = style.rstrip(";")
    return f"{style};{replacement}"


def apply_day_style(elem, dow: int, hidden: bool) -> None:
    """
    Modify a calendar-day element's inline style.

    dow    : 1-7  (1=Sun … 7=Sat)
    hidden : True → display:none, False → display:inline
    """
    style = elem.get("style", "")
    style = _set_style_prop(style, "display", "none" if hidden else "inline")

    if not hidden:
        is_weekend = dow in (1, 7)
        style = _set_style_prop(style, "fill",         WEEKEND_FILL    if is_weekend else WEEKDAY_FILL)
        style = _set_style_prop(style, "fill-opacity",  WEEKEND_OPACITY if is_weekend else WEEKDAY_OPACITY)

    elem.set("style", style)


# ---------------------------------------------------------------------------
# Month geometry
# ---------------------------------------------------------------------------

def to_dow(d: datetime.date) -> int:
    """Return 1=Sun, 2=Mon, … 7=Sat for a date."""
    return (d.weekday() + 1) % 7 + 1


def month_day_grid(year: int, month: int) -> dict:
    """
    Return a mapping  (week, dow) → True | False
    True  = this cell is in-month
    False = this cell is out-of-month (before or after)

    week : 1-5
    dow  : 1-7  (1=Sun, 2=Mon, … 7=Sat)

    The grid always starts on Sunday (dow=1) and spans exactly 5 rows.
    Day 1 is placed in the column matching its day-of-week.
    """
    first_day = datetime.date(year, month, 1)
    last_day_num = calendar.monthrange(year, month)[1]
    dow1 = to_dow(first_day)   # column that day 1 falls in

    in_month = set()
    for day in range(1, last_day_num + 1):
        d = datetime.date(year, month, day)
        dow = to_dow(d)
        offset = (day - 1) + (dow1 - 1)
        week = offset // 7 + 1
        in_month.add((week, dow))

    return in_month


# ---------------------------------------------------------------------------
# SVG processing
# ---------------------------------------------------------------------------

INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
LABEL_ATTR  = f"{{{INKSCAPE_NS}}}label"
LABEL_RE    = re.compile(r'^calendar-day-(\d{2})-(\d{2})$')


def process(input_path: Path, output_path: Path, year: int, month: int) -> None:
    in_month = month_day_grid(year, month)

    if LXML:
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(str(input_path), parser)
        root = tree.getroot()
    else:
        tree = etree.parse(str(input_path))
        root = tree.getroot()

    updated = 0
    for elem in root.iter():
        label = (
            elem.get(LABEL_ATTR)
            or elem.get("label")
            or elem.get("inkscape:label")
            or ""
        )
        m = LABEL_RE.match(label)
        if not m:
            continue

        week = int(m.group(1))
        dow  = int(m.group(2))

        if not (1 <= week <= 5 and 1 <= dow <= 7):
            print(f"  Warning: '{label}' out of expected range — skipped")
            continue

        visible = (week, dow) in in_month
        apply_day_style(elem, dow, hidden=not visible)
        updated += 1
        print(f"  {label:20s}  week={week} dow={dow}  → {'visible' if visible else 'hidden'}")

    print(f"\n{updated} calendar-day objects updated.")

    if LXML:
        tree.write(
            str(output_path),
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
            pretty_print=False,
        )
    else:
        tree.write(str(output_path), xml_declaration=True, encoding="unicode")

    print(f"Written to: {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)

    input_path  = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    year        = int(sys.argv[3])
    month       = int(sys.argv[4])

    if not input_path.exists():
        print(f"Error: '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Configuring calendar for {calendar.month_name[month]} {year}…\n")
    process(input_path, output_path, year, month)


if __name__ == "__main__":
    main()
