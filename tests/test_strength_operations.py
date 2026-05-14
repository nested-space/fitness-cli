"""Tests for strength exercise CRUD operations."""

import datetime
import sqlite3
from pathlib import Path

import pytest

from fitness_cli.database.connection import get_connection
from fitness_cli.database.models import StrengthExerciseInput
from fitness_cli.operations.strength_operations import (
    add_strength_exercise,
    delete_strength_exercise,
    get_strength_exercise,
    list_strength_exercises,
    update_strength_exercise,
)


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """Fresh database for each test."""
    return get_connection(tmp_path / "test.db")


def _add_exercise(
    conn: sqlite3.Connection,
    *,
    date: datetime.date = datetime.date(2026, 5, 14),
    exercise_name: str = "Plank",
    sets: int | None = 3,
    reps: int | None = None,
    weight_kg: float | None = None,
    duration_seconds: float | None = 60.0,
    notes: str | None = None,
) -> int:
    """Helper: add a strength exercise and return its id."""
    ex = add_strength_exercise(
        conn,
        StrengthExerciseInput(
            date=date,
            exercise_name=exercise_name,
            sets=sets,
            reps=reps,
            weight_kg=weight_kg,
            duration_seconds=duration_seconds,
            notes=notes,
        ),
    )
    assert ex.id is not None
    return ex.id


class TestAddStrengthExercise:
    """Tests for add_strength_exercise()."""

    def test_returns_exercise_with_id(self, conn: sqlite3.Connection) -> None:
        """Returns a StrengthExercise with a non-None id after insertion."""
        ex = add_strength_exercise(
            conn,
            StrengthExerciseInput(
                date=datetime.date(2026, 5, 14),
                exercise_name="Plank",
                sets=3,
                reps=None,
                weight_kg=None,
                duration_seconds=60.0,
                notes=None,
            ),
        )
        assert ex.id is not None
        assert ex.id > 0

    def test_timed_exercise_round_trip(self, conn: sqlite3.Connection) -> None:
        """A timed bodyweight exercise (plank) round-trips with reps/weight as None."""
        ex = add_strength_exercise(
            conn,
            StrengthExerciseInput(
                date=datetime.date(2026, 5, 14),
                exercise_name="Plank",
                sets=3,
                reps=None,
                weight_kg=None,
                duration_seconds=60.0,
                notes=None,
            ),
        )
        assert ex.id is not None
        fetched = get_strength_exercise(conn, ex.id)
        assert fetched is not None
        assert fetched.exercise_name == "Plank"
        assert fetched.sets == 3
        assert fetched.reps is None
        assert fetched.weight_kg is None
        assert fetched.duration_seconds == 60.0
        assert fetched.notes is None

    def test_rep_only_exercise_round_trip(self, conn: sqlite3.Connection) -> None:
        """A rep-only bodyweight exercise (leg raises) round-trips."""
        ex = add_strength_exercise(
            conn,
            StrengthExerciseInput(
                date=datetime.date(2026, 5, 14),
                exercise_name="Leg raises",
                sets=3,
                reps=15,
                weight_kg=None,
                duration_seconds=None,
                notes=None,
            ),
        )
        assert ex.id is not None
        fetched = get_strength_exercise(conn, ex.id)
        assert fetched is not None
        assert fetched.exercise_name == "Leg raises"
        assert fetched.sets == 3
        assert fetched.reps == 15
        assert fetched.weight_kg is None
        assert fetched.duration_seconds is None

    def test_resistance_exercise_round_trip(self, conn: sqlite3.Connection) -> None:
        """A resistance exercise (bench press) round-trips with all numeric fields."""
        ex = add_strength_exercise(
            conn,
            StrengthExerciseInput(
                date=datetime.date(2026, 5, 14),
                exercise_name="Bench press",
                sets=3,
                reps=10,
                weight_kg=50.0,
                duration_seconds=None,
                notes="felt strong",
            ),
        )
        assert ex.id is not None
        fetched = get_strength_exercise(conn, ex.id)
        assert fetched is not None
        assert fetched.exercise_name == "Bench press"
        assert fetched.sets == 3
        assert fetched.reps == 10
        assert fetched.weight_kg == 50.0
        assert fetched.duration_seconds is None
        assert fetched.notes == "felt strong"

    def test_multiple_exercises_get_distinct_ids(self, conn: sqlite3.Connection) -> None:
        """Two separate inserts produce distinct ids."""
        id1 = _add_exercise(conn, exercise_name="Plank")
        id2 = _add_exercise(conn, exercise_name="Leg raises", reps=15, duration_seconds=None)
        assert id1 != id2


class TestListStrengthExercises:
    """Tests for list_strength_exercises()."""

    def test_empty_database(self, conn: sqlite3.Connection) -> None:
        """Returns empty list when no exercises exist."""
        assert list_strength_exercises(conn) == []

    def test_returns_all_without_filter(self, conn: sqlite3.Connection) -> None:
        """Without filter, all exercises are returned."""
        _add_exercise(conn, date=datetime.date(2026, 4, 15))
        _add_exercise(conn, date=datetime.date(2026, 5, 14))
        assert len(list_strength_exercises(conn)) == 2

    def test_date_filter_includes_only_that_day(self, conn: sqlite3.Connection) -> None:
        """Date filter returns only exercises on that exact date."""
        _add_exercise(conn, date=datetime.date(2026, 5, 13))
        _add_exercise(conn, date=datetime.date(2026, 5, 14), exercise_name="Plank")
        _add_exercise(conn, date=datetime.date(2026, 5, 14), exercise_name="Leg raises")
        _add_exercise(conn, date=datetime.date(2026, 5, 15))

        results = list_strength_exercises(conn, date=datetime.date(2026, 5, 14))
        assert len(results) == 2
        assert all(r.date == datetime.date(2026, 5, 14) for r in results)

    def test_month_filter_includes_only_that_month(self, conn: sqlite3.Connection) -> None:
        """Month filter returns only exercises in that calendar month."""
        _add_exercise(conn, date=datetime.date(2026, 4, 30))
        _add_exercise(conn, date=datetime.date(2026, 5, 1))
        _add_exercise(conn, date=datetime.date(2026, 5, 31))
        _add_exercise(conn, date=datetime.date(2026, 6, 1))

        may = datetime.date(2026, 5, 1)
        results = list_strength_exercises(conn, month=may)
        assert len(results) == 2
        assert all(r.date.month == 5 for r in results)

    def test_month_filter_december(self, conn: sqlite3.Connection) -> None:
        """December month filter handles year boundary correctly."""
        _add_exercise(conn, date=datetime.date(2026, 12, 1))
        _add_exercise(conn, date=datetime.date(2027, 1, 1))
        results = list_strength_exercises(conn, month=datetime.date(2026, 12, 1))
        assert len(results) == 1
        assert results[0].date.month == 12

    def test_ordered_by_date_then_id(self, conn: sqlite3.Connection) -> None:
        """Exercises are returned ordered by date ascending, then id ascending."""
        _add_exercise(conn, date=datetime.date(2026, 5, 14), exercise_name="A")
        _add_exercise(conn, date=datetime.date(2026, 5, 14), exercise_name="B")
        _add_exercise(conn, date=datetime.date(2026, 5, 13), exercise_name="C")

        results = list_strength_exercises(conn)
        names = [r.exercise_name for r in results]
        assert names == ["C", "A", "B"]


class TestGetStrengthExercise:
    """Tests for get_strength_exercise()."""

    def test_returns_none_for_missing_id(self, conn: sqlite3.Connection) -> None:
        """Returns None when the id does not exist."""
        assert get_strength_exercise(conn, 1) is None

    def test_returns_exercise_for_valid_id(self, conn: sqlite3.Connection) -> None:
        """Returns the correct StrengthExercise for a valid id."""
        eid = _add_exercise(conn)
        exercise = get_strength_exercise(conn, eid)
        assert exercise is not None
        assert exercise.id == eid


class TestUpdateStrengthExercise:
    """Tests for update_strength_exercise()."""

    def test_update_all_fields_returns_updated_exercise(
        self, conn: sqlite3.Connection
    ) -> None:
        """All supplied fields are written and the refreshed exercise is returned."""
        eid = _add_exercise(conn)
        updated = update_strength_exercise(
            conn,
            eid,
            date=datetime.date(2026, 6, 1),
            exercise_name="Bench press",
            sets=4,
            reps=8,
            weight_kg=60.0,
            duration_seconds=None,
            notes="new PB",
        )
        assert updated is not None
        assert updated.date == datetime.date(2026, 6, 1)
        assert updated.exercise_name == "Bench press"
        assert updated.sets == 4
        assert updated.reps == 8
        assert updated.weight_kg == 60.0
        assert updated.duration_seconds is None
        assert updated.notes == "new PB"

    def test_update_partial_only_changes_specified_fields(
        self, conn: sqlite3.Connection
    ) -> None:
        """Fields not supplied retain their previous values."""
        eid = _add_exercise(
            conn,
            exercise_name="Bench press",
            sets=3,
            reps=10,
            weight_kg=50.0,
            duration_seconds=None,
        )
        updated = update_strength_exercise(conn, eid, weight_kg=55.0)
        assert updated is not None
        assert updated.weight_kg == 55.0
        # Untouched fields preserved
        assert updated.exercise_name == "Bench press"
        assert updated.sets == 3
        assert updated.reps == 10

    def test_update_can_set_nullable_to_none(self, conn: sqlite3.Connection) -> None:
        """Passing a nullable field as None explicitly clears it."""
        eid = _add_exercise(conn, weight_kg=50.0)
        updated = update_strength_exercise(conn, eid, weight_kg=None)
        assert updated is not None
        assert updated.weight_kg is None

    def test_update_no_fields_returns_existing_exercise(
        self, conn: sqlite3.Connection
    ) -> None:
        """No-op call returns the row unchanged."""
        eid = _add_exercise(conn, exercise_name="Plank", duration_seconds=60.0)
        result = update_strength_exercise(conn, eid)
        assert result is not None
        assert result.id == eid
        assert result.exercise_name == "Plank"
        assert result.duration_seconds == 60.0

    def test_update_nonexistent_id_returns_none(self, conn: sqlite3.Connection) -> None:
        """Returns None when no row matches the id."""
        assert update_strength_exercise(conn, 99999, reps=10) is None


class TestDeleteStrengthExercise:
    """Tests for delete_strength_exercise()."""

    def test_returns_true_when_deleted(self, conn: sqlite3.Connection) -> None:
        """Returns True when an existing exercise is deleted."""
        eid = _add_exercise(conn)
        assert delete_strength_exercise(conn, eid) is True

    def test_exercise_no_longer_exists_after_delete(self, conn: sqlite3.Connection) -> None:
        """Deleted exercise cannot be fetched."""
        eid = _add_exercise(conn)
        delete_strength_exercise(conn, eid)
        assert get_strength_exercise(conn, eid) is None

    def test_returns_false_for_nonexistent_id(self, conn: sqlite3.Connection) -> None:
        """Returns False when no exercise with that id exists."""
        assert delete_strength_exercise(conn, 9999) is False
