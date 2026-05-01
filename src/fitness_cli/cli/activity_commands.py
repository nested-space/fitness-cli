"""
CLI commands for recording, listing, and visualising fitness activities.

Responsibilities:
- Parse user input for the activity add, list, recent, show, and delete sub-commands.
- Delegate all business logic to the operations and display layers.
- Print user-facing output to stdout and errors to stderr.
"""

import datetime
import sys

import click
from rich.console import Console

from fitness_cli.database.connection import get_connection
from fitness_cli.database.models import Activity, ActivityInput, ActivityType, Intensity
from fitness_cli.display.activity_table import build_activity_table
from fitness_cli.display.calendar_display import render_calendar
from fitness_cli.operations.activity_operations import (
    UNSET,
    Unset,
    add_activity,
    build_active_days,
    delete_activity,
    list_activities,
    list_last_n_activities,
    update_activity,
)

_console = Console()


@click.group("activity")
def activity_group() -> None:
    """Commands for recording and viewing fitness activities."""


@activity_group.command("add")
@click.option(
    "--date",
    "-d",
    "date_str",
    required=True,
    metavar="YYYY-MM-DD",
    help="Date of the activity.",
)
@click.option(
    "--type",
    "-a",
    "activity_type",
    required=True,
    type=click.Choice([t.value for t in ActivityType], case_sensitive=False),
    help="Activity category.",
)
@click.option(
    "--distance",
    "-k",
    "distance_km",
    type=float,
    default=None,
    help="Distance in km.",
)
@click.option(
    "--duration",
    "-t",
    "duration_minutes",
    required=True,
    type=float,
    help="Duration in minutes.",
)
@click.option(
    "--intensity",
    "-i",
    required=True,
    type=click.Choice([i.value for i in Intensity], case_sensitive=False),
    help="Self-reported intensity level.",
)
def add_cmd(
    date_str: str,
    activity_type: str,
    distance_km: float | None,
    duration_minutes: float,
    intensity: str,
) -> None:
    """Record a new fitness activity."""
    try:
        date = datetime.date.fromisoformat(date_str)
    except ValueError:
        click.echo(f"Error: invalid date '{date_str}'. Use YYYY-MM-DD format.", err=True)
        sys.exit(1)

    conn = get_connection()
    activity = add_activity(
        conn,
        ActivityInput(
            date=date,
            activity_type=ActivityType(activity_type),
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            intensity=Intensity(intensity),
        ),
    )
    conn.close()
    _console.print(
        f"[green]✓[/green] Added activity [bold]#{activity.id}[/bold]: "
        f"{activity.activity_type} on {activity.date}."
    )


@activity_group.command("list")
@click.option(
    "--month",
    "-m",
    "month_str",
    default=None,
    metavar="YYYY-MM",
    help="Filter to a specific calendar month.",
)
def list_cmd(month_str: str | None) -> None:
    """List all activities, optionally filtered to a month."""
    month = _parse_month(month_str)
    conn = get_connection()
    activities = list_activities(conn, month=month)
    conn.close()
    _print_activities(activities, title=_list_title(month))


@activity_group.command("recent")
@click.option(
    "--count",
    "-c",
    "count",
    default=10,
    show_default=True,
    type=int,
    help="Number of recent activities to show.",
)
def recent_cmd(count: int) -> None:
    """Show the most recent N activities, newest first."""
    if count < 1:
        click.echo("Error: --count must be at least 1.", err=True)
        sys.exit(1)
    conn = get_connection()
    activities = list_last_n_activities(conn, count)
    conn.close()
    _print_activities(activities, title=f"Last {count} Activities")


@activity_group.command("show")
@click.option(
    "--month",
    "-m",
    "month_str",
    default=None,
    metavar="YYYY-MM",
    help="Month to display (default: current month).",
)
def show_cmd(month_str: str | None) -> None:
    """Show a visual calendar of activity for a month."""
    month = _parse_month(month_str) or _current_month()
    conn = get_connection()
    activities = list_activities(conn, month=month)
    conn.close()

    active_days = build_active_days(activities)
    render_calendar(month.year, month.month, active_days, console=_console)

    _console.print()
    _console.print(
        "[bold]Legend:[/bold]  "
        "[white dim]○[/white dim] none  "
        "[yellow]◎[/yellow] light  "
        "[bright_yellow bold]◉[/bright_yellow bold] moderate  "
        "[orange1 bold]●[/orange1 bold] high  "
        "[bright_red bold]⬤[/bright_red bold] peak"
    )


@activity_group.command("delete")
@click.argument("activity_id", type=int)
def delete_cmd(activity_id: int) -> None:
    """Delete an activity by its ID."""
    conn = get_connection()
    deleted = delete_activity(conn, activity_id)
    conn.close()
    if deleted:
        _console.print(f"[green]✓[/green] Deleted activity [bold]#{activity_id}[/bold].")
    else:
        click.echo(f"Error: no activity with ID {activity_id}.", err=True)
        sys.exit(1)


@activity_group.command("update")
@click.argument("activity_id", type=int)
@click.option(
    "--date",
    "-d",
    "date_str",
    default=None,
    metavar="YYYY-MM-DD",
    help="New date for the activity.",
)
@click.option(
    "--type",
    "-a",
    "activity_type",
    default=None,
    type=click.Choice([t.value for t in ActivityType], case_sensitive=False),
    help="New activity category.",
)
@click.option(
    "--distance",
    "-k",
    "distance_km",
    default=None,
    type=float,
    help="New distance in km.",
)
@click.option(
    "--duration",
    "-t",
    "duration_minutes",
    default=None,
    type=float,
    help="New duration in minutes.",
)
@click.option(
    "--intensity",
    "-i",
    default=None,
    type=click.Choice([i.value for i in Intensity], case_sensitive=False),
    help="New intensity level.",
)
def update_cmd(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    activity_id: int,
    date_str: str | None,
    activity_type: str | None,
    distance_km: float | None,
    duration_minutes: float | None,
    intensity: str | None,
) -> None:
    """Update fields of an existing activity by ID.

    Only fields supplied as flags are written; omitted fields are left
    unchanged. Note: distance cannot be cleared to NULL via the CLI — delete
    and re-add the activity if that is required.
    """
    if all(
        v is None
        for v in (date_str, activity_type, distance_km, duration_minutes, intensity)
    ):
        click.echo("Error: specify at least one field to update.", err=True)
        sys.exit(1)

    date_value: datetime.date | Unset = UNSET
    if date_str is not None:
        try:
            date_value = datetime.date.fromisoformat(date_str)
        except ValueError:
            click.echo(f"Error: invalid date '{date_str}'. Use YYYY-MM-DD format.", err=True)
            sys.exit(1)

    type_value: ActivityType | Unset = (
        ActivityType(activity_type) if activity_type is not None else UNSET
    )
    distance_value: float | None | Unset = (
        distance_km if distance_km is not None else UNSET
    )
    duration_value: float | Unset = (
        duration_minutes if duration_minutes is not None else UNSET
    )
    intensity_value: Intensity | Unset = (
        Intensity(intensity) if intensity is not None else UNSET
    )

    conn = get_connection()
    updated = update_activity(
        conn,
        activity_id,
        date=date_value,
        activity_type=type_value,
        distance_km=distance_value,
        duration_minutes=duration_value,
        intensity=intensity_value,
    )
    conn.close()

    if updated is None:
        click.echo(f"Error: no activity with ID {activity_id}.", err=True)
        sys.exit(1)
    _console.print(f"[green]✓[/green] Updated activity [bold]#{activity_id}[/bold].")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_month(month_str: str | None) -> datetime.date | None:
    """Parse a YYYY-MM string to the first of that month, or None.

    Args:
        month_str: A string in YYYY-MM format, or None.

    Returns:
        A datetime.date for the first of the month, or None if month_str is None.

    Raises:
        SystemExit: If month_str cannot be parsed.
    """
    if month_str is None:
        return None
    try:
        return datetime.date.fromisoformat(f"{month_str}-01")
    except ValueError:
        click.echo(f"Error: invalid month '{month_str}'. Use YYYY-MM format.", err=True)
        sys.exit(1)


def _current_month() -> datetime.date:
    """Return the first day of the current calendar month."""
    today = datetime.date.today()
    return datetime.date(today.year, today.month, 1)


def _list_title(month: datetime.date | None) -> str:
    """Build a table title describing the activity filter in use.

    Args:
        month: The month filter, or None if all activities are shown.

    Returns:
        A human-readable title string.
    """
    if month is None:
        return "All Activities"
    return f"Activities — {month.strftime('%B %Y')}"


def _print_activities(activities: list[Activity], title: str) -> None:
    """Render and print an activity table, or a 'none found' message.

    Args:
        activities: Activities to display.
        title: Table title.
    """
    if not activities:
        _console.print("[dim]No activities found.[/dim]")
        return
    table = build_activity_table(activities, title=title)
    _console.print(table)
