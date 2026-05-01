"""
Rich table rendering for activity lists.

Responsibilities:
- Build and return a Rich Table that displays a list of activities with
  colour-coded intensity, formatted columns, and clear headers.
- Never open a database connection — callers provide the list of activities.
"""

from rich.box import ROUNDED
from rich.style import Style
from rich.table import Table
from rich.text import Text

from fitness_cli.database.models import Activity, Intensity

#: Maps each intensity level to the Rich style used for that row's intensity cell.
_INTENSITY_STYLE: dict[Intensity, Style] = {
    Intensity.LIGHT: Style(color="yellow"),
    Intensity.MODERATE: Style(color="bright_yellow", bold=True),
    Intensity.HIGH: Style(color="orange1", bold=True),
    Intensity.PEAK: Style(color="bright_red", bold=True),
}


def build_activity_table(activities: list[Activity], title: str = "Activities") -> Table:
    """Build a Rich Table displaying the given activities.

    Each row shows the activity id, date, type, distance, duration, and
    intensity. The intensity cell is coloured by level. Rows are displayed
    in the order provided by the caller.

    Args:
        activities: The activities to display.
        title: Optional table title shown above the header row.

    Returns:
        A fully populated Rich Table ready to be printed.
    """
    table = Table(title=title, show_header=True, header_style="bold cyan", box=ROUNDED)
    table.add_column("ID", justify="right", style="dim", no_wrap=True)
    table.add_column("Date", no_wrap=True)
    table.add_column("Type")
    table.add_column("km", justify="right")
    table.add_column("min", justify="right")
    table.add_column("Intensity")

    for act in activities:
        km = f"{act.distance_km:.1f}" if act.distance_km is not None else "—"
        intensity_text = Text(act.intensity.value, style=_INTENSITY_STYLE[act.intensity])
        table.add_row(
            str(act.id or ""),
            str(act.date),
            act.activity_type.value,
            km,
            f"{act.duration_minutes:.0f}",
            intensity_text,
        )

    return table
