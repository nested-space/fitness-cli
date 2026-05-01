"""
Domain model dataclasses for the fitness-cli application.

Defines the core value objects used across all layers:
- ActivityType: enum of supported activity categories.
- Intensity: enum of activity intensity levels.
- Activity: immutable record of a single fitness activity.
"""

import datetime
import enum
from dataclasses import dataclass


class ActivityType(enum.StrEnum):
    """Supported activity categories."""

    BIKE_INDOOR = "Bike Indoor"
    ELLIPTICAL = "Elliptical"
    STRENGTH = "Strength"
    TRAIL_RUN = "Trail Run"
    RUN = "Run"
    TREADMILL = "Treadmill"
    WALK = "Walk"
    HIKE = "Hike"
    BIKE = "Bike"


class Intensity(enum.StrEnum):
    """Activity intensity levels, used for calendar colouring and milestone calculations."""

    LIGHT = "light"
    MODERATE = "moderate"
    HIGH = "high"
    PEAK = "peak"


@dataclass(frozen=True)
class ActivityInput:
    """The fields required to record a new activity (no database id).

    Used as the single parameter to add_activity() to keep the function
    signature clean and avoid passing many positional arguments.

    Attributes:
        date: Calendar date on which the activity occurred.
        activity_type: Category of the activity.
        distance_km: Distance covered in kilometres; None for non-distance activities.
        duration_minutes: Duration of the activity in minutes.
        intensity: Self-reported intensity level.
    """

    date: datetime.date
    activity_type: ActivityType
    distance_km: float | None
    duration_minutes: float
    intensity: Intensity


@dataclass(frozen=True)
class Activity:
    """Immutable record of a single fitness activity.

    Attributes:
        id: Database row identifier; None for unsaved activities.
        date: Calendar date on which the activity occurred.
        activity_type: Category of the activity.
        distance_km: Distance covered in kilometres; None for non-distance activities.
        duration_minutes: Duration of the activity in minutes.
        intensity: Self-reported intensity level.
    """

    id: int | None
    date: datetime.date
    activity_type: ActivityType
    distance_km: float | None
    duration_minutes: float
    intensity: Intensity
