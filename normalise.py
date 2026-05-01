#!/usr/bin/env python3
"""
normalise_svg_labels.py
Normalises object labels in an SVG file by applying these rules (in order):
  1. " - "  →  "-"
  2. "_"     →  "-"
  3. " "     →  "-"
  4. Upper-case letters → lower-case

Gradient definitions and all references to them (xlink:href, url(#…))
are intentionally left untouched so fills/strokes remain valid.

Usage:
    python normalise_svg_labels.py input.svg [output.svg]

If no output path is given, the result is written to <input>_normalised.svg.
"""

import re
import sys
from pathlib import Path


# Attributes whose values are treated as human-readable labels.
LABEL_ATTRS = {"id", "label", "inkscape:label", "data-name", "aria-label"}

# Elements whose inner text is treated as a label.
LABEL_ELEMENTS = {"title", "desc"}


def normalise(text: str) -> str:
    """Apply the four normalisation rules to a label string."""
    text = text.replace(" - ", "-")   # Rule 1
    text = text.replace("_", "-")     # Rule 2
    text = text.replace(" ", "-")     # Rule 3
    text = text.lower()               # Rule 4
    return text


# ---------------------------------------------------------------------------
# Collect every gradient ID so we can protect them everywhere they appear.
# ---------------------------------------------------------------------------

def collect_gradient_ids(source: str) -> set:
    """Return the set of id values that belong to gradient elements."""
    pattern = re.compile(
        r'<\w*[Gg]radient\b[^>]*?\bid\s*=\s*(["\'])(?P<id>[^"\']+)\1',
        re.DOTALL,
    )
    return {m.group("id") for m in pattern.finditer(source)}


# ---------------------------------------------------------------------------
# Attribute replacement
# ---------------------------------------------------------------------------

def make_attr_replacer(gradient_ids):
    """Return a compiled regex and a substitution function for label attrs."""

    attr_pattern = re.compile(
        r'(?P<attr>' + '|'.join(re.escape(a) for a in LABEL_ATTRS) + r')'
        r'(?P<eq>\s*=\s*)'
        r'(?P<q>["\'])'
        r'(?P<value>[^"\']*)'
        r'(?P=q)',
        re.IGNORECASE,
    )

    def replacer(m):
        value = m.group("value")
        # Leave gradient IDs alone.
        if value in gradient_ids:
            return m.group(0)
        new_val = normalise(value)
        return f'{m.group("attr")}{m.group("eq")}{m.group("q")}{new_val}{m.group("q")}'

    return attr_pattern, replacer


# ---------------------------------------------------------------------------
# Element inner-text replacement
# ---------------------------------------------------------------------------

def make_elem_replacer():
    """Return a compiled regex and substitution function for label elements."""

    elem_pattern = re.compile(
        r'(?P<open><(?:' + '|'.join(LABEL_ELEMENTS) + r')[^>]*>)'
        r'(?P<value>[^<]*)'
        r'(?P<close></(?:' + '|'.join(LABEL_ELEMENTS) + r')>)',
        re.IGNORECASE,
    )

    def replacer(m):
        new_val = normalise(m.group("value"))
        return f'{m.group("open")}{new_val}{m.group("close")}'

    return elem_pattern, replacer


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_svg(source: str) -> str:
    gradient_ids = collect_gradient_ids(source)

    attr_pattern, attr_replacer = make_attr_replacer(gradient_ids)
    source = attr_pattern.sub(attr_replacer, source)

    elem_pattern, elem_replacer = make_elem_replacer()
    source = elem_pattern.sub(elem_replacer, source)

    return source


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = (
        Path(sys.argv[2])
        if len(sys.argv) >= 3
        else input_path.with_stem(input_path.stem + "_normalised")
    )

    source = input_path.read_text(encoding="utf-8")
    result = process_svg(source)
    output_path.write_text(result, encoding="utf-8")

    print(f"Done. Normalised SVG written to: {output_path}")


if __name__ == "__main__":
    main()
