# Tech Stack

## Languages
- Python (3.11)

## Tooling
- **GitHub Codespaces (IDE)** with dev containers
- Poetry (deps, venv)
- Ruff (lint + format), mypy (types), pytest + pytest-cov (tests)
- poe-the-poet (tasks), pre-commit (hooks)
- Bicep + `az bicep` (infra authoring & linting)
- Azure Developer CLI: `azure.yml` to deploy Bicep files (CI/CD to Azure)

## Modules / Key libs
- <runtime deps, only the important ones>  
  _Full list_: see `pyproject.toml` and `poetry.lock`.

## Conventions
- Conventional Commits via Commitizen
- Branching: `<type>/<short-desc>` (e.g., `feat/watch-pipeline`)
- Code style: `ruff format`, `ruff check --fix`, strict mypy

## Folder Structure
- `.devcontainer/` — Codespaces configuration
- `docs/` — Documentation
- `infra/` — Bicep infrastructure + parameter files
- `prompts/` — Store complex prompts
- `src/` — Python code
- `src/watchtower/` — Watchtower application
- `tests/` — Python tests
- `.github/workflows/azure.yml` — GitHub Actions workflow that **deploys Bicep** to Azure

### Agentic Prompts (Authoring Workflow)
- All complex agent instructions are stored as markdown under `./prompts/`.
- Automation reads prompts from disk (e.g., `HUNT_SHEET_PATH=./prompts/HuntSheet.md`) and sends them to the Agent.
- Benefits: versioned prompts, code/prompt separation, easy reviews, quick edits without redeploying.

