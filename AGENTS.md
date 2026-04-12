# BSB Lark - Backend Project

## Project Overview
- **Project Name**: bsb_lark
- **Tech Stack**: Python 3.12 / FastAPI
- **Primary Purpose**: BSB Transport Australia - Lark-based logistics backend (migrating from Python/Google Sheets)
- **Data Source**: Lark Bitable (BSB Base, 37 tables)
- **Package Manager**: uv

## Project Structure
```
app/
  main.py                  # FastAPI entry + auto module registration
  config/
    settings.py            # Pydantic Settings (env vars)
    lark.py                # Lark client singleton
  core/
    base_repository.py     # Generic Bitable CRUD (list/get/create/update/delete/batch)
    base_service.py        # Service base class
    response.py            # Unified response envelope {code, data, message}
    exceptions.py          # AppError, NotFoundError, ValidationError, LarkApiError
    middleware.py           # Correlation ID + error handling + timing
    registry.py            # Auto-discover & register module routers
  shared/
    lark_tables.py         # All 37 Bitable table/field ID mappings (TableDef + FieldRef)
    enums.py               # Depot, ContainerType, DeliverType, etc.
    utils.py               # Date/time helpers (Sydney timezone)
  modules/                 # Business modules (auto-registered by registry.py)
    master_data/           # MD-* tables (warehouse, driver, vehicle, terminal, etc.)
    pricing/               # MD-Price-* tables + fee calculators (future)
    operations/            # Op-* tables + spider strategies (future)
    email/                 # Email automation pipeline (future)
    sync/                  # Cross-table data sync (future)
```

## Module Convention
Each module has 4 files:
- `router.py` — FastAPI router (auto-registered)
- `service.py` — Business logic
- `repository.py` — Inherits BaseRepository, just sets table_id
- `schemas.py` — Pydantic request/response models

**Adding a new module**: create directory under `modules/` with `router.py`, it's auto-registered.

## Code Standards

### Python
- Python 3.12+ with type hints everywhere
- `from __future__ import annotations` in every file
- Pydantic v2 for all data validation
- No `Any` without justification — use specific types
- `async/await` for all I/O operations

### Backend Patterns
- Repository pattern: all Bitable API calls only in repository layer
- Service layer: business logic, calls repositories
- Unified response: `{ code: 0, data, message }` via `ApiResponse.ok()` / `ApiResponse.error()`
- Custom exceptions: `AppError`, `NotFoundError`, `LarkApiError`
- Correlation ID on every request

### Lark SDK
- `larksuiteoapi` Python SDK for all Bitable operations
- Table/field IDs managed centrally in `shared/lark_tables.py`
- Token auto-refresh handled by SDK
- BaseRepository provides generic CRUD, subclasses only set `table_id`

## Skills Usage Guide

### Always Relevant
- `planning-with-files`: For tasks requiring 5+ tool calls or multi-step work
- `get-api-docs`: Before integrating any Lark API endpoint
- `context7-cli`: When needing latest docs for any library/SDK

### On Demand
- `test-driven-development`: Before implementing any new feature or bugfix
- `docx` / `xlsx` / `pdf`: When generating downloadable documents from Lark data
- `gh-fix-ci`: When GitHub Actions checks fail
- `exa-search`: When researching Lark API capabilities

## Git Conventions
- Branch naming: `feat/xxx`, `fix/xxx`, `refactor/xxx`, `chore/xxx`
- Commit messages: Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`)
- PR before merge to main — no direct push to main
- Run lint + typecheck + test before committing

## Commands
```bash
# Development
uv run uvicorn app.main:app --reload --port 3000     # Start dev server
uv run ruff check .                                    # Lint
uv run ruff format .                                   # Format
uv run mypy app/                                       # Type check
uv run pytest                                          # Run tests
```

## Lark CLI
```bash
lark-cli base +base-get --base-token WXcubLU2oaJbHdsNTzCjy16Spwc   # Check base
lark-cli base +field-list --base-token WXcubLU2oaJbHdsNTzCjy16Spwc --table-id TABLE_ID  # List fields
lark-cli base +record-list --base-token WXcubLU2oaJbHdsNTzCjy16Spwc --table-id TABLE_ID  # List records
```
