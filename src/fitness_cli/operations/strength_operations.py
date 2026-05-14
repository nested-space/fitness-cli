"""
CRUD operations for the strength_exercises table.

Responsibilities:
- Convert between sqlite3.Row records and StrengthExercise dataclasses.
- Provide typed functions for adding, listing, fetching, updating, and
  deleting strength exercises.
- Never open a database connection — callers pass a sqlite3.Connection.
"""

import datetime
import sqlite3

from fitness_cli.database.models import StrengthExercise, StrengthExerciseInput
from fitness_cli.operations.activity_operations import UNSET, Unset


def _row_to_strength_exercise(row: sqlite3.Row) -> StrengthExercise:
    """Convert a sqlite3.Row from the strength_exercises table into a StrengthExercise.

    Args:
        row: A row returned by a SELECT on the strength_exercises table.

    Returns:
        A fully populated StrengthExercise instance.
    """
    return StrengthExercise(
        id=row["id"],
        date=datetime.date.fromisoformat(row["date"]),
        exercise_name=row["exercise_name"],
        sets=row["sets"],
        reps=row["reps"],
        weight_kg=row["weight_kg"],
        duration_seconds=row["duration_seconds"],
        notes=row["notes"],
    )


def add_strength_exercise(
    conn: sqlite3.Connection,
    exercise_input: StrengthExerciseInput,
) -> StrengthExercise:
    """Insert a new strength exercise and return it with its assigned id.

    Args:
        conn: Open SQLite connection with the strength_exercises table present.
        exercise_input: The fields to persist.

    Returns:
        The newly created StrengthExercise with its database id populated.
    """
    cur = conn.execute(
        """
        INSERT INTO strength_exercises (
            date, exercise_name, sets, reps, weight_kg, duration_seconds, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            exercise_input.date.isoformat(),
            exercise_input.exercise_name,
            exercise_input.sets,
            exercise_input.reps,
            exercise_input.weight_kg,
            exercise_input.duration_seconds,
            exercise_input.notes,
        ),
    )
    conn.commit()
    return StrengthExercise(
        id=cur.lastrowid,
        date=exercise_input.date,
        exercise_name=exercise_input.exercise_name,
        sets=exercise_input.sets,
        reps=exercise_input.reps,
        weight_kg=exercise_input.weight_kg,
        duration_seconds=exercise_input.duration_seconds,
        notes=exercise_input.notes,
    )


def list_strength_exercises(
    conn: sqlite3.Connection,
    *,
    date: datetime.date | None = None,
    month: datetime.date | None = None,
) -> list[StrengthExercise]:
    """Return strength exercises, optionally filtered to a single date or month.

    Args:
        conn: Open SQLite connection with the strength_exercises table present.
        date: When provided, only exercises with this exact date are returned.
        month: When provided, only exercises whose date falls within this
            calendar month (year + month) are returned. The day component of
            the date is ignored. Ignored if `date` is also provided.

    Returns:
        List of StrengthExercise instances ordered by date ascending, then id
        ascending (so exercises within a single session retain insertion order).
    """
    if date is not None:
        cur = conn.execute(
            "SELECT * FROM strength_exercises WHERE date = ? ORDER BY date ASC, id ASC;",
            (date.isoformat(),),
        )
    elif month is not None:
        first = datetime.date(month.year, month.month, 1)
        if month.month == 12:
            last = datetime.date(month.year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            last = datetime.date(month.year, month.month + 1, 1) - datetime.timedelta(days=1)
        cur = conn.execute(
            "SELECT * FROM strength_exercises WHERE date BETWEEN ? AND ? "
            "ORDER BY date ASC, id ASC;",
            (first.isoformat(), last.isoformat()),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM strength_exercises ORDER BY date ASC, id ASC;"
        )
    return [_row_to_strength_exercise(row) for row in cur.fetchall()]


def get_strength_exercise(
    conn: sqlite3.Connection,
    exercise_id: int,
) -> StrengthExercise | None:
    """Fetch a single strength exercise by its id.

    Args:
        conn: Open SQLite connection with the strength_exercises table present.
        exercise_id: The id of the exercise to fetch.

    Returns:
        The StrengthExercise if found, or None if no exercise with that id exists.
    """
    cur = conn.execute(
        "SELECT * FROM strength_exercises WHERE id = ?;", (exercise_id,)
    )
    row = cur.fetchone()
    return _row_to_strength_exercise(row) if row else None


_UPDATE_COLUMNS: dict[str, str] = {
    "date": "date",
    "exercise_name": "exercise_name",
    "sets": "sets",
    "reps": "reps",
    "weight_kg": "weight_kg",
    "duration_seconds": "duration_seconds",
    "notes": "notes",
}


def update_strength_exercise(  # pylint: disable=too-many-arguments
    conn: sqlite3.Connection,
    exercise_id: int,
    *,
    date: datetime.date | Unset = UNSET,
    exercise_name: str | Unset = UNSET,
    sets: int | None | Unset = UNSET,
    reps: int | None | Unset = UNSET,
    weight_kg: float | None | Unset = UNSET,
    duration_seconds: float | None | Unset = UNSET,
    notes: str | None | Unset = UNSET,
) -> StrengthExercise | None:
    """Partially update a strength exercise, writing only fields that were supplied.

    Each keyword argument defaults to the UNSET sentinel. Fields equal to UNSET
    are not touched; fields with any other value (including None for the
    nullable columns) are written. This lets callers distinguish "leave alone"
    from "clear to NULL".

    Args:
        conn: Open SQLite connection with the strength_exercises table present.
        exercise_id: The id of the exercise to update.
        date: New date, or leave unchanged if omitted.
        exercise_name: New exercise name, or leave unchanged if omitted.
        sets: New sets count (use None to clear), or leave unchanged.
        reps: New reps per set (use None to clear), or leave unchanged.
        weight_kg: New weight (use None to clear), or leave unchanged.
        duration_seconds: New duration (use None to clear), or leave unchanged.
        notes: New notes (use None to clear), or leave unchanged.

    Returns:
        The refreshed StrengthExercise if the row exists, otherwise None. If no
        fields are supplied the function performs no UPDATE and simply returns
        the current row (or None if missing).
    """
    raw: dict[str, object] = {
        "date": date.isoformat() if isinstance(date, datetime.date) else date,
        "exercise_name": exercise_name,
        "sets": sets,
        "reps": reps,
        "weight_kg": weight_kg,
        "duration_seconds": duration_seconds,
        "notes": notes,
    }
    updates: list[tuple[str, object]] = [
        (_UPDATE_COLUMNS[name], value)
        for name, value in raw.items()
        if not isinstance(value, Unset)
    ]

    if updates:
        set_clause = ", ".join(f"{col} = ?" for col, _ in updates)
        params: tuple[object, ...] = tuple(value for _, value in updates) + (exercise_id,)
        conn.execute(
            f"UPDATE strength_exercises SET {set_clause} WHERE id = ?;",
            params,
        )
        conn.commit()

    return get_strength_exercise(conn, exercise_id)


def delete_strength_exercise(conn: sqlite3.Connection, exercise_id: int) -> bool:
    """Delete a strength exercise by its id.

    Args:
        conn: Open SQLite connection with the strength_exercises table present.
        exercise_id: The id of the exercise to delete.

    Returns:
        True if a row was deleted, False if no exercise with that id existed.
    """
    cur = conn.execute(
        "DELETE FROM strength_exercises WHERE id = ?;", (exercise_id,)
    )
    conn.commit()
    return cur.rowcount > 0
