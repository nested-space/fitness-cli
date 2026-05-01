"""
Fitness Wallpaper CLI.

Entry point for the fitness-wallpaper command-line tool.
"""

import click

from fitness_cli.cli.activity_commands import activity_group
from fitness_cli.cli.wallpaper_commands import wallpaper_group


@click.group()
def main() -> None:
    """Fitness Wallpaper — record activities and generate monthly SVG wallpapers."""


main.add_command(activity_group)
main.add_command(wallpaper_group)
