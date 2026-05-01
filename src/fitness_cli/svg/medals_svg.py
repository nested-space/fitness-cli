"""
Medal visibility and badge number manipulation for the wallpaper SVG.

Responsibilities:
- Show the coloured medal group and hide the grey placeholder when a
  milestone is earned (and vice versa).
- Set the numeric text of a medal badge to reflect the milestone value.

Element labels referenced here are documented in wallpaper-template-spec.json.
"""

from typing import Literal

from lxml import etree

from fitness_cli.svg.svg_editor import find_by_label, set_style_prop

Medal = Literal["distance", "consistency"]

_COLOURED_LABEL: dict[Medal, str] = {
    "distance": "distance-medal",
    "consistency": "consistency-medal",
}

_GREY_LABEL: dict[Medal, str] = {
    "distance": "distance-medal-grey-out",
    "consistency": "consistency-medal-grey-out",
}

_NUMBER_LABEL: dict[Medal, str] = {
    "distance": "distance-medal-ribbon-top",
    "consistency": "consistency-medal-number",
}


class MedalElementNotFoundError(Exception):
    """Raised when a required medal element cannot be found in the SVG."""


def set_medal_visibility(
    root: etree._Element,
    medal: Medal,
    earned: bool,
) -> None:
    """Show or hide the coloured and grey-out medal groups.

    When earned is True the coloured group is made visible and the grey
    placeholder is hidden. When earned is False the coloured group is hidden
    and the grey placeholder is shown.

    Args:
        root: Root element of the parsed SVG.
        medal: Which medal to update ("distance" or "consistency").
        earned: True if the milestone has been achieved.

    Raises:
        MedalElementNotFoundError: If either required group element is missing.
    """
    coloured = find_by_label(root, _COLOURED_LABEL[medal])
    grey = find_by_label(root, _GREY_LABEL[medal])

    if coloured is None:
        raise MedalElementNotFoundError(
            f"Element '{_COLOURED_LABEL[medal]}' not found in SVG."
        )
    if grey is None:
        raise MedalElementNotFoundError(
            f"Element '{_GREY_LABEL[medal]}' not found in SVG."
        )

    set_style_prop(coloured, "display", "inline" if earned else "none")
    set_style_prop(grey, "display", "none" if earned else "inline")


def set_medal_number(
    root: etree._Element,
    medal: Medal,
    value: int,
) -> None:
    """Set the numeric text displayed on a medal badge.

    Args:
        root: Root element of the parsed SVG.
        medal: Which medal to update ("distance" or "consistency").
        value: The integer value to display on the badge.

    Raises:
        MedalElementNotFoundError: If the badge text element is missing.
    """
    label = _NUMBER_LABEL[medal]
    elem = find_by_label(root, label)
    if elem is None:
        raise MedalElementNotFoundError(f"Element '{label}' not found in SVG.")
    # lxml text nodes are set directly; tspan children (if any) are left intact.
    elem.text = str(value)
