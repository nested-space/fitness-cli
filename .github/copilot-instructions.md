# Fitness Wallpaper CLI — Copilot Instructions

## Project Overview

This is a Python CLI tool (`fitness-wallpaper`) for:

1. **Storing fitness activities** in a lightweight local SQLite database (date, type, distance, duration, intensity).
2. **Generating a monthly SVG wallpaper** from `wallpaper-template.svg` by:
   - Showing or hiding distance/consistency milestone medals based on achievement.
   - Setting badge numbers to reflect the current milestone level.
   - Configuring the calendar grid to display the correct month layout.
   - Colouring active calendar days by intensity (light or moderate/high).

## Installation & Setup

```bash
# Always use the project virtual environment — never bare python/pip/pytest
source ~/.venvs/fitness/bin/activate

# Install in editable mode with dev tools
pip install -e ".[dev]"
```

**Hard rule**: Every command in this project — `python`, `pip`, `pytest`, `mypy`, `ruff`, `pylint` — must be run inside `~/.venvs/fitness`. Never invoke system-level binaries for project work.

## Quality Gates — Applied at Every Phase

After every phase of work (except documentation-only phases), the following must **all pass** before moving on:

```bash
source ~/.venvs/fitness/bin/activate
ruff check src/ tests/          # linting + formatting
pylint src/                     # static analysis
mypy src/ --strict              # type checking
pytest tests/ -v                # unit tests
```

Tests for newly written code must be written **alongside** the code — not deferred to a later phase.

## Architecture

### Source Layout

```
src/
└── fitness_wallpaper/
    ├── __main__.py                  # Click CLI root group
    ├── cli/
    │   ├── activity_commands.py     # activity add / list / delete
    │   └── wallpaper_commands.py    # wallpaper generate
    ├── database/
    │   ├── connection.py            # SQLite connection + schema creation
    │   └── models.py                # Dataclasses: Activity, ActivityType, Intensity
    ├── operations/
    │   ├── activity_operations.py   # CRUD on the activities table
    │   └── milestone_operations.py  # Distance and consistency milestone logic
    ├── svg/
    │   ├── svg_editor.py            # Shared lxml helpers
    │   ├── medals_svg.py            # Medal visibility + badge text
    │   └── calendar_svg.py          # Month grid + activity day colouring
    └── config/
        └── settings.py              # DB path, template path, colour constants
tests/
├── test_database.py
├── test_activity_operations.py
├── test_milestone_operations.py
├── test_medals_svg.py
└── test_calendar_svg.py
```

### Data Flow

```
CLI args (click)
  → CLI command handler (cli/)
  → Operations layer (operations/)
  → Database (database/) or SVG layer (svg/)
```

Each layer has **exactly one responsibility**:
- `cli/` — argument parsing and user feedback only.
- `operations/` — business logic; no I/O beyond the database.
- `database/` — schema, connection, and raw SQL only; no business logic.
- `svg/` — SVG manipulation only; no business logic.
- `config/` — constants and paths only.

## Architecture Principles

### SOLID

- **Single Responsibility**: Each module and function does one thing. `medals_svg.py` only manipulates medal elements; it knows nothing about milestone thresholds.
- **Open/Closed**: Use dataclasses and typed enums for domain objects so new activity types or intensity levels can be added without modifying existing logic.
- **Liskov Substitution**: Prefer pure functions over classes where state is not required.
- **Interface Segregation**: Keep function signatures small; never pass a God-object when only one field is needed.
- **Dependency Inversion**: Pass `sqlite3.Connection` into operations rather than constructing it inside them.

### DRY

- Shared SVG style manipulation lives only in `svg_editor.py`. Never copy `set_style_prop` logic into other modules.
- Milestone threshold constants live only in `config/settings.py`.
- SQL table definitions live only in `database/connection.py`.

### Clean Responsibility Seams

- Business logic never touches `lxml` or `sqlite3` directly — it delegates to the SVG or database layers.
- CLI handlers never perform calculations — they call operations and print results.

## Key Conventions

### Type Hints

- Type hints are **mandatory everywhere** — function signatures, return types, local variables where the type is not obvious.
- `mypy --strict` must pass. Never use `Any` unless there is no alternative, and document why.
- Use `Literal["light", "moderate", "high"]` instead of bare strings for intensity values.
- Use `enum.Enum` for `ActivityType`; use `Literal` or `Enum` for `Intensity`.

### Dataclasses

- Use `@dataclass` (or `@dataclass(frozen=True)`) for value objects such as `Activity`.
- Do not use mutable default arguments.

### Database

- Use raw `sqlite3` — no ORM.
- Always use parameterised queries (`?` placeholders). Never interpolate user values into SQL strings.
- Schema is created on first connection via `connection.py`.
- Pass `sqlite3.Connection` into operations; never open a connection inside an operation function.

### SVG Editing

- Always parse SVG with `lxml.etree`; never use `xml.etree.ElementTree` or regex on SVG content.
- Locate elements by `inkscape:label` attribute using `find_by_label()` from `svg_editor.py`.
- Modify only inline `style` attributes via `set_style_prop()`. Never modify `fill` or `display` as top-level attributes.
- Write output with `xml_declaration=True`, `encoding="UTF-8"`, `standalone=True`.

### CLI

- Use `click` for all CLI composition (groups, commands, options).
- Every command must have a `--help` string.
- Print success/error output to stdout/stderr respectively.
- Do not mix CLI argument parsing with business logic.

### Error Handling

- Raise specific, typed exceptions from the operations and SVG layers.
- Catch and print user-friendly messages in the CLI layer before exiting with a non-zero code.
- Never swallow exceptions silently.

## Milestone Definitions

### Distance Milestone

- Query: the **maximum single-activity `distance_km`** recorded in the **last 4 calendar weeks**.
- Milestone value: `math.floor(max_distance)` as an integer (kilometres).
- Medal shown (coloured) when value ≥ 1; otherwise the grey-out placeholder is shown.

### Consistency Milestone

- A **complete week** (Mon–Sun) satisfies **both**:
  - At least **2** activities with intensity `moderate` or `high`.
  - At least **3** activities in total.
- Milestone value: the count of **consecutive complete weeks** ending before the current (incomplete) week.
- Medal shown (coloured) when value ≥ 1.

## SVG Element Reference

Refer to `wallpaper-template-spec.json` for the authoritative list of `inkscape:label` values. Key labels:

| Purpose | Label |
|---|---|
| Coloured distance medal group | `distance-medal` |
| Grey distance medal placeholder | `distance-medal-grey-out` |
| Distance badge number text | `distance-medal-ribbon-top` |
| Coloured consistency medal group | `consistency-medal` |
| Grey consistency medal placeholder | `consistency-medal-grey-out` |
| Consistency badge number text | `consistency-medal-number` |
| Calendar day elements | `calendar-day-WW-DD` (week 01–05, dow 01–07) |

## Calendar Day Colours

| Activity intensity | Fill colour | Fill opacity |
|---|---|---|
| None (default weekday) | `#242424` | `1` |
| None (default weekend) | `#000000` | `0.116777` |
| Light | `#fef3c7` | `1` |
| Moderate or High | `#f7bb01` | `1` |

## Documentation Style

### Module-Level Docstrings

```python
"""
Brief one-line description of the module.

More detailed explanation covering:
- Primary purpose and scope
- Key responsibilities
- Important behavioural notes or constraints
"""
```

### Function / Method Docstrings

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """Brief one-line description.

    Optional longer explanation covering:
    - Why this function exists
    - Important behavioural details
    - Edge cases or gotchas

    Args:
        param1: Description, including constraints or expected format.
        param2: Description.

    Returns:
        Description of the return value.

    Raises:
        ExceptionType: When and why this exception is raised.
    """
```

### Class Docstrings

```python
class ClassName:
    """Brief description of the class purpose.

    Attributes:
        attr_name: Description, including type and constraints.
    """
```

### Key Principles

1. **Explain "why", not "what"** — code explains what; docstrings explain why.
2. **Document rules in validation functions** using a `Rules enforced:` section.
3. **Use inline comments sparingly** — only for non-obvious logic.
4. **Keep docstrings focused** on behaviour and contracts, not implementation details.

## Common Commands

```bash
# Activate the venv first
source ~/.venvs/fitness/bin/activate

# Install / update
pip install -e ".[dev]"

# Add an activity
fitness-wallpaper activity add --date 2026-04-15 --type Run --distance 8.2 --duration 45 --intensity moderate

# List activities for a month
fitness-wallpaper activity list --month 2026-04

# Delete an activity
fitness-wallpaper activity delete 42

# Generate the wallpaper SVG for the current month
fitness-wallpaper wallpaper generate --month 2026-04 --output output.svg

# Quality gates
ruff check src/ tests/
pylint src/
mypy src/ --strict
pytest tests/ -v
```
