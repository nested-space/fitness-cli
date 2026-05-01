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
        """Activities in the current week do not count towards the milestone."""
        # Lots of activity this week — should not affect the count.
        for day_offset in range(7):
            _add(conn, REF + datetime.timedelta(days=day_offset), intensity=Intensity.HIGH)
        assert consistency_milestone(conn, reference_date=REF) == 0
