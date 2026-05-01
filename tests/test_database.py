"""Tests for the database connection and schema creation."""

import dataclasses
import datetime
import sqlite3
from pathlib import Path

import pytest

from fitness_cli.database.connection import get_connection
from fitness_cli.database.models import Activity, ActivityType, Intensity


@pytest.fixture()
def tmp_db(tmp_path: Path) -> sqlite3.Connection:
    """Return a connection to a fresh temporary database."""
    return get_connection(tmp_path / "test.db")


class TestGetConnection:
    """Tests for get_connection()."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """Database file is created when it does not exist."""
        db_path = tmp_path / "sub" / "fitness.db"
        conn = get_connection(db_path)
        conn.close()
        assert db_path.exists()

    def test_returns_connection(self, tmp_path: Path) -> None:
        """get_connection() returns a sqlite3.Connection."""
        conn = get_connection(tmp_path / "fitness.db")
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_row_factory_set(self, tmp_db: sqlite3.Connection) -> None:
        """row_factory is sqlite3.Row for column-name access."""
        assert tmp_db.row_factory is sqlite3.Row
        tmp_db.close()

    def test_activities_table_exists(self, tmp_db: sqlite3.Connection) -> None:
        """The activities table is created by get_connection()."""
        cur = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='activities';"
        )
        assert cur.fetchone() is not None
        tmp_db.close()

    def test_idempotent(self, tmp_path: Path) -> None:
        """Calling get_connection() twice on the same path does not raise."""
        db_path = tmp_path / "fitness.db"
        conn1 = get_connection(db_path)
        conn1.close()
        conn2 = get_connection(db_path)
        conn2.close()


class TestModels:
    """Tests for the domain model dataclasses."""

    def test_activity_is_frozen(self) -> None:
        """Activity is immutable."""
        activity = Activity(
            id=None,
            date=datetime.date(2026, 4, 15),
            activity_type=ActivityType.RUN,
            distance_km=8.2,
            duration_minutes=45.0,
            intensity=Intensity.MODERATE,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            activity.id = 1  # type: ignore[misc]

    def test_activity_type_values(self) -> None:
        """ActivityType enum values match expected strings."""
        assert ActivityType.RUN.value == "Run"
        assert ActivityType.BIKE_INDOOR.value == "Bike Indoor"

    def test_intensity_values(self) -> None:
        """Intensity enum values match expected strings."""
        assert Intensity.LIGHT.value == "light"
        assert Intensity.MODERATE.value == "moderate"
        assert Intensity.HIGH.value == "high"

    def test_activity_distance_optional(self) -> None:
        """distance_km may be None for non-distance activities."""
        activity = Activity(
            id=1,
            date=datetime.date(2026, 4, 10),
            activity_type=ActivityType.STRENGTH,
            distance_km=None,
            duration_minutes=60.0,
            intensity=Intensity.HIGH,
        )
        assert activity.distance_km is None
