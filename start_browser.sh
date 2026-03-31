#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
BOOTSTRAP_MARKER="$VENV_DIR/.stupid_browser_ready"

if [[ ! -d "$VENV_DIR" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python 3.10+ is required but was not found in PATH."
    exit 1
  fi

  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [[ ! -f "$BOOTSTRAP_MARKER" || "$ROOT_DIR/pyproject.toml" -nt "$BOOTSTRAP_MARKER" ]]; then
  python -m pip install -e "$ROOT_DIR"
  touch "$BOOTSTRAP_MARKER"
fi

cd "$ROOT_DIR"
python -m stupid_browser_scratch.main "$@"
