"""
CLI commands for recording, listing, updating, and deleting strength exercises.

Responsibilities:
- Parse user input for the strength add, list, update, and delete sub-commands.
- The `add` sub-command runs an interactive loop, prompting for each exercise
  until the user enters a blank exercise name.
- Delegate all business logic to the operations and display layers.
- Print user-facing output to stdout and errors to stderr.
"""

import datetime
import sys

import click
from rich.console import Console

from fitness_cli.database.connection import get_connection
from fitness_cli.database.models import StrengthExercise, StrengthExerciseInput
from fitness_cli.display.strength_table import build_strength_table
from fitness_cli.operations.activity_operations import UNSET, Unset
from fitness_cli.operations.strength_operations import (
    add_strength_exercise,
    delete_strength_exercise,
    list_strength_exercises,
    update_strength_exercise,
)

_console = Console()


@click.group("strength")
def strength_group() -> None:
    """Commands for recording and viewing strength training exercises."""


@strength_group.command("add")
@click.option(
    "--date",
    "-d",
    "date_str",
    required=True,
    metavar="YYYY-MM-DD",
    help="Date of the strength session.",
)
def add_cmd(date_str: str) -> None:
    """Record one or more strength exercises for a date.

    Runs an interactive loop, prompting for each exercise until a blank
    exercise name is entered. Bodyweight, timed, and resistance exercises are
    all supported — leave fields blank when they do not apply.
    """
    try:
        session_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        click.echo(f"Error: invalid date '{date_str}'. Use YYYY-MM-DD format.", err=True)
        sys.exit(1)

    conn = get_connection()
    recorded = 0
    try:
        while True:
            name = click.prompt(
                "Exercise name (blank to finish)",
                default="",
                show_default=False,
            ).strip()
            if not name:
                break

            sets = _prompt_optional_int("Sets")
            reps = _prompt_optional_int("Reps per set (blank for timed exercises)")
            weight_kg = _prompt_optional_float("Weight kg (blank for bodyweight)")
            duration_seconds = _prompt_optional_float(
                "Duration seconds per set (blank for rep-based)"
            )
            notes = _prompt_optional_str("Notes (blank to skip)")

            exercise = add_strength_exercise(
                conn,
                StrengthExerciseInput(
                    date=session_date,
                    exercise_name=name,
                    sets=sets,
                    reps=reps,
                    weight_kg=weight_kg,
                    duration_seconds=duration_seconds,
                    notes=notes,
                ),
            )
            recorded += 1
            _console.print(
                f"[green]✓[/green] Added exercise [bold]#{exercise.id}[/bold]: "
                f"{exercise.exercise_name}."
            )
    finally:
        conn.close()

    if recorded == 0:
        _console.print("[dim]No exercises recorded.[/dim]")
    else:
        _console.print(
            f"[bold]Recorded {recorded} exercise{'s' if recorded != 1 else ''} "
            f"on {session_date}.[/bold]"
        )


@strength_group.command("list")
@click.option(
    "--date",
    "-d",
    "date_str",
    default=None,
    metavar="YYYY-MM-DD",
    help="Filter to a specific date.",
)
@click.option(
    "--month",
    "-m",
    "month_str",
    default=None,
    metavar="YYYY-MM",
    help="Filter to a specific calendar month.",
)
def list_cmd(date_str: str | None, month_str: str | None) -> None:
    """List strength exercises, optionally filtered to a date or month."""
    filter_date = _parse_date(date_str) if date_str is not None else None
    month = _parse_month(month_str)

    conn = get_connection()
    exercises = list_strength_exercises(conn, date=filter_date, month=month)
    conn.close()

    _print_exercises(exercises, title=_list_title(filter_date, month))


@strength_group.command("delete")
@click.argument("exercise_id", type=int)
def delete_cmd(exercise_id: int) -> None:
    """Delete a strength exercise by its ID."""
    conn = get_connection()
    deleted = delete_strength_exercise(conn, exercise_id)
    conn.close()
    if deleted:
        _console.print(f"[green]✓[/green] Deleted exercise [bold]#{exercise_id}[/bold].")
    else:
        click.echo(f"Error: no strength exercise with ID {exercise_id}.", err=True)
        sys.exit(1)


@strength_group.command("update")
@click.argument("exercise_id", type=int)
@click.option(
    "--date",
    "-d",
    "date_str",
    default=None,
    metavar="YYYY-MM-DD",
    help="New date for the exercise.",
)
@click.option(
    "--exercise",
    "-e",
    "exercise_name",
    default=None,
    help="New exercise name.",
)
@click.option(
    "--sets",
    "-s",
    default=None,
    type=int,
    help="New sets count.",
)
@click.option(
    "--reps",
    "-r",
    default=None,
    type=int,
    help="New reps per set.",
)
@click.option(
    "--weight",
    "-w",
    "weight_kg",
    default=None,
    type=float,
    help="New weight in kg.",
)
@click.option(
    "--duration",
    "-t",
    "duration_seconds",
    default=None,
    type=float,
    help="New duration per set in seconds.",
)
@click.option(
    "--notes",
    "-n",
    default=None,
    help="New notes.",
)
def update_cmd(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    exercise_id: int,
    date_str: str | None,
    exercise_name: str | None,
    sets: int | None,
    reps: int | None,
    weight_kg: float | None,
    duration_seconds: float | None,
    notes: str | None,
) -> None:
    """Update fields of an existing strength exercise by ID.

    Only fields supplied as flags are written; omitted fields are left
    unchanged. Clearing nullable fields to NULL is not supported via the CLI —
    delete and re-add the exercise if that is required.
    """
    if all(
        v is None
        for v in (
            date_str,
            exercise_name,
            sets,
            reps,
            weight_kg,
            duration_seconds,
            notes,
        )
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

    name_value: str | Unset = exercise_name if exercise_name is not None else UNSET
    sets_value: int | None | Unset = sets if sets is not None else UNSET
    reps_value: int | None | Unset = reps if reps is not None else UNSET
    weight_value: float | None | Unset = weight_kg if weight_kg is not None else UNSET
    duration_value: float | None | Unset = (
        duration_seconds if duration_seconds is not None else UNSET
    )
    notes_value: str | None | Unset = notes if notes is not None else UNSET

    conn = get_connection()
    updated = update_strength_exercise(
        conn,
        exercise_id,
        date=date_value,
        exercise_name=name_value,
        sets=sets_value,
        reps=reps_value,
        weight_kg=weight_value,
        duration_seconds=duration_value,
        notes=notes_value,
    )
    conn.close()

    if updated is None:
        click.echo(f"Error: no strength exercise with ID {exercise_id}.", err=True)
        sys.exit(1)
    _console.print(f"[green]✓[/green] Updated exercise [bold]#{exercise_id}[/bold].")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _prompt_optional_int(prompt_text: str) -> int | None:
    """Prompt for an optional integer; return None on blank input.

    Re-prompts on invalid input instead of crashing.
    """
    while True:
        raw = click.prompt(prompt_text, default="", show_default=False).strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            click.echo(f"Invalid integer '{raw}'. Try again or leave blank.", err=True)


def _prompt_optional_float(prompt_text: str) -> float | None:
    """Prompt for an optional float; return None on blank input.

    Re-prompts on invalid input instead of crashing.
    """
    while True:
        raw = click.prompt(prompt_text, default="", show_default=False).strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            click.echo(f"Invalid number '{raw}'. Try again or leave blank.", err=True)


def _prompt_optional_str(prompt_text: str) -> str | None:
    """Prompt for an optional string; return None on blank input."""
    raw = click.prompt(prompt_text, default="", show_default=False).strip()
    return raw or None


def _parse_date(date_str: str) -> datetime.date:
    """Parse a YYYY-MM-DD string, exiting with an error on failure."""
    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        click.echo(f"Error: invalid date '{date_str}'. Use YYYY-MM-DD format.", err=True)
        sys.exit(1)


def _parse_month(month_str: str | None) -> datetime.date | None:
    """Parse a YYYY-MM string to the first of that month, or None."""
    if month_str is None:
        return None
    try:
        return datetime.date.fromisoformat(f"{month_str}-01")
    except ValueError:
        click.echo(f"Error: invalid month '{month_str}'. Use YYYY-MM format.", err=True)
        sys.exit(1)


def _list_title(filter_date: datetime.date | None, month: datetime.date | None) -> str:
    """Build a table title describing the filter in use."""
    if filter_date is not None:
        return f"Strength — {filter_date}"
    if month is not None:
        return f"Strength — {month.strftime('%B %Y')}"
    return "All Strength Exercises"


def _print_exercises(exercises: list[StrengthExercise], title: str) -> None:
    """Render and print a strength table, or a 'none found' message."""
    if not exercises:
        _console.print("[dim]No strength exercises found.[/dim]")
        return
    table = build_strength_table(exercises, title=title)
    _console.print(table)
