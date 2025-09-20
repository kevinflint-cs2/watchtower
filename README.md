# WatchTower: WORK IN PROGRESS

An Agent AI for Incident Response that triages alerts, auto-enriches evidence, and orchestrates approved containment actions—under human-in-the-loop control—to cut MTTA/MTTR, standardize response, and keep a complete audit trail.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/kevinflint-cs2/watchtower?quickstart=1)


---

## What is this?

A simple, automated setup of **Azure AI Foundry** that:

* Provisions infra with **azd + Bicep**, builds the following:
  * Application Insight
  * Log Analytic Workspace
  * Key Vault
  * Storage Account
  * AI Foundry Project
* Creates a **AI Agents**
  * Work in progress, but will create a single agent
  * Goal is to leverage Agentic AI to assist with incident response 
* Runs a **post-creation smoke test**
* Gives you a one-liner to query the agent

---

## Tech Stack

* **GitHub** for repo
* **azd / Bicep** for infrastructure
* **azd** for environment management
* **Python 3.12** for for non-inrastructure tasks like env setup and agent mgmt
* **`azure.yaml`** orchestrates post-provision agent creation
* **Poetry** for dependencies & virtualenv
* **Poe the Poet** for task running
* **Ruff** for lint + format
* **mypy** for type checking
* **Commitizen** for conventional commits & versioning
* **detect-secrets** + **pre-commit** to detect & block secret leaks

---

## Prerequisites

* **Azure** subscription with permissions to create resource groups, AI Foundry, Key Vault, etc.
* **CLI tools**

  * [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az`)
  * [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/) (`azd`)
  * **Python 3.12** and **Poetry**

    ```bash
    pipx install poetry  # or use your preferred installer
    ```

> Codespaces friendly: open with the badge above for an in-browser dev environment.

---

## Quickstart

```bash
# 1) Install Python deps
poetry install

# 2) Provision infra, bootstrap envs, create agent, and run a smoke test
poetry run poe up

# 3) Ask the agent a question
poetry run python ./scripts/ask_question.py "what is 1+1, answer only"

# 4) Tear everything down (purges where applicable)
poetry run poe down
```

**What `poe up` does**

* Prompts for environment (`dev` / `preprod` / `prod`, default `dev`)
* Creates/updates `.azure/<env>/.env` and sets **azd env** values
* Exports the active env to root `.env` (Python reads this)
* Runs `azd up` to deploy infra and create an AI Agent
* Executes a quick smoke test to verify the agent responds

---

## Environments & Configuration

* **Source of truth:** `azd env` (per-env key/value store)
* **Per-env files:** `.azure/<env>/.env` (generated & managed by the bootstrap script)
* **Root file for Python:** `.env` (auto-exported from the selected `azd` env)

> Keep `.env` files **untracked**. They mirror azd values locally for Python.

---

## Common Tasks

```bash
# Bring up/update the selected environment (interactive wizard)
poetry run poe up

# Ask the agent something
poetry run python ./scripts/ask_question.py "help me summarize X"

# Destroy all resources (non-interactive, purge where supported)
poetry run poe down

# Lint, fix, typecheck, secrets validation (optional bundle)
poetry run poe checks
```

See `pyproject.toml` for the full set of Poe tasks (login, commit, secret scans, etc.).

---

## Secret Hygiene

**Local guard rails + server protection**

* **detect-secrets** (local)

  ```bash
  poetry add -G dev detect-secrets pre-commit
  poetry run detect-secrets scan > .secrets.baseline
  poetry run detect-secrets audit .secrets.baseline
  git add .secrets.baseline && git commit -m "chore(secrets): add baseline"
  poetry run pre-commit install
  ```

  Validate anytime:

  ```bash
  poetry run detect-secrets scan --baseline .secrets.baseline
  ```

* **GitHub Secret Scanning + Push Protection** (enable in repo/org settings)

> Azure Subscription IDs are **not credentials**, but rotate any real secrets (keys/tokens) that ever land in git.

---

## Development

* **Ruff**

  ```bash
  poetry run ruff format .
  poetry run ruff check . --fix
  ```
* **mypy**

  ```bash
  poetry run mypy scripts tests
  ```
* **Commitizen**

  ```bash
  poetry run cz commit          # guided conventional-commits
  poetry run cz bump --yes      # bump version + changelog + tag
  ```

---

## How it works (high level)

```mermaid
flowchart LR
  Dev["poetry run poe up"] --> Env["Bootstrap envs<br/>(.azure/&lt;env&gt;/.env + azd env)"]
  Env --> Bicep["azd up → Bicep deploy"]
  Bicep --> AFA["Azure AI Foundry Account"]
  Bicep --> AFP["Azure AI Foundry Project"]
  Env -- python --> Agent["Create AI Agent"]
  Agent --> Test["Smoke Test"]
```

* **Infra**: Bicep templates deployed by `azd up`
* **Env**: Values come from `azd env`; Python consumes the exported `.env`
* **Agent**: Python scripts create/query/clean up the agent

---

## Troubleshooting

* **Login issues**

  ```bash
  azd login
  az account show
  ```
* **Env drift**

  * Re-run `poetry run poe up` and re-select the environment
* **Key Vault purge protection**

  * `poetry run poe down` uses purge flags; if blocked by policy, update purge protection or delete manually
* **Missing `.env`**

  * `poetry run poe up` will recreate it from `azd env get-values`

---

## Cleanup

```bash
poetry run poe down
```

> Destructive and **irreversible** for purge-capable resources—use with care.

---
