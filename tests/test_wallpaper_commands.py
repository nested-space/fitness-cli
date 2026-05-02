"""Integration tests for the `fcli wallpaper generate` command."""

from pathlib import Path

import pytest
from click.testing import CliRunner
from lxml import etree

from fitness_cli.cli import wallpaper_commands
from fitness_cli.cli.wallpaper_commands import wallpaper_group
from fitness_cli.database.connection import get_connection

_LABEL_NS = "http://www.inkscape.org/namespaces/inkscape"


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect wallpaper_commands.get_connection at a fresh tmp database."""
    db_path = tmp_path / "fitness.db"
    get_connection(db_path).close()
    monkeypatch.setattr(
        wallpaper_commands,
        "get_connection",
        lambda: get_connection(db_path),
    )
    return db_path


def _find_title_style(svg_path: Path) -> str:
    """Return the style string of the <g inkscape:label='title'> group."""
    tree = etree.parse(str(svg_path))
    for el in tree.getroot().iter():
        if el.get(f"{{{_LABEL_NS}}}label") == "title":
            return el.get("style", "")
    raise AssertionError(f"No title group in {svg_path}")


class TestGenerateCommand:
    """Tests for `wallpaper generate` end-to-end."""

    def test_writes_four_outputs(self, tmp_path: Path, isolated_db: Path) -> None:
        """Default invocation writes wallpaper + lockscreen as both SVG and JPG."""
        base = tmp_path / "morning"
        runner = CliRunner()
        result = runner.invoke(
            wallpaper_group,
            ["generate", "--month", "2026-04", "--output", str(base)],
        )
        assert result.exit_code == 0, result.output

        wallpaper_svg = tmp_path / "morning-wallpaper.svg"
        wallpaper_jpg = tmp_path / "morning-wallpaper.jpg"
        lockscreen_svg = tmp_path / "morning-lockscreen.svg"
        lockscreen_jpg = tmp_path / "morning-lockscreen.jpg"
        for path in (wallpaper_svg, wallpaper_jpg, lockscreen_svg, lockscreen_jpg):
            assert path.exists(), f"missing output: {path}"
            assert path.stat().st_size > 0, f"empty output: {path}"

        assert wallpaper_jpg.read_bytes()[:3] == b"\xff\xd8\xff"
        assert lockscreen_jpg.read_bytes()[:3] == b"\xff\xd8\xff"

    def test_title_visibility_differs(self, tmp_path: Path, isolated_db: Path) -> None:
        """Wallpaper variant shows the title; lockscreen variant hides it."""
        base = tmp_path / "out"
        runner = CliRunner()
        result = runner.invoke(
            wallpaper_group,
            ["generate", "--month", "2026-04", "--output", str(base)],
        )
        assert result.exit_code == 0, result.output

        wallpaper_style = _find_title_style(tmp_path / "out-wallpaper.svg")
        lockscreen_style = _find_title_style(tmp_path / "out-lockscreen.svg")
        assert "display:inline" in wallpaper_style
        assert "display:none" in lockscreen_style
