"""
Milestone calculation logic for distance and consistency badges.

Responsibilities:
- Calculate the distance milestone: floor of the maximum single-activity
  distance recorded in the last 4 calendar weeks.
- Calculate the consistency milestone: the number of consecutive complete
  weeks immediately preceding the current (incomplete) week.
- A week runs Monday–Sunday.
- A complete week requires at least 2 moderate/high activities AND at least
  3 activities in total.

Neither function opens a database connection — callers provide the connection.
"""

import datetime
import math
import sqlite3
from collections import defaultdict

from fitness_cli.database.models import Intensity


def _week_start(date: datetime.date) -> datetime.date:
    """Return the Monday that starts the ISO week containing date.

    Args:
        date: Any calendar date.

    Returns:
        The Monday of the same ISO week as date.
    """
    return date - datetime.timedelta(days=date.weekday())


def distance_milestone(
    conn: sqlite3.Connection,
    reference_date: datetime.date | None = None,
) -> int:
    """Return the distance milestone value for the current period.

    The milestone is the floor of the maximum single-activity distance (km)
    recorded in the 4-week window ending on the day before reference_date.
    A milestone of 0 means no qualifying activity exists.

    Args:
        conn: Open SQLite connection with the activities table present.
        reference_date: The date to treat as "today". Defaults to today's date.
            Useful for testing.

    Returns:
        Floor of the maximum distance (km) in the last 4 weeks, as an integer.
        Returns 0 if no activities with a distance exist in that window.
    """
    today = reference_date or datetime.date.today()
    window_start = today - datetime.timedelta(weeks=4)

    cur = conn.execute(
        """
        SELECT MAX(distance_km) AS max_distance
        FROM activities
        WHERE date >= ? AND date < ?
          AND distance_km IS NOT NULL
        """,
        (window_start.isoformat(), today.isoformat()),
    )
    row = cur.fetchone()
    if row is None or row["max_distance"] is None:
        return 0
    return math.floor(float(row["max_distance"]))


def consistency_milestone(
    conn: sqlite3.Connection,
    reference_date: datetime.date | None = None,
) -> int:
    """Return the consistency milestone value.

    Counts consecutive complete weeks ending immediately before the week that
    contains reference_date. The current (potentially incomplete) week is not
    counted.

    A week is complete when it contains:
    - At least 3 activities in total, AND
    - At least 2 activities with intensity 'moderate' or 'high'.

    Weeks are scanned in reverse chronological order starting from the week
    before the current week. Scanning stops at the first incomplete week.

    Args:
        conn: Open SQLite connection with the activities table present.
        reference_date: The date to treat as "today". Defaults to today's date.
            Useful for testing.

    Returns:
        Count of consecutive complete weeks before the current week.
        Returns 0 if the immediately preceding week was not complete.
    """
    today = reference_date or datetime.date.today()
    current_week_start = _week_start(today)

    # Fetch all activities before the current week.
    cur = conn.execute(
        "SELECT date, intensity FROM activities WHERE date < ? ORDER BY date ASC;",
        (current_week_start.isoformat(),),
    )
    rows = cur.fetchall()

    if not rows:
        return 0

    # Group activities by their week start (Monday).
    week_activities: dict[datetime.date, list[str]] = defaultdict(list)
    for row in rows:
        d = datetime.date.fromisoformat(row["date"])
        week_activities[_week_start(d)].append(row["intensity"])

    # Walk backwards week by week from the week before current_week_start.
    consecutive = 0
    week = current_week_start - datetime.timedelta(weeks=1)

    while True:
        intensities = week_activities.get(week, [])
        total = len(intensities)
        strong = sum(
            1 for i in intensities
            if i in (Intensity.MODERATE.value, Intensity.HIGH.value, Intensity.PEAK.value)
        )
        if total >= 3 and strong >= 2:
            consecutive += 1
            week -= datetime.timedelta(weeks=1)
        else:
            break

    return consecutive
