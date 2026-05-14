"""
Rich table rendering for strength exercise lists.

Responsibilities:
- Build and return a Rich Table that displays a list of strength exercises
  with formatted columns and clear headers.
- Never open a database connection — callers provide the list of exercises.
"""

from rich.box import ROUNDED
from rich.table import Table

from fitness_cli.database.models import StrengthExercise

_EMPTY = "—"


def build_strength_table(
    exercises: list[StrengthExercise],
    title: str = "Strength",
) -> Table:
    """Build a Rich Table displaying the given strength exercises.

    Each row shows the exercise id, date, name, sets, reps, weight, duration,
    and notes. Nullable numeric columns render as "—" when empty.

    Args:
        exercises: The exercises to display.
        title: Optional table title shown above the header row.

    Returns:
        A fully populated Rich Table ready to be printed.
    """
    table = Table(title=title, show_header=True, header_style="bold cyan", box=ROUNDED)
    table.add_column("ID", justify="right", style="dim", no_wrap=True)
    table.add_column("Date", no_wrap=True)
    table.add_column("Exercise")
    table.add_column("Sets", justify="right")
    table.add_column("Reps", justify="right")
    table.add_column("Weight (kg)", justify="right")
    table.add_column("Duration (s)", justify="right")
    table.add_column("Notes", style="dim")

    for ex in exercises:
        table.add_row(
            str(ex.id or ""),
            str(ex.date),
            ex.exercise_name,
            str(ex.sets) if ex.sets is not None else _EMPTY,
            str(ex.reps) if ex.reps is not None else _EMPTY,
            f"{ex.weight_kg:.1f}" if ex.weight_kg is not None else _EMPTY,
            f"{ex.duration_seconds:.0f}" if ex.duration_seconds is not None else _EMPTY,
            ex.notes or "",
        )

    return table
