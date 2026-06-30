#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_HOME="${HOME}/.davinci_plugins"
PLUGIN_DIR="${PLUGIN_HOME}/media_browser"
SCRIPT_DIR="${HOME}/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"
SCRIPT_PATH="${SCRIPT_DIR}/Online Media Browser.py"
CONFIG_PATH="${PLUGIN_HOME}/api_keys.json"
WFI_SOURCE_DIR="${ROOT_DIR}/workflow_integration/io.github.davincionlinemediabrowser.resolve"
WFI_INSTALL_ROOT="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins"
WFI_PLUGIN_DIR="${WFI_INSTALL_ROOT}/io.github.davincionlinemediabrowser.resolve"
WFI_NODE_SOURCE="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Workflow Integrations/Examples/SamplePlugin/WorkflowIntegration.node"
INSTALL_WFI=1
WFI_INSTALLED=0

for arg in "$@"; do
  case "${arg}" in
    --no-wfi)
      INSTALL_WFI=0
      ;;
    -h|--help)
      cat <<EOF
Usage: ./install.sh [--no-wfi]

Installs the local API/Web UI and Resolve Scripts menu launcher.
Studio users also get the Workflow Integration panel unless --no-wfi is passed.

Options:
  --no-wfi   Skip installing the Resolve Studio Workflow Integration panel.
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      exit 1
      ;;
  esac
done

mkdir -p "${PLUGIN_HOME}" "${PLUGIN_DIR}" "${SCRIPT_DIR}"

rsync -a --delete \
  --exclude ".git" \
  --exclude ".claude" \
  --exclude "__pycache__" \
  --exclude ".venv" \
  --exclude "venv" \
  --exclude "dist" \
  --exclude "api_keys.json" \
  --exclude "WorkflowIntegration.node" \
  --exclude "runtime-config.json" \
  "${ROOT_DIR}/" "${PLUGIN_DIR}/"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  cp "${ROOT_DIR}/api_keys.example.json" "${CONFIG_PATH}"
fi

cat > "${SCRIPT_PATH}" <<PY
import os
import subprocess

installed_runner = os.path.expanduser("~/.davinci_plugins/media_browser/run_web_browser.sh")
dev_runner = "${ROOT_DIR}/run_web_browser.sh"
script = dev_runner if os.environ.get("DAVINCI_ONLINE_BROWSER_DEV") == "1" and os.path.exists(dev_runner) else installed_runner

subprocess.Popen(["/bin/bash", script], close_fds=True)
PY

install_wfi_plugin() {
  if [[ "${INSTALL_WFI}" != "1" ]]; then
    echo "Skipped Workflow Integration install (--no-wfi)."
    return
  fi

  if [[ ! -d "${WFI_SOURCE_DIR}" ]]; then
    echo "Workflow Integration source not found, skipped: ${WFI_SOURCE_DIR}"
    return
  fi

  local runtime_config
  runtime_config="$(cat <<JSON
{
  "projectRoot": "${PLUGIN_DIR}",
  "configPath": "${CONFIG_PATH}",
  "python": ""
}
JSON
)"

  install_wfi_without_sudo() {
    mkdir -p "${WFI_PLUGIN_DIR}" &&
      rsync -a --delete \
        --exclude "WorkflowIntegration.node" \
        --exclude "runtime-config.json" \
        "${WFI_SOURCE_DIR}/" "${WFI_PLUGIN_DIR}/" &&
      {
        if [[ -f "${WFI_NODE_SOURCE}" ]]; then
          cp "${WFI_NODE_SOURCE}" "${WFI_PLUGIN_DIR}/WorkflowIntegration.node"
        else
          echo "Warning: WorkflowIntegration.node not found at:"
          echo "  ${WFI_NODE_SOURCE}"
          echo "The Studio panel will not load until this file is copied into:"
          echo "  ${WFI_PLUGIN_DIR}"
        fi
      } &&
      printf "%s\n" "${runtime_config}" > "${WFI_PLUGIN_DIR}/runtime-config.json"
  }

  install_wfi_with_sudo() {
    if ! command -v sudo >/dev/null 2>&1; then
      return 1
    fi
    echo "Administrator permission is needed to install the Studio Workflow Integration panel."
    sudo mkdir -p "${WFI_PLUGIN_DIR}" &&
      sudo rsync -a --delete \
        --exclude "WorkflowIntegration.node" \
        --exclude "runtime-config.json" \
        "${WFI_SOURCE_DIR}/" "${WFI_PLUGIN_DIR}/" &&
      {
        if [[ -f "${WFI_NODE_SOURCE}" ]]; then
          sudo cp "${WFI_NODE_SOURCE}" "${WFI_PLUGIN_DIR}/WorkflowIntegration.node"
        else
          echo "Warning: WorkflowIntegration.node not found at:"
          echo "  ${WFI_NODE_SOURCE}"
          echo "The Studio panel will not load until this file is copied into:"
          echo "  ${WFI_PLUGIN_DIR}"
        fi
      } &&
      printf "%s\n" "${runtime_config}" | sudo tee "${WFI_PLUGIN_DIR}/runtime-config.json" >/dev/null
  }

  if install_wfi_without_sudo 2>/dev/null || install_wfi_with_sudo; then
    WFI_INSTALLED=1
  else
    echo "Skipped Studio Workflow Integration install."
    echo "You can still use: Workspace -> Scripts -> Utility -> Online Media Browser"
    echo "To retry the Studio panel later, rerun: ./install.sh"
  fi
}

install_wfi_plugin

echo "Installed plugin files to: ${PLUGIN_DIR}"
echo "Installed Resolve launcher to: ${SCRIPT_PATH}"
if [[ "${WFI_INSTALLED}" == "1" ]]; then
  echo "Installed Studio Workflow Integration to: ${WFI_PLUGIN_DIR}"
elif [[ "${INSTALL_WFI}" == "1" ]]; then
  echo "Studio Workflow Integration was not installed. Browser/Scripts mode is available."
fi
echo "Edit keys here: ${CONFIG_PATH}"
