"""
SVG-to-JPEG rasterisation for the wallpaper output.

Renders an in-memory lxml SVG tree to PNG bytes via cairosvg, composites
the result onto an opaque white background (JPEG has no alpha channel),
and writes a JPEG file to disk.
"""

from io import BytesIO
from pathlib import Path

import cairosvg
from lxml import etree
from PIL import Image


def svg_tree_to_jpg(
    tree: etree._ElementTree,
    path: Path,
    *,
    quality: int = 90,
) -> None:
    """Rasterise an SVG element tree and write it to a JPEG file.

    Args:
        tree: Parsed SVG element tree to render.
        path: Destination filesystem path for the JPEG.
        quality: JPEG quality (1–95). Pillow recommends staying at or below 95.
    """
    svg_bytes = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
    png_bytes = cairosvg.svg2png(bytestring=svg_bytes)
    rendered = Image.open(BytesIO(png_bytes))
    background = Image.new("RGB", rendered.size, (255, 255, 255))
    if rendered.mode in ("RGBA", "LA"):
        background.paste(rendered, mask=rendered.split()[-1])
    else:
        background.paste(rendered)
    background.save(path, "JPEG", quality=quality, optimize=True)
