"""Tests for title group visibility manipulation."""

import pytest
from lxml import etree

from fitness_cli.svg.title_svg import TitleGroupNotFoundError, set_title_visibility

_LABEL_NS = "http://www.inkscape.org/namespaces/inkscape"


def _make_svg_with_title() -> etree._Element:
    """Build a minimal SVG with a single <g inkscape:label='title'>."""
    root = etree.Element("svg")
    g = etree.SubElement(root, "g")
    g.set(f"{{{_LABEL_NS}}}label", "title")
    g.set("style", "display:inline")
    return root


class TestSetTitleVisibility:
    """Tests for set_title_visibility()."""

    def test_visible_sets_inline(self) -> None:
        """visible=True forces display:inline on the title group."""
        root = _make_svg_with_title()
        set_title_visibility(root, visible=True)
        title = root.find("g")
        assert title is not None
        assert "display:inline" in title.get("style", "")

    def test_hidden_sets_none(self) -> None:
        """visible=False forces display:none on the title group."""
        root = _make_svg_with_title()
        set_title_visibility(root, visible=False)
        title = root.find("g")
        assert title is not None
        assert "display:none" in title.get("style", "")

    def test_missing_group_raises(self) -> None:
        """Raises TitleGroupNotFoundError when the title group is absent."""
        root = etree.Element("svg")
        with pytest.raises(TitleGroupNotFoundError):
            set_title_visibility(root, visible=False)
