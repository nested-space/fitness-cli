"""Tests for distance and consistency milestone calculations."""

import datetime
import sqlite3
from pathlib import Path

import pytest

from fitness_cli.database.connection import get_connection
from fitness_cli.database.models import ActivityInput, ActivityType, Intensity
from fitness_cli.operations.activity_operations import add_activity
from fitness_cli.operations.milestone_operations import (
    consistency_milestone,
    distance_milestone,
)


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """Fresh database for each test."""
    return get_connection(tmp_path / "test.db")


def _add(
    conn: sqlite3.Connection,
    date: datetime.date,
    distance: float | None = None,
    intensity: Intensity = Intensity.MODERATE,
    activity_type: ActivityType = ActivityType.RUN,
) -> None:
    """Helper to add an activity with minimal boilerplate."""
    add_activity(
        conn,
        ActivityInput(
            date=date,
            activity_type=activity_type,
            distance_km=distance,
            duration_minutes=30.0,
            intensity=intensity,
        ),
    )


# ---------------------------------------------------------------------------
# Reference date used across tests: a Monday so week boundaries are explicit.
# 2026-04-27 is a Monday.
# ---------------------------------------------------------------------------
REF = datetime.date(2026, 4, 27)  # current week start = 2026-04-27


class TestDistanceMilestone:
    """Tests for distance_milestone()."""

    def test_no_activities_returns_zero(self, conn: sqlite3.Connection) -> None:
        """Returns 0 when no activities exist."""
        assert distance_milestone(conn, reference_date=REF) == 0

    def test_floors_distance(self, conn: sqlite3.Connection) -> None:
        """Returns the floor of the maximum distance."""
        _add(conn, REF - datetime.timedelta(days=3), distance=8.9)
        assert distance_milestone(conn, reference_date=REF) == 8

    def test_uses_maximum_not_sum(self, conn: sqlite3.Connection) -> None:
        """Returns the single longest activity distance, not the total."""
        _add(conn, REF - datetime.timedelta(days=5), distance=3.0)
        _add(conn, REF - datetime.timedelta(days=3), distance=7.5)
        assert distance_milestone(conn, reference_date=REF) == 7

    def test_excludes_activities_older_than_4_weeks(self, conn: sqlite3.Connection) -> None:
        """Activities more than 4 weeks old are excluded."""
        _add(conn, REF - datetime.timedelta(weeks=5), distance=20.0)
        assert distance_milestone(conn, reference_date=REF) == 0

    def test_includes_activity_exactly_4_weeks_ago(self, conn: sqlite3.Connection) -> None:
        """Activity exactly 4 weeks before reference is included (window_start ≤ date < today)."""
        _add(conn, REF - datetime.timedelta(weeks=4), distance=10.0)
        assert distance_milestone(conn, reference_date=REF) == 10

    def test_excludes_reference_date_itself(self, conn: sqlite3.Connection) -> None:
        """Activity on the reference date is excluded (window is date < today)."""
        _add(conn, REF, distance=15.0)
        assert distance_milestone(conn, reference_date=REF) == 0

    def test_ignores_activities_without_distance(self, conn: sqlite3.Connection) -> None:
        """Strength activities with no distance do not affect the milestone."""
        _add(conn, REF - datetime.timedelta(days=2), distance=None,
             activity_type=ActivityType.STRENGTH)
        assert distance_milestone(conn, reference_date=REF) == 0

    def test_treadmill_distance_counts(self, conn: sqlite3.Connection) -> None:
        """Treadmill activities contribute to the distance milestone."""
        _add(conn, REF - datetime.timedelta(days=3), distance=6.0,
             activity_type=ActivityType.TREADMILL)
        assert distance_milestone(conn, reference_date=REF) == 6

    def test_non_running_distance_excluded(self, conn: sqlite3.Connection) -> None:
        """Non-running activities (e.g. Bike, Hike) are excluded even with a distance."""
        for activity_type in (ActivityType.BIKE, ActivityType.HIKE, ActivityType.TRAIL_RUN,
                              ActivityType.WALK, ActivityType.BIKE_INDOOR):
            _add(conn, REF - datetime.timedelta(days=3), distance=20.0,
                 activity_type=activity_type)
        assert distance_milestone(conn, reference_date=REF) == 0

    def test_run_beats_treadmill(self, conn: sqlite3.Connection) -> None:
        """Run and Treadmill both count; the maximum is returned."""
        _add(conn, REF - datetime.timedelta(days=5), distance=5.0,
             activity_type=ActivityType.TREADMILL)
        _add(conn, REF - datetime.timedelta(days=3), distance=9.5,
             activity_type=ActivityType.RUN)
        assert distance_milestone(conn, reference_date=REF) == 9


class TestConsistencyMilestone:
    """Tests for consistency_milestone()."""

    def test_no_activities_returns_zero(self, conn: sqlite3.Connection) -> None:
        """Returns 0 when no activities exist."""
        assert consistency_milestone(conn, reference_date=REF) == 0

    def test_previous_week_complete_returns_one(self, conn: sqlite3.Connection) -> None:
        """One complete week immediately before current week → milestone = 1."""
        # Previous week: 2026-04-20 (Mon) – 2026-04-26 (Sun)
        prev_mon = REF - datetime.timedelta(weeks=1)
        _add(conn, prev_mon, intensity=Intensity.MODERATE)
        _add(conn, prev_mon + datetime.timedelta(days=2), intensity=Intensity.HIGH)
        _add(conn, prev_mon + datetime.timedelta(days=4), intensity=Intensity.LIGHT)
        assert consistency_milestone(conn, reference_date=REF) == 1

    def test_two_consecutive_complete_weeks(self, conn: sqlite3.Connection) -> None:
        """Two consecutive complete weeks → milestone = 2."""
        for weeks_back in (1, 2):
            week_mon = REF - datetime.timedelta(weeks=weeks_back)
            _add(conn, week_mon, intensity=Intensity.MODERATE)
            _add(conn, week_mon + datetime.timedelta(days=2), intensity=Intensity.HIGH)
            _add(conn, week_mon + datetime.timedelta(days=4), intensity=Intensity.LIGHT)
        assert consistency_milestone(conn, reference_date=REF) == 2

    def test_gap_stops_count(self, conn: sqlite3.Connection) -> None:
        """A gap of one incomplete week resets the count."""
        # Week 1 ago: complete. Week 2 ago: incomplete. Week 3 ago: complete.
        for weeks_back in (1, 3):
            week_mon = REF - datetime.timedelta(weeks=weeks_back)
            _add(conn, week_mon, intensity=Intensity.MODERATE)
            _add(conn, week_mon + datetime.timedelta(days=2), intensity=Intensity.HIGH)
            _add(conn, week_mon + datetime.timedelta(days=4), intensity=Intensity.LIGHT)
        assert consistency_milestone(conn, reference_date=REF) == 1

    def test_incomplete_week_needs_enough_strong(self, conn: sqlite3.Connection) -> None:
        """A week with 3 activities but only 1 moderate/high is not complete."""
        prev_mon = REF - datetime.timedelta(weeks=1)
        _add(conn, prev_mon, intensity=Intensity.MODERATE)
        _add(conn, prev_mon + datetime.timedelta(days=2), intensity=Intensity.LIGHT)
        _add(conn, prev_mon + datetime.timedelta(days=4), intensity=Intensity.LIGHT)
        assert consistency_milestone(conn, reference_date=REF) == 0

    def test_incomplete_week_needs_enough_total(self, conn: sqlite3.Connection) -> None:
        """A week with 2 moderate activities but only 2 total is not complete."""
        prev_mon = REF - datetime.timedelta(weeks=1)
        _add(conn, prev_mon, intensity=Intensity.MODERATE)
        _add(conn, prev_mon + datetime.timedelta(days=2), intensity=Intensity.HIGH)
        assert consistency_milestone(conn, reference_date=REF) == 0

    def test_current_week_activities_excluded(self, conn: sqlite3.Connection) -> None:
        """Current week counts if it already meets the criteria."""
        # REF is Monday 2026-04-27; add 3 days' worth of activity within that week.
        _add(conn, REF, intensity=Intensity.MODERATE)
        _add(conn, REF + datetime.timedelta(days=2), intensity=Intensity.HIGH)
        _add(conn, REF + datetime.timedelta(days=4), intensity=Intensity.LIGHT)
        assert consistency_milestone(conn, reference_date=REF + datetime.timedelta(days=4)) == 1

    def test_current_week_incomplete_does_not_block_previous_streak(
        self, conn: sqlite3.Connection
    ) -> None:
        """A not-yet-complete current week is skipped; prior complete weeks still count."""
        # Previous week: complete.
        prev_mon = REF - datetime.timedelta(weeks=1)
        _add(conn, prev_mon, intensity=Intensity.MODERATE)
        _add(conn, prev_mon + datetime.timedelta(days=2), intensity=Intensity.HIGH)
        _add(conn, prev_mon + datetime.timedelta(days=4), intensity=Intensity.LIGHT)
        # Current week: only 1 activity — not yet complete.
        _add(conn, REF, intensity=Intensity.HIGH)
        assert consistency_milestone(conn, reference_date=REF) == 1

    def test_current_week_complete_plus_previous_gives_two(
        self, conn: sqlite3.Connection
    ) -> None:
        """Current week complete AND previous week complete → streak = 2."""
        for weeks_back in (0, 1):
            week_mon = REF - datetime.timedelta(weeks=weeks_back)
            _add(conn, week_mon, intensity=Intensity.MODERATE)
            _add(conn, week_mon + datetime.timedelta(days=2), intensity=Intensity.HIGH)
            _add(conn, week_mon + datetime.timedelta(days=4), intensity=Intensity.LIGHT)
        assert consistency_milestone(conn, reference_date=REF + datetime.timedelta(days=4)) == 2

    def test_two_activities_same_day_count_as_one_day(self, conn: sqlite3.Connection) -> None:
        """Multiple activities on the same day count as a single active day."""
        prev_mon = REF - datetime.timedelta(weeks=1)
        # Monday: two sessions — should still be 1 day, not 2.
        _add(conn, prev_mon, intensity=Intensity.MODERATE)
        _add(conn, prev_mon, intensity=Intensity.HIGH)
        # Wednesday and Friday: one session each.
        _add(conn, prev_mon + datetime.timedelta(days=2), intensity=Intensity.LIGHT)
        _add(conn, prev_mon + datetime.timedelta(days=4), intensity=Intensity.LIGHT)
        # 3 distinct days, 1 strong day — should NOT be complete (needs 2 strong days).
        assert consistency_milestone(conn, reference_date=REF) == 0

    def test_day_is_strong_if_any_activity_is_moderate(self, conn: sqlite3.Connection) -> None:
        """A day with mixed intensities counts as strong if any session is moderate+."""
        prev_mon = REF - datetime.timedelta(weeks=1)
        # Monday: light + moderate → counts as a strong day.
        _add(conn, prev_mon, intensity=Intensity.LIGHT)
        _add(conn, prev_mon, intensity=Intensity.MODERATE)
        # Wednesday and Friday: moderate each.
        _add(conn, prev_mon + datetime.timedelta(days=2), intensity=Intensity.MODERATE)
        _add(conn, prev_mon + datetime.timedelta(days=4), intensity=Intensity.HIGH)
        # 3 distinct days, 3 strong days → complete.
        assert consistency_milestone(conn, reference_date=REF) == 1
