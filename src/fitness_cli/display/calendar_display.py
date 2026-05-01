"""
Terminal calendar rendering using Rich.

Responsibilities:
- Render a Sunday-first monthly calendar that matches the SVG grid layout.
- Colour each day dot according to the highest recorded activity intensity.
- Accept the same dict[date, Intensity] interface used by the SVG layer so
  no duplicate reduction logic is needed in callers.

Grid layout (matches wallpaper-template-spec.json):
  Columns 1–7 = Sun, Mon, Tue, Wed, Thu, Fri, Sat
  Rows    1–5 = weeks 1–5

Symbol and colour per intensity:
  None     →  ○   dim white
  LIGHT    →  ◎   yellow
  MODERATE →  ◉   bright_yellow bold
  HIGH     →  ●   orange1 bold
  PEAK     →  ⬤   bright_red bold

A Rich Table is used so that each column is sized consistently regardless of
the terminal display width of individual Unicode symbols.
"""

import calendar
import datetime

import rich.box
from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text

from fitness_cli.database.models import Intensity
from fitness_cli.svg.calendar_svg import to_dow as _to_dow

_DOW_HEADERS = ("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa")

#: Symbol and (non-bold base) style for each intensity level.
_INTENSITY_DISPLAY: dict[Intensity, tuple[str, Style]] = {
    Intensity.LIGHT: ("◎", Style(color="yellow")),
    Intensity.MODERATE: ("◉", Style(color="bright_yellow", bold=True)),
    Intensity.HIGH: ("●", Style(color="orange1", bold=True)),
    Intensity.PEAK: ("⬤", Style(color="bright_red", bold=True)),
}

_NO_ACTIVITY_SYMBOL = "○"
_NO_ACTIVITY_STYLE = Style(color="white", dim=True)

#: Minimum column width keeps cells aligned regardless of symbol render width.
_COL_WIDTH = 3


def _month_grid(year: int, month: int) -> list[list[datetime.date | None]]:
    """Build a 5×7 grid of dates for the given month.

    Each row is a week (Sun–Sat). Out-of-month slots are None.

    Args:
        year: Four-digit year.
        month: Month number (1–12).

    Returns:
        List of 5 rows, each a list of 7 items (date or None).
    """
    first = datetime.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    dow1 = _to_dow(first)  # which column (1-indexed) day 1 falls in

    grid: list[list[datetime.date | None]] = [[None] * 7 for _ in range(5)]
    for day_num in range(1, last_day + 1):
        d = datetime.date(year, month, day_num)
        offset = (day_num - 1) + (dow1 - 1)
        row = offset // 7
        col = offset % 7
        if row < 5:
            grid[row][col] = d
    return grid


def _day_cell(date: datetime.date, active_days: dict[datetime.date, Intensity]) -> Text:
    """Return a styled Text cell for a single calendar day.

    Args:
        date: The calendar date to render.
        active_days: Mapping of date → highest intensity for that day.

    Returns:
        A Rich Text object with the appropriate symbol and colour.
    """
    intensity = active_days.get(date)
    if intensity is None:
        return Text(_NO_ACTIVITY_SYMBOL, style=_NO_ACTIVITY_STYLE, justify="center")
    symbol, style = _INTENSITY_DISPLAY[intensity]
    return Text(symbol, style=style, justify="center")


def render_calendar(
    year: int,
    month: int,
    active_days: dict[datetime.date, Intensity],
    console: Console | None = None,
) -> None:
    """Print a colour-coded monthly calendar to the terminal via a Rich Table.

    The calendar is Sunday-first, matching the wallpaper SVG layout. Each day
    slot is rendered as a coloured Unicode symbol based on the activity
    intensity recorded for that date. Using a Rich Table ensures every column
    is the same width regardless of the terminal display width of each symbol.

    Args:
        year: Four-digit year.
        month: Month number (1–12).
        active_days: Mapping of date to the highest recorded intensity for
            that day. Dates outside the given month are ignored.
        console: Rich Console to print to. Defaults to a new Console() if not
            provided (useful for testing with a captured console).
    """
    if console is None:
        console = Console()

    month_name = calendar.month_name[month]

    table = Table(
        title=f"{month_name.upper()} {year}",
        title_style="bold cyan",
        box=rich.box.SIMPLE_HEAD,
        show_footer=False,
        show_edge=False,
        padding=(0, 1),
    )

    for header in _DOW_HEADERS:
        table.add_column(
            header,
            justify="center",
            header_style="bold white",
            min_width=_COL_WIDTH,
            max_width=_COL_WIDTH,
        )

    grid = _month_grid(year, month)
    for week in grid:
        row: list[Text | str] = []
        for date in week:
            row.append("" if date is None else _day_cell(date, active_days))
        table.add_row(*row)

    console.print(table)
