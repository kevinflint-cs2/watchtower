#!/usr/bin/env bash
# This rcfile is intended to be used as an --rcfile for bash launched by VS Code terminal/profile
# Source VS Code shell integration if it exists (keeps existing features)
if [ -f "/vscode/bin/linux-x64/*/out/vs/workbench/contrib/terminal/common/scripts/shellIntegration-bash.sh" ]; then
  # best-effort: try to source the integration file if path is known
  for f in /vscode/bin/linux-x64/*/out/vs/workbench/contrib/terminal/common/scripts/shellIntegration-bash.sh; do
    [ -f "$f" ] && source "$f" && break
  done
fi
# Activate project venv if present
# Compute project root relative to this rc file (two levels up: .vscode/..)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
  # shellcheck disable=SC1090
  source "$PROJECT_ROOT/.venv/bin/activate"
fi
# load user's .bashrc as well
[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc"

# finally, set prompt and start interactive shell
PS1="(project) $PS1"
