# Tech Stack

## Languages
- Python (3.11)

## Tooling
- Poetry (deps, venv)
- Ruff (lint + format), mypy (types), pytest + pytest-cov (tests)
- poe-the-poet (tasks), pre-commit (hooks)
- Bicep + `az bicep` (infra)

## Modules / Key libs
- <runtime deps, only the important ones>  
  _Full list_: see `pyproject.toml` and `poetry.lock`.

## Conventions
- Conventional Commits via Commitizen
- Branching: `<type>/<short-desc>` (e.g., `feat/watch-pipeline`)
- Code style: `ruff format`, `ruff check --fix`, strict mypy

## Folder Structure
- .devcontainer for codespace configuration
- ./docs for documentation
- ./infra for bicep infrastructure and parameter files
- ./src for python code
- ./src/watchtower for watchtower application
- ./tests for python tests