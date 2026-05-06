"""HTTP upload of generated wallpaper SVGs to the wallpaper API.

The single public entry point is :func:`upload_svg`, which POSTs an SVG file
as ``multipart/form-data`` and returns an :class:`UploadResult` describing the
outcome. It never raises — all transport, protocol, and filesystem errors are
caught internally and surfaced via the result object so the caller can
fail-fast deterministically.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request

from fitness_cli.config import settings

_TIMEOUT_SECONDS = 30
_SVG_CONTENT_TYPE = "image/svg+xml"


@dataclass(frozen=True)
class UploadResult:
    """Result of a single image upload attempt.

    Attributes:
        name: The image name posted to the API (e.g. 'fcli-wallpaper').
        success: True if the API returned HTTP 200.
        status_code: The HTTP status code received, or None if the request failed entirely.
        error: Human-readable error message, or None on success.
    """

    name: str
    success: bool
    status_code: int | None
    error: str | None


def upload_svg(name: str, svg_path: Path, api_url: str) -> UploadResult:
    """POST an SVG file to the wallpaper API under the given name.

    Constructs the upload URL from ``api_url`` and the
    :data:`fitness_cli.config.settings.WALLPAPER_API_IMAGE_PATH` template.
    Returns an :class:`UploadResult` regardless of outcome — never raises.

    Args:
        name: The image name to register with the API (e.g. 'fcli-wallpaper').
        svg_path: Absolute path to the SVG file to upload.
        api_url: Base URL of the wallpaper API (e.g. 'https://wallpaper.nestedspace.co.uk').

    Returns:
        UploadResult describing the outcome of the upload attempt.
    """
    url = f"{api_url.rstrip('/')}{settings.WALLPAPER_API_IMAGE_PATH.format(name=name)}"

    try:
        body, content_type = _build_multipart(svg_path, name)
    except OSError as exc:
        return UploadResult(name, False, None, f"Could not read {svg_path}: {exc}")

    req = request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", content_type)
    req.add_header("Accept", "application/json")

    try:
        with request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:  # noqa: S310
            status = int(resp.status)
            if status == 200:
                return UploadResult(name, True, status, None)
            return UploadResult(
                name, False, status, f"Unexpected status {status} from {url}"
            )
    except error.HTTPError as exc:
        return UploadResult(name, False, exc.code, f"HTTP {exc.code} from {url}: {exc.reason}")
    except (error.URLError, TimeoutError) as exc:
        return UploadResult(name, False, None, f"Network error contacting {url}: {exc}")
    except OSError as exc:
        return UploadResult(name, False, None, f"OS error during upload to {url}: {exc}")


def _build_multipart(svg_path: Path, name: str) -> tuple[bytes, str]:
    """Build a multipart/form-data body containing the SVG file as field 'file'."""
    boundary = f"----fcli-{uuid.uuid4().hex}"
    filename = f"{name}.svg"
    data = svg_path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {_SVG_CONTENT_TYPE}\r\n\r\n".encode(),
        data,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"
