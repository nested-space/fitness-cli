"""Tests for SVG-to-JPEG rasterisation."""

from pathlib import Path

from lxml import etree

from fitness_cli.svg.raster import svg_tree_to_jpg


def _make_minimal_svg_tree() -> etree._ElementTree:
    """Build a tiny but valid SVG element tree."""
    root = etree.Element("{http://www.w3.org/2000/svg}svg", nsmap={None: "http://www.w3.org/2000/svg"})
    root.set("width", "16")
    root.set("height", "16")
    root.set("viewBox", "0 0 16 16")
    rect = etree.SubElement(root, "{http://www.w3.org/2000/svg}rect")
    rect.set("width", "16")
    rect.set("height", "16")
    rect.set("fill", "#f7bb01")
    return etree.ElementTree(root)


def test_writes_valid_jpeg(tmp_path: Path) -> None:
    """svg_tree_to_jpg produces a non-empty file with the JPEG SOI marker."""
    out = tmp_path / "out.jpg"
    svg_tree_to_jpg(_make_minimal_svg_tree(), out)
    assert out.exists()
    data = out.read_bytes()
    assert len(data) > 0
    assert data[:3] == b"\xff\xd8\xff"


def test_quality_argument_accepted(tmp_path: Path) -> None:
    """The quality kwarg is honoured (lower quality should not raise)."""
    out = tmp_path / "low.jpg"
    svg_tree_to_jpg(_make_minimal_svg_tree(), out, quality=40)
    assert out.exists()
    assert out.read_bytes()[:3] == b"\xff\xd8\xff"
