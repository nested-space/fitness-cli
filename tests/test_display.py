"""Tests for the display layer — calendar grid logic and activity table."""

import datetime

from rich.console import Console

from fitness_cli.database.models import Activity, ActivityType, Intensity
from fitness_cli.display.activity_table import build_activity_table
from fitness_cli.display.calendar_display import _month_grid, _to_dow, render_calendar


class TestToDow:
    """Tests for the _to_dow() helper."""

    def test_sunday_returns_1(self) -> None:
        """A Sunday returns 1."""
        # 2026-04-05 is a Sunday
        assert _to_dow(datetime.date(2026, 4, 5)) == 1

    def test_monday_returns_2(self) -> None:
        """A Monday returns 2."""
        assert _to_dow(datetime.date(2026, 4, 6)) == 2

    def test_saturday_returns_7(self) -> None:
        """A Saturday returns 7."""
        assert _to_dow(datetime.date(2026, 4, 4)) == 7


class TestMonthGrid:
    """Tests for the _month_grid() layout function."""

    def test_grid_is_5_rows_of_7(self) -> None:
        """Grid always has exactly 5 rows of 7 columns."""
        grid = _month_grid(2026, 4)
        assert len(grid) == 5
        assert all(len(row) == 7 for row in grid)

    def test_april_2026_day1_is_wednesday(self) -> None:
        """April 1 2026 is a Wednesday (dow=4, col index 3)."""
        grid = _month_grid(2026, 4)
        # April 1 is Wednesday (dow=4 → col index 3)
        assert grid[0][3] == datetime.date(2026, 4, 1)

    def test_april_2026_day1_sunday_slot_is_none(self) -> None:
        """The Sunday slot of week 1 is None for April 2026 (before day 1)."""
        grid = _month_grid(2026, 4)
        assert grid[0][0] is None  # Sunday col

    def test_in_month_dates_are_present(self) -> None:
        """All 30 days of April appear exactly once."""
        grid = _month_grid(2026, 4)
        dates = [cell for row in grid for cell in row if cell is not None]
        assert len(dates) == 30
        assert all(d.month == 4 for d in dates)

    def test_january_2026_starts_on_thursday(self) -> None:
        """January 1 2026 is a Thursday (dow=5, col index 4)."""
        grid = _month_grid(2026, 1)
        assert grid[0][4] == datetime.date(2026, 1, 1)

    def test_february_2026_ends_correctly(self) -> None:
        """February 2026 has 28 days."""
        grid = _month_grid(2026, 2)
        dates = [cell for row in grid for cell in row if cell is not None]
        assert len(dates) == 28


class TestRenderCalendar:
    """Tests for render_calendar() — verifies output via captured console."""

    def _capture(
        self,
        year: int,
        month: int,
        active_days: dict[datetime.date, Intensity] | None = None,
    ) -> str:
        """Render the calendar and return plain text output."""
        console = Console(width=40, no_color=True, highlight=False)
        with console.capture() as capture:
            render_calendar(year, month, active_days or {}, console=console)
        return capture.get()

    def test_header_contains_month_and_year(self) -> None:
        """Output contains the month name and year."""
        output = self._capture(2026, 4)
        assert "APRIL" in output
        assert "2026" in output

    def test_dow_headers_present(self) -> None:
        """Day-of-week headers are present."""
        output = self._capture(2026, 4)
        assert "Su" in output
        assert "Sa" in output

    def test_no_activity_symbol_present(self) -> None:
        """The no-activity circle symbol appears for in-month days."""
        output = self._capture(2026, 4)
        assert "○" in output

    def test_active_day_symbols_present(self) -> None:
        """Activity symbols appear for active days."""
        active: dict[datetime.date, Intensity] = {
            datetime.date(2026, 4, 15): Intensity.MODERATE,
            datetime.date(2026, 4, 20): Intensity.PEAK,
        }
        output = self._capture(2026, 4, active)
        assert "◉" in output
        assert "⬤" in output


class TestBuildActivityTable:
    """Tests for build_activity_table()."""

    def _make_activity(
        self,
        activity_id: int = 1,
        intensity: Intensity = Intensity.MODERATE,
        distance: float | None = 5.0,
    ) -> Activity:
        return Activity(
            id=activity_id,
            date=datetime.date(2026, 4, 15),
            activity_type=ActivityType.RUN,
            distance_km=distance,
            duration_minutes=30.0,
            intensity=intensity,
        )

    def test_table_has_correct_column_count(self) -> None:
        """Table has 6 columns."""
        table = build_activity_table([self._make_activity()])
        assert len(table.columns) == 6

    def test_table_row_count_matches_activities(self) -> None:
        """One row per activity."""
        activities = [self._make_activity(i) for i in range(1, 4)]
        table = build_activity_table(activities)
        assert table.row_count == 3

    def test_empty_activities_produces_empty_table(self) -> None:
        """Empty activity list produces a table with no rows."""
        table = build_activity_table([])
        assert table.row_count == 0

    def test_none_distance_shows_dash(self) -> None:
        """Activities without a distance display '—' in the km column."""
        console = Console(no_color=True, highlight=False)
        table = build_activity_table([self._make_activity(distance=None)])
        with console.capture() as cap:
            console.print(table)
        assert "—" in cap.get()

    def test_custom_title_used(self) -> None:
        """The provided title appears in the rendered table."""
        console = Console(no_color=True, highlight=False)
        table = build_activity_table([], title="My Activities")
        with console.capture() as cap:
            console.print(table)
        assert "My Activities" in cap.get()
