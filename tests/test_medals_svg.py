"""Tests for medal SVG visibility and badge number manipulation."""

import pytest
from lxml import etree

from fitness_cli.svg.medals_svg import (
    MedalElementNotFoundError,
    set_medal_number,
    set_medal_visibility,
)


def _make_svg(labels: list[str]) -> etree._Element:
    """Build a minimal SVG with one <g> element per label."""
    NS = "http://www.inkscape.org/namespaces/inkscape"
    root = etree.Element("svg")
    for label in labels:
        g = etree.SubElement(root, "g")
        g.set(f"{{{NS}}}label", label)
        g.set("style", "display:inline")
    return root


_DISTANCE_LABELS = [
    "distance-medal",
    "distance-medal-grey-out",
    "distance-medal-ribbon-top",
]
_CONSISTENCY_LABELS = [
    "consistency-medal",
    "consistency-medal-grey-out",
    "consistency-medal-number",
]


@pytest.fixture()
def distance_svg() -> etree._Element:
    """SVG root with the distance medal elements."""
    return _make_svg(_DISTANCE_LABELS)


@pytest.fixture()
def consistency_svg() -> etree._Element:
    """SVG root with the consistency medal elements."""
    return _make_svg(_CONSISTENCY_LABELS)


class TestSetMedalVisibility:
    """Tests for set_medal_visibility()."""

    def test_earned_shows_coloured_hides_grey(self, distance_svg: etree._Element) -> None:
        """When earned, coloured group is inline and grey-out is none."""
        set_medal_visibility(distance_svg, "distance", earned=True)
        NS = "http://www.inkscape.org/namespaces/inkscape"
        for elem in distance_svg.iter():
            label = elem.get(f"{{{NS}}}label", "")
            style = elem.get("style", "")
            if label == "distance-medal":
                assert "display:inline" in style
            elif label == "distance-medal-grey-out":
                assert "display:none" in style

    def test_not_earned_hides_coloured_shows_grey(self, distance_svg: etree._Element) -> None:
        """When not earned, coloured group is none and grey-out is inline."""
        set_medal_visibility(distance_svg, "distance", earned=False)
        NS = "http://www.inkscape.org/namespaces/inkscape"
        for elem in distance_svg.iter():
            label = elem.get(f"{{{NS}}}label", "")
            style = elem.get("style", "")
            if label == "distance-medal":
                assert "display:none" in style
            elif label == "distance-medal-grey-out":
                assert "display:inline" in style

    def test_consistency_medal(self, consistency_svg: etree._Element) -> None:
        """Works for the consistency medal pair."""
        set_medal_visibility(consistency_svg, "consistency", earned=True)
        NS = "http://www.inkscape.org/namespaces/inkscape"
        for elem in consistency_svg.iter():
            label = elem.get(f"{{{NS}}}label", "")
            if label == "consistency-medal":
                assert "display:inline" in elem.get("style", "")
            elif label == "consistency-medal-grey-out":
                assert "display:none" in elem.get("style", "")

    def test_missing_coloured_group_raises(self) -> None:
        """Raises MedalElementNotFoundError if the coloured group is absent."""
        root = _make_svg(["distance-medal-grey-out"])
        with pytest.raises(MedalElementNotFoundError):
            set_medal_visibility(root, "distance", earned=True)

    def test_missing_grey_group_raises(self) -> None:
        """Raises MedalElementNotFoundError if the grey placeholder is absent."""
        root = _make_svg(["distance-medal"])
        with pytest.raises(MedalElementNotFoundError):
            set_medal_visibility(root, "distance", earned=True)


class TestSetMedalNumber:
    """Tests for set_medal_number()."""

    def test_sets_text_content(self, distance_svg: etree._Element) -> None:
        """Badge text element gets the correct string value."""
        set_medal_number(distance_svg, "distance", 10)
        NS = "http://www.inkscape.org/namespaces/inkscape"
        for elem in distance_svg.iter():
            if elem.get(f"{{{NS}}}label") == "distance-medal-ribbon-top":
                assert elem.text == "10"

    def test_sets_consistency_number(self, consistency_svg: etree._Element) -> None:
        """Works for the consistency badge."""
        set_medal_number(consistency_svg, "consistency", 4)
        NS = "http://www.inkscape.org/namespaces/inkscape"
        for elem in consistency_svg.iter():
            if elem.get(f"{{{NS}}}label") == "consistency-medal-number":
                assert elem.text == "4"

    def test_missing_number_element_raises(self) -> None:
        """Raises MedalElementNotFoundError if the number text element is absent."""
        root = _make_svg(["distance-medal", "distance-medal-grey-out"])
        with pytest.raises(MedalElementNotFoundError):
            set_medal_number(root, "distance", 5)
