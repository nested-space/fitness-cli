# Governance CLI - Copilot Instructions

## Project Overview

This is a Python CLI tool (`gcli`) for managing chemical materials and projects in a governance database. It provides operations for materials (with SMILES support), projects, manufacturing processes, stages, components, and NCRM library entries. The CLI interfaces with a PostgreSQL database via the `governance_server` package (distributed as a wheel in `lib/`).

## Installation & Setup

```bash
# Development installation
./install.sh

# Or manually:
pip install ./lib/governance_server-1.10.0-py3-none-any.whl
pip install -e .
```

**Environment Variables Required:**
- `DB_USER`, `DB_PASSWORD`: Database credentials
- `DB_HOST`, `DB_PORT`: Database connection (defaults: localhost:5432)
- `DB_NAME`: Production database (default: cggovernance)
- `DB_TEST_NAME`: Dev/test database (default: cd-governance-dev)

## Testing

Tests use pytest with async support:

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_ncrm_parser.py -v

# Run single test function
python -m pytest tests/test_ncrm_parser.py::test_parse_comma_and_quoted_aliases -v
```

**Note:** pytest is not included in `requirements.txt` or `pyproject.toml` dependencies—install separately for testing.

## Architecture

### Core Structure

- **`src/governance_cli/__main__.py`**: Main CLI entry point with argparse-based command routing
- **`src/governance_cli/cli/`**: Command handlers (`*_commands.py`) for each entity type
- **`src/governance_cli/parsers/`**: Argparse subparser definitions and CSV parsing utilities
- **`src/governance_cli/operations/`**: Business logic for CRUD operations and data processing
- **`src/governance_cli/database/`**: Database connection management and session handling
- **`src/governance_cli/config/`**: Environment settings and database URL construction
- **`src/governance_cli/utils/`**: Console formatting, CSV parsing, and helper utilities
- **`src/governance_cli/service/`**: External service integrations (DMTA enrichment)

### Data Flow Pattern

1. CLI argument parsing (parsers) → 2. Command handler (cli) → 3. Operations layer → 4. Database/external services
5. All async operations use SQLAlchemy async sessions via `get_db_session()`

### Key Entities

- **Material**: Chemical materials with SMILES notation, aliases, and DMTA enrichment support
- **Project**: Projects linked to therapy areas and materials
- **Stage**: Manufacturing stages with risk assessments
- **Component**: Stage components with salts and counterions
- **NCRM Library**: Non-controlled raw materials with SMILES and aliases
- **Manufacturing Process**: Process definitions and relationships

## Key Conventions

### Async Patterns

- All database operations are async (use `async def` and `await`)
- Session management: Always use `async with get_db_session(env) as session`
- Entry points: Use `asyncio.run()` for CLI command handlers called from `__main__.py`

### Generic Operations Pattern

The operations layer provides generic base operations to reduce code duplication:

**Available Generic Operations** (from `operations/base_operations.py`):
- `generic_get_by_id(model, id, name, env, verbose)` - Get any entity by UUID
- `generic_check_exists(model, id, name, env, verbose)` - Check existence by UUID (simple ID-only)
- `generic_get_stats(model, name, env, verbose, calculator)` - Get entity statistics with optional custom calculator
- `generic_list_by_field(model, field, value, name, env, verbose)` - List by foreign key filter

**When to Use Generic vs Specialized**:

Use generic operations when:
- Simple ID-based lookups with no joins or eager loading
- Standard existence checks by UUID only (not composite keys)
- Basic foreign key filtering without complex conditions
- Simple statistics or with well-defined calculator function

Keep specialized operations when:
- Name-based or SMILES-based lookups (domain-specific logic)
- Composite key checks (e.g., check_component_exists checks process+material uniqueness)
- Complex queries requiring joins, eager loading, or multiple conditions
- Operations requiring special transaction management or business rules
- Complex statistics with domain logic best kept together

**Example Usage**:
```python
# In operations/component_operations.py
async def get_component_by_id(component_id: UUID, env: Environment, verbose: bool) -> Optional[Component]:
    """Get a component by ID."""
    from .base_operations import generic_get_by_id
    return await generic_get_by_id(Component, component_id, "component", env, verbose)

# In operations/stage_operations.py
async def list_stages_by_process(process_id: UUID, env: Environment, verbose: bool) -> list[Stage]:
    """List all stages for a specific manufacturing process."""
    from .base_operations import generic_list_by_field
    return await generic_list_by_field(Stage, 'process_id', process_id, 'stage', env, verbose)
```

**Impact**: Generic operations have eliminated ~260 lines of duplicated CRUD code across 21 functions while maintaining type safety and consistent error handling.

### Error Handling

- **Connectivity errors**: Check with `is_connectivity_error(exc)` from `database.exceptions`
- **User-friendly messages**: Print specific error messages before re-raising
- Bulk operations: Support `--skip-errors` to continue on individual failures

### Console Output

Use utilities from `utils/console_formatting.py`:
- `print_success()`, `print_error()`, `print_warning()`, `print_info()`
- `print_header()`, `print_subheader()`, `print_separator()`
- `print_key_value()` for structured output
- `print_progress()` for operations feedback

Color coding: Green (success), Red (error), Yellow (warning), Cyan (info), Magenta (emphasis)

### SMILES Handling

- **Canonicalization**: Use RDKit to validate and canonicalize SMILES strings
- **Check function**: `is_smiles_canonical()` in `operations/smiles_operations.py`
- **Pattern**: Auto-detect if search value is UUID, SMILES, or name based on characters
- SMILES contain chemical chars: `()[]=#@+-` without spaces

### Dry Run Support

- Add `--dry-run` flag to destructive operations (create, update, delete)
- Pattern: Check `if dry_run:` early, print intended actions, return without database changes
- Helper: `add_dry_run_argument()` in `parsers/base.py`

### CSV Bulk Operations

- Support both comma and semicolon delimiters (auto-detect)
- Handle quoted fields with embedded delimiters
- Aliases: Split on commas, semicolons, or pipes within quoted fields
- Pattern: Parse entire file first, then process with optional `--skip-errors`

### Argument Parsing

- Use helper functions from `parsers/base.py`:
  - `add_common_arguments()`: Adds `--verbose`
  - `add_dry_run_argument()`: Adds `--dry-run`
  - `add_dmta_arguments()`: Adds `--enable-dmta`/`--disable-dmta`
  - `add_material_search_arguments()`: Adds `--id`/`--name`/`--smiles` mutually exclusive group
- Global `--env {dev,prod}` flag for environment selection

### Material Search Pattern

Use `run_material_get_by_name_or_id()` from `cli/material_commands.py` to resolve materials by ID or name. Auto-detection logic in `update_material_by_search()` can identify UUID vs SMILES vs name.

### Database Models

Models come from `governance_server.model.table` (external wheel). Use SQLModel patterns:
- `await Model.get_all(session)`
- `await Model.get_where(session, condition)`
- Update via schema objects from `governance_server.schema.update`

## Common Commands

```bash
# Material operations
gcli material create --name "Aspirin" --smiles "CC(=O)Oc1ccccc1C(=O)O" --dry-run
gcli material list --has-smiles --limit 10
gcli material update --name "Old" --set-name "New"
gcli material bulk-create --file materials.csv --enable-dmta

# Project operations
gcli project create --name "Alpha" --therapy-area "Oncology" --material-name "Aspirin"
gcli project list --therapy-area "CVRM"
gcli project bulk-create --file projects.csv

# Database maintenance
gcli database material analyze
gcli database material canonicalize --dry-run
```

## Therapy Areas

Valid values (enum from governance_server):
- Oncology
- CVRM
- Respiratory and Immunology
- Vaccines and Immune Therapies
- Rare Diseases

## External Dependencies

- **governance_server wheel**: Provides database models, schemas, and base operations (in `lib/`)
- **RDKit**: Chemical informatics for SMILES validation and canonicalization
- **DMTA service**: Optional external enrichment for materials (see `operations/dmta_operations.py`)
- **argcomplete**: Shell tab completion support (optional)

## File Naming Conventions

- Commands: `<entity>_commands.py` (e.g., `material_commands.py`)
- Parsers: `<entity>_parser.py` (e.g., `material_parser.py`)
- Operations: `<entity>_operations.py` (e.g., `material_operations.py`)
- Functions: Snake case (e.g., `run_material_create`, `update_material_by_search`)

## Documentation Style

Follow these conventions for docstrings and comments (see `tmp/example_documentation.py` for reference):

### Module-Level Docstrings

Start each module with a brief description followed by elaboration of key responsibilities:

```python
"""
Brief one-line description of the module.

More detailed explanation covering:
- Primary purpose and scope
- Key responsibilities (bullet points)
- Important behavioral notes or constraints
"""
```

### Function/Method Docstrings

Use descriptive docstrings with clear structure:

```python
def function_name(param1: type, param2: type) -> return_type:
    """Brief one-line description of what the function does.

    Optional longer explanation covering:
    - Why this function exists or when to use it
    - Important behavioral details
    - Edge cases or gotchas

    Args:
        param1: Description of param1, including constraints or expected format.
        param2: Description of param2.

    Returns:
        Description of the return value, including type details if complex.

    Raises:
        ExceptionType: When and why this exception is raised.
        OtherException: Description of other exceptions.
    """
```

### Class Docstrings

Classes should document their purpose and key attributes:

```python
class ClassName:
    """Brief description of the class purpose.

    Longer explanation if needed, covering:
    - Primary use case
    - Key behaviors or patterns
    - Important lifecycle notes

    Attributes:
        attr_name: Description of the attribute, including type and constraints.
        other_attr: Description with important details.
    """
```

### Key Documentation Principles

1. **"Why this exists" context**: For non-obvious functions, explain the reasoning or problem being solved
2. **Location strings**: For validation errors, create consistent location strings showing exactly where an issue occurred:
   ```python
   location = f"config='{file}', page='{page}', field='{field}'"
   ```

3. **Validation method structure**: Document what rules are enforced in validation methods:
   ```python
   """Validate integrity rules for X.

   Rules enforced:
       - Rule 1 description
       - Rule 2 description
       - Rule 3 description

   Args:
       ...

   Raises:
       ConfigError: If any integrity rule is violated.
   """
   ```

4. **Expected data shapes**: Document expected argument structures for complex dictionaries:
   ```python
   """Validate mapping arguments.

   Expected shape:
       args = {
           "required_field": "value",     # required, type details
           "optional_field": "value"      # optional, default behavior
       }

   Args:
       ...
   """
   ```

5. **Keep docstrings focused**: Document behavior and contracts, not implementation details
6. **Use inline comments sparingly**: Only for non-obvious logic; prefer clear code over comments
