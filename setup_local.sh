#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
INSTALL_LEGACY_UI=0

for arg in "$@"; do
  case "${arg}" in
    --legacy-ui)
      INSTALL_LEGACY_UI=1
      ;;
    -h|--help)
      cat <<EOF
Usage: ./setup_local.sh [--legacy-ui]

Default setup installs only the lightweight Web/WFI runtime dependencies.

Options:
  --legacy-ui   Install the old PySide6 desktop UI dependency.
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/requirements.txt"

if [[ "${INSTALL_LEGACY_UI}" == "1" ]]; then
  "${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/requirements-legacy-ui.txt"
fi

echo "Local UI environment is ready:"
echo "  ${VENV_DIR}/bin/python"
echo
echo "Launch with:"
echo "  ${ROOT_DIR}/run_web_browser.sh"
if [[ "${INSTALL_LEGACY_UI}" == "1" ]]; then
  echo "  ${ROOT_DIR}/run_media_browser.sh"
fi
