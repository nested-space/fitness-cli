"""Unit tests for upload_operations.upload_svg.

The HTTP call is patched at ``fitness_cli.operations.upload_operations.request.urlopen``
so no real network requests are made.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest import mock
from urllib import error, request

import pytest

from fitness_cli.operations.upload_operations import UploadResult, upload_svg

_API_URL = "https://wallpaper.test"


@pytest.fixture()
def svg_file(tmp_path: Path) -> Path:
    path = tmp_path / "input.svg"
    path.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"/>')
    return path


def _fake_response(status: int) -> mock.MagicMock:
    """Build a context-manager mock matching urllib's HTTPResponse surface."""
    resp = mock.MagicMock()
    resp.status = status
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


class TestUploadSvg:
    def test_success_returns_success_result(self, svg_file: Path) -> None:
        with mock.patch(
            "fitness_cli.operations.upload_operations.request.urlopen",
            return_value=_fake_response(200),
        ):
            result = upload_svg("fcli-wallpaper", svg_file, _API_URL)

        assert result == UploadResult(
            name="fcli-wallpaper", success=True, status_code=200, error=None
        )

    def test_http_422_returns_failure_with_status(self, svg_file: Path) -> None:
        http_err = error.HTTPError(
            url=f"{_API_URL}/api/v1/i/fcli-wallpaper",
            code=422,
            msg="Unprocessable Entity",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b""),
        )
        with mock.patch(
            "fitness_cli.operations.upload_operations.request.urlopen",
            side_effect=http_err,
        ):
            result = upload_svg("fcli-wallpaper", svg_file, _API_URL)

        assert result.success is False
        assert result.status_code == 422
        assert result.error
        assert "422" in result.error

    def test_connection_error_returns_failure_without_status(self, svg_file: Path) -> None:
        with mock.patch(
            "fitness_cli.operations.upload_operations.request.urlopen",
            side_effect=error.URLError("connection refused"),
        ):
            result = upload_svg("fcli-wallpaper", svg_file, _API_URL)

        assert result.success is False
        assert result.status_code is None
        assert result.error
        assert "Network error" in result.error

    def test_timeout_returns_failure_without_status(self, svg_file: Path) -> None:
        with mock.patch(
            "fitness_cli.operations.upload_operations.request.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            result = upload_svg("fcli-wallpaper", svg_file, _API_URL)

        assert result.success is False
        assert result.status_code is None
        assert result.error

    def test_unexpected_status_is_failure(self, svg_file: Path) -> None:
        with mock.patch(
            "fitness_cli.operations.upload_operations.request.urlopen",
            return_value=_fake_response(204),
        ):
            result = upload_svg("fcli-wallpaper", svg_file, _API_URL)

        assert result.success is False
        assert result.status_code == 204

    def test_request_uses_post_with_multipart_body(self, svg_file: Path) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(req: request.Request, timeout: float = 0) -> mock.MagicMock:  # noqa: ARG001
            captured["method"] = req.get_method()
            captured["url"] = req.full_url
            captured["content_type"] = req.get_header("Content-type")
            captured["body"] = req.data
            return _fake_response(200)

        with mock.patch(
            "fitness_cli.operations.upload_operations.request.urlopen",
            side_effect=fake_urlopen,
        ):
            result = upload_svg("fcli-wallpaper", svg_file, _API_URL)

        assert result.success is True
        assert captured["method"] == "POST"
        assert captured["url"] == f"{_API_URL}/api/v1/i/fcli-wallpaper"
        assert captured["content_type"].startswith("multipart/form-data; boundary=")
        body: bytes = captured["body"]
        assert b'name="file"' in body
        assert b'filename="fcli-wallpaper.svg"' in body
        assert b"Content-Type: image/svg+xml" in body
        assert svg_file.read_bytes() in body

    def test_trailing_slash_on_api_url_is_handled(self, svg_file: Path) -> None:
        captured_url: dict[str, str] = {}

        def fake_urlopen(req: request.Request, timeout: float = 0) -> mock.MagicMock:  # noqa: ARG001
            captured_url["url"] = req.full_url
            return _fake_response(200)

        with mock.patch(
            "fitness_cli.operations.upload_operations.request.urlopen",
            side_effect=fake_urlopen,
        ):
            upload_svg("fcli-wallpaper", svg_file, _API_URL + "/")

        assert captured_url["url"] == f"{_API_URL}/api/v1/i/fcli-wallpaper"

    def test_missing_svg_file_returns_failure(self, tmp_path: Path) -> None:
        result = upload_svg("fcli-wallpaper", tmp_path / "missing.svg", _API_URL)

        assert result.success is False
        assert result.status_code is None
        assert result.error
        assert "Could not read" in result.error
