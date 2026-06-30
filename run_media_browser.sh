#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="${ROOT_DIR}/api_keys.json"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  CONFIG_PATH="${HOME}/.davinci_plugins/api_keys.json"
fi

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"
exec "${PYTHON_BIN}" -m media_browser.main --config "${CONFIG_PATH}"
