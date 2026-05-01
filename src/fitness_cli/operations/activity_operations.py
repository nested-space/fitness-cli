"""
CRUD operations for the activities table.

Responsibilities:
- Convert between sqlite3.Row records and Activity dataclasses.
- Provide typed functions for adding, listing, and deleting activities.
- Never open a database connection — callers pass a sqlite3.Connection.
"""

import datetime
import sqlite3

from fitness_cli.database.models import Activity, ActivityInput, ActivityType, Intensity


def _row_to_activity(row: sqlite3.Row) -> Activity:
    """Convert a sqlite3.Row from the activities table into an Activity dataclass.

    Args:
        row: A row returned by a SELECT on the activities table.

    Returns:
        A fully populated Activity instance.
    """
    return Activity(
        id=row["id"],
        date=datetime.date.fromisoformat(row["date"]),
        activity_type=ActivityType(row["activity_type"]),
        distance_km=row["distance_km"],
        duration_minutes=row["duration_minutes"],
        intensity=Intensity(row["intensity"]),
    )


def add_activity(conn: sqlite3.Connection, activity_input: ActivityInput) -> Activity:
    """Insert a new activity into the database and return it with its assigned id.

    Args:
        conn: Open SQLite connection with the activities table present.
        activity_input: The activity fields to persist.

    Returns:
        The newly created Activity with its database id populated.
    """
    cur = conn.execute(
        """
        INSERT INTO activities (date, activity_type, distance_km, duration_minutes, intensity)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            activity_input.date.isoformat(),
            activity_input.activity_type.value,
            activity_input.distance_km,
            activity_input.duration_minutes,
            activity_input.intensity.value,
        ),
    )
    conn.commit()
    return Activity(
        id=cur.lastrowid,
        date=activity_input.date,
        activity_type=activity_input.activity_type,
        distance_km=activity_input.distance_km,
        duration_minutes=activity_input.duration_minutes,
        intensity=activity_input.intensity,
    )


def list_activities(
    conn: sqlite3.Connection,
    month: datetime.date | None = None,
) -> list[Activity]:
    """Return activities ordered by date, optionally filtered to a calendar month.

    Args:
        conn: Open SQLite connection with the activities table present.
        month: When provided, only activities whose date falls within this
            calendar month (year + month) are returned. The day component of
            the date is ignored.

    Returns:
        List of Activity instances ordered by date ascending.
    """
    if month is None:
        cur = conn.execute("SELECT * FROM activities ORDER BY date ASC;")
    else:
        first = datetime.date(month.year, month.month, 1)
        # Compute last day by rolling to the next month's first day minus 1.
        if month.month == 12:
            last = datetime.date(month.year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            last = datetime.date(month.year, month.month + 1, 1) - datetime.timedelta(days=1)

        cur = conn.execute(
            "SELECT * FROM activities WHERE date BETWEEN ? AND ? ORDER BY date ASC;",
            (first.isoformat(), last.isoformat()),
        )
    return [_row_to_activity(row) for row in cur.fetchall()]


def delete_activity(conn: sqlite3.Connection, activity_id: int) -> bool:
    """Delete an activity by its id.

    Args:
        conn: Open SQLite connection with the activities table present.
        activity_id: The id of the activity to delete.

    Returns:
        True if a row was deleted, False if no activity with that id existed.
    """
    cur = conn.execute("DELETE FROM activities WHERE id = ?;", (activity_id,))
    conn.commit()
    return cur.rowcount > 0


def get_activity(conn: sqlite3.Connection, activity_id: int) -> Activity | None:
    """Fetch a single activity by its id.

    Args:
        conn: Open SQLite connection with the activities table present.
        activity_id: The id of the activity to fetch.

    Returns:
        The Activity if found, or None if no activity with that id exists.
    """
    cur = conn.execute("SELECT * FROM activities WHERE id = ?;", (activity_id,))
    row = cur.fetchone()
    return _row_to_activity(row) if row else None


def list_last_n_activities(conn: sqlite3.Connection, count: int) -> list[Activity]:
    """Return the most recent activities, newest first.

    Args:
        conn: Open SQLite connection with the activities table present.
        count: Maximum number of activities to return. Must be >= 1.

    Returns:
        List of Activity instances ordered by date descending, then id descending.
        May contain fewer than count items if the database has fewer rows.

    Raises:
        ValueError: If count is less than 1.
    """
    if count < 1:
        raise ValueError(f"count must be >= 1, got {count}")
    cur = conn.execute(
        "SELECT * FROM activities ORDER BY date DESC, id DESC LIMIT ?;",
        (count,),
    )
    return [_row_to_activity(row) for row in cur.fetchall()]


_INTENSITY_RANK: dict[Intensity, int] = {
    Intensity.LIGHT: 0,
    Intensity.MODERATE: 1,
    Intensity.HIGH: 2,
    Intensity.PEAK: 3,
}


def build_active_days(activities: list[Activity]) -> dict[datetime.date, Intensity]:
    """Build a date → intensity mapping, keeping the highest intensity per day.

    When multiple activities fall on the same date the one with the highest
    intensity (PEAK > HIGH > MODERATE > LIGHT) is used for the calendar colour.

    Args:
        activities: List of Activity instances.

    Returns:
        Mapping of date to the highest recorded intensity on that date.
    """
    result: dict[datetime.date, Intensity] = {}
    for act in activities:
        existing = result.get(act.date)
        if existing is None or _INTENSITY_RANK[act.intensity] > _INTENSITY_RANK[existing]:
            result[act.date] = act.intensity
    return result
