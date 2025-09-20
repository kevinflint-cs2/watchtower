#!/usr/bin/env python3
# ./scripts/set_envs.py
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

VALID_ENVS = ["dev", "preprod", "prod"]
DEFAULT_ENV = "dev"
DEFAULT_LOCATION = "eastus2"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_PREFIX = "wt"

STORAGE_SKUS = [
    "Standard_LRS",
    "Standard_GRS",
    "Standard_RAGRS",
    "Standard_ZRS",
    "Standard_GZRS",
    "Standard_RAGZRS",
    "Premium_LRS",
    "Premium_ZRS",
]

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)


def run(
    cmd: List[str], check: bool = True, capture: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def prompt_choice(prompt: str, choices: List[str], default: str) -> str:
    choice_str = "/".join(choices)
    raw = input(f"{prompt} [{choice_str}] (default: {default}): ").strip().lower()
    if not raw:
        return default
    if raw not in choices:
        print(f"Invalid choice: {raw}. Using default: {default}")
        return default
    return raw


def prompt_text(prompt: str, default: str | None = None, validator=None) -> str:
    suffix = f" (default: {default})" if default is not None else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw and default is not None:
            raw = default
        if validator and raw:
            if not validator(raw):
                print("Invalid value, please try again.")
                continue
        if raw:
            return raw


def is_uuid(s: str) -> bool:
    return bool(UUID_RE.match(s))


def try_default_subscription() -> str | None:
    try:
        cp = run(["az", "account", "show", "--query", "id", "-o", "tsv"])
        sub = cp.stdout.strip()
        return sub if is_uuid(sub) else None
    except Exception:
        return None


def parse_env_file(path: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def ensure_azd_env(env: str, subscription_id: str, location: str) -> None:
    try:
        run(["azd", "env", "select", env], check=True)
        return
    except subprocess.CalledProcessError:
        pass
    print(f"Creating azd environment '{env}' ...")
    run(
        [
            "azd",
            "env",
            "new",
            env,
            "--subscription",
            subscription_id,
            "--location",
            location,
            "--no-prompt",
        ],
        check=True,
    )


def write_env_file(env_path: Path, env_map: Dict[str, str]) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={env_map[k]}" for k in sorted(env_map.keys())]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_root_env_from_azd(env: str, root_path: Path = Path(".env")) -> None:
    cp = run(["azd", "env", "get-values", "-e", env, "--no-prompt"])
    root_path.write_text(cp.stdout, encoding="utf-8")
    print(f"Wrote {root_path} (exported from azd env '{env}')")


def main() -> int:
    print("=== Azure env bootstrap (single-task) ===")
    env = prompt_choice("Choose environment", VALID_ENVS, DEFAULT_ENV)

    per_env_dir = Path(".azure") / env
    per_env_file = per_env_dir / ".env"

    # If a per-env file exists, prefer values from it to avoid reprompting.
    existing = parse_env_file(per_env_file) if per_env_file.exists() else {}

    # Get/confirm required core values
    name_prefix = existing.get("NAME_PREFIX") or prompt_text(
        "Name prefix (e.g., 'wt')", default=DEFAULT_PREFIX
    )
    location = existing.get("AZURE_LOCATION") or prompt_text(
        "Azure location", default=DEFAULT_LOCATION
    )

    default_sub = (
        existing.get("AZURE_SUBSCRIPTION_ID") or try_default_subscription() or ""
    )
    subscription_id = existing.get("AZURE_SUBSCRIPTION_ID") or prompt_text(
        "Azure subscription ID (UUID)", default=default_sub, validator=is_uuid
    )

    # Storage SKU selection (numeric menu)
    storage_sku = existing.get("STORAGE_SKU")
    if not storage_sku:
        print("Select Storage SKU:")
        for idx, sku in enumerate(STORAGE_SKUS, start=1):
            print(f"  {idx}) {sku}")

        def sku_validator(s: str) -> bool:
            return s.isdigit() and 1 <= int(s) <= len(STORAGE_SKUS)

        sku_index_raw = prompt_text(
            "Enter number", default="1", validator=sku_validator
        )
        storage_sku = STORAGE_SKUS[int(sku_index_raw) - 1]

    model = existing.get("MODEL_DEPLOYMENT_NAME") or prompt_text(
        "Model deployment name (only 'gpt-4o-mini' supported for now)",
        default=DEFAULT_MODEL,
    )

    # Derived values
    azure_env_name = env
    agent_name = f"{name_prefix}-smoketest-{azure_env_name}"
    aifoundry_account = f"{name_prefix}-aifa-{azure_env_name}"
    aifoundry_project = f"{name_prefix}-aifp-{azure_env_name}"
    project_endpoint = f"https://{aifoundry_project}.services.ai.azure.com/api/projects/{aifoundry_project}"

    env_map = {
        "AGENT_NAME": agent_name,
        "AIFOUNDRY_ACCOUNT": aifoundry_account,
        "AIFOUNDRY_PROJECT": aifoundry_project,
        "AZURE_ENV_NAME": azure_env_name,
        "AZURE_LOCATION": location,
        "AZURE_SUBSCRIPTION_ID": subscription_id,
        "MODEL_DEPLOYMENT_NAME": model,
        "NAME_PREFIX": name_prefix,
        "PROJECT_ENDPOINT": project_endpoint,
        "STORAGE_SKU": storage_sku,
    }

    # Ensure azd env exists/selected
    ensure_azd_env(
        env=azure_env_name, subscription_id=subscription_id, location=location
    )

    # If per-env file did not exist, write it now; if it existed, refresh it with any new derived values
    write_env_file(per_env_file, {**existing, **env_map})
    print(f"Wrote {per_env_file}")

    # Push values into azd store for this env (import from per-env file)
    run(
        [
            "azd",
            "env",
            "set",
            "--file",
            str(per_env_file),
            "-e",
            azure_env_name,
            "--no-prompt",
        ],
        check=True,
    )
    print("Synced values into azd env store.")

    # Always export root .env from azd so Python uses the exact same set
    export_root_env_from_azd(env=azure_env_name, root_path=Path(".env"))
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
