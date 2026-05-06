"""
Config settings for the fitness-cli application.

Centralises all configurable constants — paths, colours, and thresholds —
so that no other module needs to hard-code values.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

#: Default path for the SQLite database file.
DEFAULT_DB_PATH: Path = Path.home() / ".fitness-cli" / "fitness.db"

#: Default path for the SVG wallpaper template.
DEFAULT_TEMPLATE_PATH: Path = Path(__file__).parents[3] / "wallpaper-template.svg"

# ---------------------------------------------------------------------------
# Milestone thresholds
# ---------------------------------------------------------------------------

#: Activity types that count towards the distance milestone (running only).
DISTANCE_ACTIVITY_TYPES: tuple[str, ...] = ("Run", "Treadmill")

# ---------------------------------------------------------------------------
# Calendar day fill colours
# ---------------------------------------------------------------------------

#: Fill colour for a day with light-intensity activity.
COLOUR_LIGHT_ACTIVITY: str = "#fef3c7"

#: Fill colour for a day with moderate or high intensity activity.
COLOUR_ACTIVE_ACTIVITY: str = "#f7bb01"

#: Default weekday fill (no activity).
COLOUR_WEEKDAY_DEFAULT: str = "#242424"

#: Default weekend fill (no activity).
COLOUR_WEEKEND_DEFAULT: str = "#000000"

#: Default weekend fill-opacity (no activity).
OPACITY_WEEKEND_DEFAULT: str = "0.116777"

# ---------------------------------------------------------------------------
# Wallpaper API
# ---------------------------------------------------------------------------

#: Base URL of the wallpaper API. Read from the WALLPAPER_API_URL env var; the
#: upload command checks for None at runtime and fails fast if unset.
WALLPAPER_API_URL: str | None = os.environ.get("WALLPAPER_API_URL")

#: Image upload path template, joined onto WALLPAPER_API_URL. The {name}
#: placeholder is the resource identifier the API will store the image under.
WALLPAPER_API_IMAGE_PATH: str = "/api/v1/i/{name}"
