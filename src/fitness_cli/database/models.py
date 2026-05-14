"""
Domain model dataclasses for the fitness-cli application.

Defines the core value objects used across all layers:
- ActivityType: enum of supported activity categories.
- Intensity: enum of activity intensity levels.
- Activity: immutable record of a single fitness activity.
- StrengthExercise: immutable record of a single strength exercise.
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


@dataclass(frozen=True)
class StrengthExerciseInput:
    """The fields required to record a new strength exercise (no database id).

    Every metric field is optional so the same shape covers bodyweight, timed,
    and resistance exercises:
    - Plank: duration_seconds set; reps and weight None.
    - Leg raises: sets and reps set; weight and duration None.
    - Bench press: sets, reps, and weight_kg set; duration None.

    Attributes:
        date: Calendar date on which the exercise was performed.
        exercise_name: Free-form name of the exercise (e.g. "Plank", "Bench press").
        sets: Number of sets performed; None if not tracked.
        reps: Reps per set; None for timed exercises.
        weight_kg: Resistance weight per set in kg; None for bodyweight exercises.
        duration_seconds: Duration per set in seconds; None for rep-based exercises.
        notes: Free-form notes; None if no notes were recorded.
    """

    date: datetime.date
    exercise_name: str
    sets: int | None
    reps: int | None
    weight_kg: float | None
    duration_seconds: float | None
    notes: str | None


@dataclass(frozen=True)
class StrengthExercise:
    """Immutable record of a single strength exercise.

    Attributes:
        id: Database row identifier; None for unsaved exercises.
        date: Calendar date on which the exercise was performed.
        exercise_name: Free-form name of the exercise.
        sets: Number of sets performed; None if not tracked.
        reps: Reps per set; None for timed exercises.
        weight_kg: Resistance weight per set in kg; None for bodyweight exercises.
        duration_seconds: Duration per set in seconds; None for rep-based exercises.
        notes: Free-form notes; None if no notes were recorded.
    """

    id: int | None
    date: datetime.date
    exercise_name: str
    sets: int | None
    reps: int | None
    weight_kg: float | None
    duration_seconds: float | None
    notes: str | None
