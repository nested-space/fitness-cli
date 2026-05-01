"""
Milestone calculation logic for distance and consistency badges.

Responsibilities:
- Calculate the distance milestone: floor of the maximum single-activity
  distance recorded in the last 4 calendar weeks, restricted to running
  activities (Run and Treadmill).
- Calculate the consistency milestone: the number of consecutive complete
  weeks, starting from the current week and walking backwards.
- A week runs Monday–Sunday.
- A complete week requires at least 3 distinct days with any activity AND
  at least 2 distinct days where at least one activity is moderate/high/peak.
- The current (potentially incomplete) week is included if it already meets
  the criteria; otherwise the streak starts from the previous week.

Neither function opens a database connection — callers provide the connection.
"""

import datetime
import math
import sqlite3
from collections import defaultdict

from fitness_cli.config.settings import DISTANCE_ACTIVITY_TYPES
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
    recorded in the 4-week window ending on the day before reference_date,
    considering only running activities (Run and Treadmill).
    A milestone of 0 means no qualifying activity exists.

    Args:
        conn: Open SQLite connection with the activities table present.
        reference_date: The date to treat as "today". Defaults to today's date.
            Useful for testing.

    Returns:
        Floor of the maximum running distance (km) in the last 4 weeks.
        Returns 0 if no qualifying activities exist in that window.
    """
    today = reference_date or datetime.date.today()
    window_start = today - datetime.timedelta(weeks=4)

    placeholders = ",".join("?" * len(DISTANCE_ACTIVITY_TYPES))
    cur = conn.execute(
        f"""
        SELECT MAX(distance_km) AS max_distance
        FROM activities
        WHERE date >= ? AND date < ?
          AND distance_km IS NOT NULL
          AND activity_type IN ({placeholders})
        """,
        (window_start.isoformat(), today.isoformat(), *DISTANCE_ACTIVITY_TYPES),
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

    Counts consecutive complete weeks, starting from the current week and
    walking backwards. The current week is included in the count if it already
    satisfies the completion criteria; otherwise the streak starts from the
    preceding week.

    A week is complete when it has:
    - At least 3 distinct days with any activity recorded, AND
    - At least 2 distinct days on which at least one activity is
      moderate, high, or peak intensity.

    Note: multiple activities on the same day count as one day.

    Weeks are scanned in reverse chronological order. Scanning stops at the
    first incomplete week (after the initial current-week skip if needed).

    Args:
        conn: Open SQLite connection with the activities table present.
        reference_date: The date to treat as "today". Defaults to today's date.
            Useful for testing.

    Returns:
        Count of consecutive complete weeks including the current week if
        already complete. Returns 0 if no complete week is found.
    """
    today = reference_date or datetime.date.today()
    current_week_start = _week_start(today)

    _strong = frozenset((Intensity.MODERATE.value, Intensity.HIGH.value, Intensity.PEAK.value))

    # Fetch all activities up to and including today (current week is eligible).
    cur = conn.execute(
        "SELECT date, intensity FROM activities WHERE date <= ? ORDER BY date ASC;",
        (today.isoformat(),),
    )
    rows = cur.fetchall()

    if not rows:
        return 0

    # For each week, track the set of active days and the set of "strong" days.
    # A day is strong if any activity logged on it is moderate/high/peak.
    week_days: dict[datetime.date, set[datetime.date]] = defaultdict(set)
    week_strong_days: dict[datetime.date, set[datetime.date]] = defaultdict(set)
    for row in rows:
        d = datetime.date.fromisoformat(row["date"])
        week = _week_start(d)
        week_days[week].add(d)
        if row["intensity"] in _strong:
            week_strong_days[week].add(d)

    def _is_complete(week: datetime.date) -> bool:
        total = len(week_days.get(week, set()))
        strong = len(week_strong_days.get(week, set()))
        return total >= 3 and strong >= 2

    # Walk backwards starting from the current week.
    # If the current week is not yet complete, skip it and begin the streak
    # from the previous week — prior complete weeks still count.
    consecutive = 0
    week = current_week_start

    while True:
        if _is_complete(week):
            consecutive += 1
            week -= datetime.timedelta(weeks=1)
        elif week == current_week_start:
            # Current week not yet complete — skip it, start streak from prev week.
            week -= datetime.timedelta(weeks=1)
        else:
            break

    return consecutive
