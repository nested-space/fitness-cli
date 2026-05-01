"""Tests for activity CRUD operations."""

import datetime
import sqlite3
from pathlib import Path

import pytest

from fitness_cli.database.connection import get_connection
from fitness_cli.database.models import Activity, ActivityInput, ActivityType, Intensity
from fitness_cli.operations.activity_operations import (
    add_activity,
    build_active_days,
    delete_activity,
    get_activity,
    list_activities,
    list_last_n_activities,
)


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """Fresh in-memory-style database for each test."""
    return get_connection(tmp_path / "test.db")


def _add_run(
    conn: sqlite3.Connection,
    date: datetime.date = datetime.date(2026, 4, 15),
    distance: float = 8.2,
    intensity: Intensity = Intensity.MODERATE,
) -> int:
    """Helper: add a Run activity and return its id."""
    act = add_activity(
        conn,
        ActivityInput(
            date=date,
            activity_type=ActivityType.RUN,
            distance_km=distance,
            duration_minutes=45.0,
            intensity=intensity,
        ),
    )
    assert act.id is not None
    return act.id


class TestAddActivity:
    """Tests for add_activity()."""

    def test_returns_activity_with_id(self, conn: sqlite3.Connection) -> None:
        """Returns an Activity with a non-None id after insertion."""
        act = add_activity(
            conn,
            ActivityInput(
                date=datetime.date(2026, 4, 15),
                activity_type=ActivityType.RUN,
                distance_km=8.2,
                duration_minutes=45.0,
                intensity=Intensity.MODERATE,
            ),
        )
        assert act.id is not None
        assert act.id > 0

    def test_fields_round_trip(self, conn: sqlite3.Connection) -> None:
        """All fields survive the insert → fetch round trip."""
        act = add_activity(
            conn,
            ActivityInput(
                date=datetime.date(2026, 4, 15),
                activity_type=ActivityType.STRENGTH,
                distance_km=None,
                duration_minutes=60.0,
                intensity=Intensity.HIGH,
            ),
        )
        assert act.id is not None
        fetched = get_activity(conn, act.id)
        assert fetched is not None
        assert fetched.date == datetime.date(2026, 4, 15)
        assert fetched.activity_type == ActivityType.STRENGTH
        assert fetched.distance_km is None
        assert fetched.duration_minutes == 60.0
        assert fetched.intensity == Intensity.HIGH

    def test_multiple_activities_get_distinct_ids(self, conn: sqlite3.Connection) -> None:
        """Two separate inserts produce distinct ids."""
        id1 = _add_run(conn, datetime.date(2026, 4, 1))
        id2 = _add_run(conn, datetime.date(2026, 4, 2))
        assert id1 != id2


class TestListActivities:
    """Tests for list_activities()."""

    def test_empty_database(self, conn: sqlite3.Connection) -> None:
        """Returns empty list when no activities exist."""
        assert list_activities(conn) == []

    def test_returns_all_without_filter(self, conn: sqlite3.Connection) -> None:
        """Without month filter, all activities are returned."""
        _add_run(conn, datetime.date(2026, 3, 10))
        _add_run(conn, datetime.date(2026, 4, 15))
        assert len(list_activities(conn)) == 2

    def test_month_filter_includes_only_that_month(self, conn: sqlite3.Connection) -> None:
        """Month filter returns only activities in that calendar month."""
        _add_run(conn, datetime.date(2026, 3, 31))
        _add_run(conn, datetime.date(2026, 4, 1))
        _add_run(conn, datetime.date(2026, 4, 30))
        _add_run(conn, datetime.date(2026, 5, 1))

        april = datetime.date(2026, 4, 1)
        results = list_activities(conn, month=april)
        assert len(results) == 2
        assert all(r.date.month == 4 for r in results)

    def test_month_filter_december(self, conn: sqlite3.Connection) -> None:
        """December month filter handles year boundary correctly."""
        _add_run(conn, datetime.date(2026, 12, 1))
        _add_run(conn, datetime.date(2027, 1, 1))
        results = list_activities(conn, month=datetime.date(2026, 12, 1))
        assert len(results) == 1
        assert results[0].date.month == 12

    def test_ordered_by_date_ascending(self, conn: sqlite3.Connection) -> None:
        """Activities are returned ordered by date ascending."""
        _add_run(conn, datetime.date(2026, 4, 20))
        _add_run(conn, datetime.date(2026, 4, 5))
        _add_run(conn, datetime.date(2026, 4, 12))
        results = list_activities(conn)
        dates = [r.date for r in results]
        assert dates == sorted(dates)


class TestDeleteActivity:
    """Tests for delete_activity()."""

    def test_returns_true_when_deleted(self, conn: sqlite3.Connection) -> None:
        """Returns True when an existing activity is deleted."""
        aid = _add_run(conn)
        assert delete_activity(conn, aid) is True

    def test_activity_no_longer_exists_after_delete(self, conn: sqlite3.Connection) -> None:
        """Deleted activity cannot be fetched."""
        aid = _add_run(conn)
        delete_activity(conn, aid)
        assert get_activity(conn, aid) is None

    def test_returns_false_for_nonexistent_id(self, conn: sqlite3.Connection) -> None:
        """Returns False when no activity with that id exists."""
        assert delete_activity(conn, 9999) is False


class TestGetActivity:
    """Tests for get_activity()."""

    def test_returns_none_for_missing_id(self, conn: sqlite3.Connection) -> None:
        """Returns None when the id does not exist."""
        assert get_activity(conn, 1) is None

    def test_returns_activity_for_valid_id(self, conn: sqlite3.Connection) -> None:
        """Returns the correct Activity for a valid id."""
        aid = _add_run(conn)
        activity = get_activity(conn, aid)
        assert activity is not None
        assert activity.id == aid


class TestListLastNActivities:
    """Tests for list_last_n_activities()."""

    def test_empty_database_returns_empty(self, conn: sqlite3.Connection) -> None:
        """Returns empty list when no activities exist."""
        assert list_last_n_activities(conn, 5) == []

    def test_returns_newest_first(self, conn: sqlite3.Connection) -> None:
        """Activities are returned newest-first."""
        _add_run(conn, datetime.date(2026, 4, 1))
        _add_run(conn, datetime.date(2026, 4, 20))
        _add_run(conn, datetime.date(2026, 4, 10))
        results = list_last_n_activities(conn, 3)
        dates = [r.date for r in results]
        assert dates == sorted(dates, reverse=True)

    def test_limits_to_n(self, conn: sqlite3.Connection) -> None:
        """Returns at most n activities even when more exist."""
        for day in range(1, 11):
            _add_run(conn, datetime.date(2026, 4, day))
        assert len(list_last_n_activities(conn, 3)) == 3

    def test_returns_all_when_fewer_than_n(self, conn: sqlite3.Connection) -> None:
        """Returns all activities when database has fewer than n rows."""
        _add_run(conn, datetime.date(2026, 4, 1))
        _add_run(conn, datetime.date(2026, 4, 2))
        assert len(list_last_n_activities(conn, 10)) == 2

    def test_invalid_count_raises(self, conn: sqlite3.Connection) -> None:
        """Raises ValueError for count < 1."""
        with pytest.raises(ValueError):
            list_last_n_activities(conn, 0)


class TestBuildActiveDays:
    """Tests for build_active_days()."""

    def _make_activity(
        self,
        date: datetime.date,
        intensity: Intensity,
    ) -> Activity:
        return Activity(
            id=1,
            date=date,
            activity_type=ActivityType.RUN,
            distance_km=None,
            duration_minutes=30.0,
            intensity=intensity,
        )

    def test_empty_list_returns_empty_dict(self) -> None:
        """Empty input produces an empty mapping."""
        assert build_active_days([]) == {}

    def test_single_activity_mapped(self) -> None:
        """A single activity appears in the result with its intensity."""
        date = datetime.date(2026, 4, 15)
        result = build_active_days([self._make_activity(date, Intensity.MODERATE)])
        assert result == {date: Intensity.MODERATE}

    def test_highest_intensity_wins_same_day(self) -> None:
        """When multiple activities share a date the highest intensity is kept."""
        date = datetime.date(2026, 4, 15)
        acts = [
            self._make_activity(date, Intensity.LIGHT),
            self._make_activity(date, Intensity.HIGH),
            self._make_activity(date, Intensity.MODERATE),
        ]
        result = build_active_days(acts)
        assert result[date] == Intensity.HIGH

    def test_peak_beats_high(self) -> None:
        """PEAK intensity ranks above HIGH."""
        date = datetime.date(2026, 4, 20)
        acts = [
            self._make_activity(date, Intensity.HIGH),
            self._make_activity(date, Intensity.PEAK),
        ]
        result = build_active_days(acts)
        assert result[date] == Intensity.PEAK

    def test_different_dates_are_independent(self) -> None:
        """Activities on different dates produce separate entries."""
        d1 = datetime.date(2026, 4, 1)
        d2 = datetime.date(2026, 4, 2)
        acts = [
            self._make_activity(d1, Intensity.LIGHT),
            self._make_activity(d2, Intensity.HIGH),
        ]
        result = build_active_days(acts)
        assert result[d1] == Intensity.LIGHT
        assert result[d2] == Intensity.HIGH
