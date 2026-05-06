"""Integration tests for the `fcli wallpaper` commands."""

from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner
from lxml import etree

from fitness_cli.cli import wallpaper_commands
from fitness_cli.cli.wallpaper_commands import wallpaper_group
from fitness_cli.config import settings
from fitness_cli.database.connection import get_connection
from fitness_cli.operations.upload_operations import UploadResult

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


def _success(name: str) -> UploadResult:
    return UploadResult(name=name, success=True, status_code=200, error=None)


def _failure(name: str, status_code: int | None = 500, message: str = "boom") -> UploadResult:
    return UploadResult(name=name, success=False, status_code=status_code, error=message)


@pytest.fixture()
def api_url(monkeypatch: pytest.MonkeyPatch) -> str:
    url = "https://wallpaper.test"
    monkeypatch.setattr(settings, "WALLPAPER_API_URL", url)
    return url


class TestUploadCommand:
    """Tests for `wallpaper upload`."""

    def test_missing_api_url_exits_before_generation(
        self, monkeypatch: pytest.MonkeyPatch, isolated_db: Path  # noqa: ARG002
    ) -> None:
        monkeypatch.setattr(settings, "WALLPAPER_API_URL", None)
        gen_spy = mock.MagicMock()
        monkeypatch.setattr(wallpaper_commands, "_generate_wallpaper_outputs", gen_spy)
        upload_spy = mock.MagicMock()
        monkeypatch.setattr(wallpaper_commands, "upload_svg", upload_spy)

        result = CliRunner().invoke(wallpaper_group, ["upload", "-y"])

        assert result.exit_code == 1
        assert "WALLPAPER_API_URL is not set" in result.stderr
        gen_spy.assert_not_called()
        upload_spy.assert_not_called()

    def test_decline_confirmation_aborts_without_uploading(
        self, monkeypatch: pytest.MonkeyPatch, api_url: str, isolated_db: Path  # noqa: ARG002
    ) -> None:
        del api_url
        upload_spy = mock.MagicMock()
        monkeypatch.setattr(wallpaper_commands, "upload_svg", upload_spy)

        result = CliRunner().invoke(wallpaper_group, ["upload"], input="n\n")

        assert result.exit_code != 0
        upload_spy.assert_not_called()

    def test_yes_flag_skips_prompt_and_uploads_both(
        self, monkeypatch: pytest.MonkeyPatch, api_url: str, isolated_db: Path  # noqa: ARG002
    ) -> None:
        del api_url
        upload_spy = mock.MagicMock(side_effect=lambda name, _path, _url: _success(name))
        monkeypatch.setattr(wallpaper_commands, "upload_svg", upload_spy)

        result = CliRunner().invoke(
            wallpaper_group, ["upload", "--month", "2026-04", "-y"]
        )

        assert result.exit_code == 0, result.output
        assert upload_spy.call_count == 2
        names = [call.args[0] for call in upload_spy.call_args_list]
        assert names == ["fcli-wallpaper", "fcli-lockscreen"]
        assert "✓ fcli-wallpaper uploaded successfully." in result.output
        assert "✓ fcli-lockscreen uploaded successfully." in result.output

    def test_first_upload_failure_skips_second(
        self, monkeypatch: pytest.MonkeyPatch, api_url: str, isolated_db: Path  # noqa: ARG002
    ) -> None:
        del api_url
        upload_spy = mock.MagicMock(
            side_effect=[_failure("fcli-wallpaper", 500, "boom"), _success("fcli-lockscreen")]
        )
        monkeypatch.setattr(wallpaper_commands, "upload_svg", upload_spy)

        result = CliRunner().invoke(
            wallpaper_group, ["upload", "--month", "2026-04", "-y"]
        )

        assert result.exit_code == 1
        assert upload_spy.call_count == 1
        assert "Error uploading fcli-wallpaper" in result.stderr

    def test_generation_failure_skips_upload(
        self, monkeypatch: pytest.MonkeyPatch, api_url: str, isolated_db: Path  # noqa: ARG002
    ) -> None:
        del api_url
        upload_spy = mock.MagicMock()
        monkeypatch.setattr(wallpaper_commands, "upload_svg", upload_spy)
        monkeypatch.setattr(
            wallpaper_commands,
            "_generate_wallpaper_outputs",
            mock.MagicMock(side_effect=FileNotFoundError("template.svg missing")),
        )

        result = CliRunner().invoke(wallpaper_group, ["upload", "-y"])

        assert result.exit_code != 0
        upload_spy.assert_not_called()

    def test_uploaded_svgs_are_from_tempdir(
        self, monkeypatch: pytest.MonkeyPatch, api_url: str, isolated_db: Path  # noqa: ARG002
    ) -> None:
        del api_url
        captured_paths: list[Path] = []

        def fake_upload(name: str, path: Path, _url: str) -> UploadResult:
            captured_paths.append(path)
            return _success(name)

        monkeypatch.setattr(wallpaper_commands, "upload_svg", fake_upload)

        result = CliRunner().invoke(
            wallpaper_group, ["upload", "--month", "2026-04", "-y"]
        )

        assert result.exit_code == 0, result.output
        assert len(captured_paths) == 2
        assert captured_paths[0].name == "output-wallpaper.svg"
        assert captured_paths[1].name == "output-lockscreen.svg"
        # Tempdir is cleaned up on exit, so the files should not exist by now.
        for path in captured_paths:
            assert not path.exists()
