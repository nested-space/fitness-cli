"""
Shared lxml helpers for SVG loading, writing, and element manipulation.

Responsibilities:
- Load and write SVG files via lxml, preserving the original encoding and
  XML declaration.
- Locate SVG elements by their inkscape:label attribute.
- Mutate individual CSS properties within an element's inline style string
  without touching unrelated properties.

All other SVG modules depend on this module; none of them import lxml directly.
"""

import re
from pathlib import Path

from lxml import etree

_INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
#: The fully-qualified inkscape:label attribute name. Exported for use by other SVG modules.
INKSCAPE_LABEL_ATTR = f"{{{_INKSCAPE_NS}}}label"
_LABEL_ATTR = INKSCAPE_LABEL_ATTR


def load_svg(path: Path) -> etree._ElementTree:
    """Parse an SVG file and return its element tree.

    Args:
        path: Filesystem path to the SVG file.

    Returns:
        The parsed lxml element tree.

    Raises:
        FileNotFoundError: If the file does not exist.
        lxml.etree.XMLSyntaxError: If the file is not valid XML.
    """
    if not path.exists():
        raise FileNotFoundError(f"SVG template not found: {path}")
    parser = etree.XMLParser(remove_blank_text=False)
    return etree.parse(str(path), parser)


def write_svg(tree: etree._ElementTree, path: Path) -> None:
    """Write an lxml element tree to an SVG file.

    Produces a file with an XML declaration, UTF-8 encoding, and
    standalone=yes — matching Inkscape's export format.

    Args:
        tree: The element tree to serialise.
        path: Destination filesystem path. Parent directories must exist.
    """
    tree.write(
        str(path),
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
        pretty_print=False,
    )


def find_by_label(
    root: etree._Element,
    label: str,
) -> etree._Element | None:
    """Find the first element whose inkscape:label (or plain label) matches.

    Searches the full element tree rooted at root. Checks the namespaced
    inkscape:label attribute first, then falls back to a plain label attribute.

    Args:
        root: The root element to search from.
        label: The exact label string to match.

    Returns:
        The first matching element, or None if not found.
    """
    for elem in root.iter():
        if elem.get(_LABEL_ATTR) == label or elem.get("label") == label:
            return elem
    return None


def set_style_prop(element: etree._Element, prop: str, value: str) -> None:
    """Set a single CSS property in an element's inline style attribute.

    If the property already exists in the style string it is updated in place.
    If it is absent it is appended. Other properties are not disturbed.

    Args:
        element: The SVG element whose style attribute will be modified.
        prop: The CSS property name (e.g. "display", "fill", "fill-opacity").
        value: The new value for the property (e.g. "none", "#f7bb01", "1").
    """
    style = element.get("style", "")
    pattern = re.compile(
        r"(?<![a-z-])" + re.escape(prop) + r"\s*:[^;]*",
        re.IGNORECASE,
    )
    replacement = f"{prop}:{value}"
    if pattern.search(style):
        new_style = pattern.sub(replacement, style)
    else:
        new_style = style.rstrip(";") + f";{replacement}" if style else replacement
    element.set("style", new_style)
