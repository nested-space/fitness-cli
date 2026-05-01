"""
CLI command for generating the monthly SVG wallpaper.

Responsibilities:
- Parse the --month, --template, and --output options.
- Orchestrate the milestone calculations and SVG transformations.
- Write the finished SVG to the output path.
"""

import datetime
import sys
from dataclasses import dataclass
from pathlib import Path

import click

from fitness_cli.config.settings import DEFAULT_TEMPLATE_PATH
from fitness_cli.database.connection import get_connection
from fitness_cli.database.models import Intensity
from fitness_cli.operations.activity_operations import build_active_days, list_activities
from fitness_cli.operations.milestone_operations import (
    consistency_milestone,
    distance_milestone,
)
from fitness_cli.svg.calendar_svg import set_active_days, set_calendar_month, set_month_text
from fitness_cli.svg.medals_svg import set_medal_number, set_medal_visibility
from fitness_cli.svg.svg_editor import load_svg, write_svg


@dataclass(frozen=True)
class _WallpaperParams:
    """Collects computed wallpaper parameters before SVG editing begins.

    Attributes:
        year: Four-digit year of the target month.
        month: Month number (1–12).
        active_days: Mapping of date to highest recorded intensity for that day.
        dist_value: Distance milestone integer value.
        cons_value: Consistency milestone integer value.
    """

    year: int
    month: int
    active_days: dict[datetime.date, Intensity]
    dist_value: int
    cons_value: int


@click.group("wallpaper")
def wallpaper_group() -> None:
    """Commands for generating the monthly SVG wallpaper."""


@wallpaper_group.command("generate")
@click.option(
    "--month",
    "month_str",
    default=None,
    metavar="YYYY-MM",
    help="Month to generate the wallpaper for (default: current month).",
)
@click.option(
    "--template",
    "template_path_str",
    default=None,
    metavar="PATH",
    help="Path to the SVG template (default: wallpaper-template.svg).",
)
@click.option(
    "--output",
    "output_path_str",
    default="output.svg",
    metavar="PATH",
    show_default=True,
    help="Path for the generated SVG.",
)
def generate_cmd(
    month_str: str | None,
    template_path_str: str | None,
    output_path_str: str,
) -> None:
    """Generate the monthly fitness wallpaper SVG."""
    year, month = _resolve_month(month_str)
    template_path = Path(template_path_str) if template_path_str else DEFAULT_TEMPLATE_PATH
    output_path = Path(output_path_str)

    conn = get_connection()
    dist_value = distance_milestone(conn)
    cons_value = consistency_milestone(conn)
    activities = list_activities(conn, month=datetime.date(year, month, 1))
    conn.close()

    params = _WallpaperParams(
        year=year,
        month=month,
        active_days=build_active_days(activities),
        dist_value=dist_value,
        cons_value=cons_value,
    )
    _edit_and_write_svg(template_path, output_path, params)

    dist_status = "earned" if params.dist_value >= 1 else "not earned"
    cons_status = "earned" if params.cons_value >= 1 else "not earned"
    click.echo(f"Wallpaper written to: {output_path}")
    click.echo(f"  Distance milestone : {params.dist_value} km ({dist_status})")
    click.echo(f"  Consistency streak : {params.cons_value} week(s) ({cons_status})")
    click.echo(f"  Active days        : {len(params.active_days)}")


def _resolve_month(month_str: str | None) -> tuple[int, int]:
    """Parse an optional YYYY-MM string into (year, month).

    Args:
        month_str: A string in YYYY-MM format, or None to use the current month.

    Returns:
        A (year, month) tuple.

    Raises:
        SystemExit: If month_str is provided but cannot be parsed.
    """
    if month_str is None:
        today = datetime.date.today()
        return today.year, today.month
    try:
        parsed = datetime.date.fromisoformat(f"{month_str}-01")
        return parsed.year, parsed.month
    except ValueError:
        click.echo(f"Error: invalid month '{month_str}'. Use YYYY-MM format.", err=True)
        sys.exit(1)


def _edit_and_write_svg(
    template_path: Path,
    output_path: Path,
    params: _WallpaperParams,
) -> None:
    """Load the SVG template, apply all edits, and write the result.

    Args:
        template_path: Path to the source SVG template.
        output_path: Destination path for the generated SVG.
        params: Computed wallpaper parameters (month, milestones, active days).

    Raises:
        SystemExit: If the template file cannot be found.
    """
    try:
        tree = load_svg(template_path)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    root = tree.getroot()
    set_calendar_month(root, params.year, params.month)
    set_active_days(root, params.year, params.month, params.active_days)
    set_month_text(root, params.year, params.month)
    set_medal_visibility(root, "distance", earned=params.dist_value >= 1)
    set_medal_visibility(root, "consistency", earned=params.cons_value >= 1)
    set_medal_number(root, "distance", params.dist_value)
    set_medal_number(root, "consistency", params.cons_value)
    write_svg(tree, output_path)
