"""
Title group visibility manipulation for the wallpaper SVG.

The `title` group holds the operation title text (title-1 / title-2 / title-3).
Hiding it produces the lockscreen variant of the wallpaper, where device-drawn
clock and notifications occupy that region.
"""

from lxml import etree

from fitness_cli.svg.svg_editor import find_by_label, set_style_prop

_TITLE_LABEL = "title"


class TitleGroupNotFoundError(Exception):
    """Raised when the title group cannot be found in the SVG."""


def set_title_visibility(root: etree._Element, visible: bool) -> None:
    """Show or hide the title group.

    Args:
        root: Root element of the parsed SVG.
        visible: True for the wallpaper variant, False for the lockscreen variant.

    Raises:
        TitleGroupNotFoundError: If the title group is missing from the SVG.
    """
    elem = find_by_label(root, _TITLE_LABEL)
    if elem is None:
        raise TitleGroupNotFoundError(f"Element '{_TITLE_LABEL}' not found in SVG.")
    set_style_prop(elem, "display", "inline" if visible else "none")
