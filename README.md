# fitness-cli

A lightweight command-line tool to record fitness activities and generate a monthly SVG wallpaper showcasing your progress.

## Features

- **Activity logging** — store runs, rides, hikes, and more in a local SQLite database.
- **Monthly calendar view** — visualise active days coloured by intensity right in the terminal.
- **SVG wallpaper generation** — produce a personalised monthly wallpaper with milestone medals and a colour-coded calendar grid.
- **Milestone tracking** — distance and consistency medals are earned automatically from your logged activities.

## Requirements

- Python 3.11+

## Installation

```bash
# Create and activate a virtual environment (recommended)
python -m venv ~/.venvs/fitness
source ~/.venvs/fitness/activate

# Install from source
git clone https://github.com/nested-space/fitness-cli.git
cd fitness-cli
pip install -e ".[dev]"
```

The tool is available as both `fitness-cli` and `fcli`.

## Usage

### Record an activity

```bash
fitness-cli activity add \
  --date 2026-05-01 \
  --type Run \
  --distance 8.2 \
  --duration 45 \
  --intensity moderate
```

**Activity types:** `Bike Indoor`, `Elliptical`, `Strength`, `Trail Run`, `Run`, `Treadmill`, `Walk`, `Hike`, `Bike`

**Intensity levels:** `light`, `moderate`, `high`, `peak`

`--distance` is optional (e.g. for Strength sessions).

### List activities

```bash
# All activities
fitness-cli activity list

# Filter to a specific month
fitness-cli activity list --month 2026-05
```

### View recent activities

```bash
# Last 10 activities (default)
fitness-cli activity recent

# Last N activities
fitness-cli activity recent --count 20
```

### Show a calendar view

```bash
# Current month
fitness-cli activity show

# Specific month
fitness-cli activity show --month 2026-05
```

Intensity legend: `○` none · `◎` light · `◉` moderate · `●` high · `⬤` peak

### Delete an activity

```bash
fitness-cli activity delete 42
```

### Generate the monthly SVG wallpaper

```bash
# Current month, default output path (output.svg)
fitness-cli wallpaper generate

# Specific month and output path
fitness-cli wallpaper generate --month 2026-05 --output ~/Desktop/may-wallpaper.svg

# Custom SVG template
fitness-cli wallpaper generate --template my-template.svg --output wallpaper.svg
```

The command prints a summary of earned milestones and active days.

## Milestones

| Medal | Earned when |
|---|---|
| **Distance** | Maximum single-activity distance in the last 4 weeks ≥ 1 km. Badge shows `floor(max_km)`. |
| **Consistency** | ≥ 1 consecutive complete week (Mon–Sun) with ≥ 3 activities, of which ≥ 2 are `moderate` or higher. Badge shows the streak count. |

## Development

```bash
source ~/.venvs/fitness/bin/activate
pip install -e ".[dev]"

# Quality gates (all must pass before committing)
ruff check src/ tests/
pylint src/
mypy src/ --strict
pytest tests/ -v
```

## Licence

MIT
