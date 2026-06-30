#!/usr/bin/env bash
set -euo pipefail

KEEP_USER_DATA=1
for arg in "$@"; do
  case "${arg}" in
    --remove-user-data)
      KEEP_USER_DATA=0
      ;;
    -h|--help)
      cat <<EOF
Usage: ./uninstall.sh [--remove-user-data]

Removes the installed Resolve launcher, Workflow Integration panel, and plugin
runtime copy. By default API keys, settings, and cached media are kept.

Options:
  --remove-user-data   Also remove ~/.davinci_plugins/api_keys.json, settings,
                       and cache data.
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      exit 1
      ;;
  esac
done

PLUGIN_HOME="${HOME}/.davinci_plugins"
PLUGIN_DIR="${PLUGIN_HOME}/media_browser"
SCRIPT_PATH="${HOME}/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/Online Media Browser.py"
WFI_PLUGIN_DIR="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/io.github.davincionlinemediabrowser.resolve"

rm -rf "${PLUGIN_DIR}"
rm -f "${SCRIPT_PATH}"

if [[ -d "${WFI_PLUGIN_DIR}" ]]; then
  if rm -rf "${WFI_PLUGIN_DIR}" 2>/dev/null; then
    :
  else
    echo "Could not remove Workflow Integration without sudo:"
    echo "  sudo rm -rf '${WFI_PLUGIN_DIR}'"
  fi
fi

if [[ "${KEEP_USER_DATA}" == "0" ]]; then
  rm -f "${PLUGIN_HOME}/api_keys.json" "${PLUGIN_HOME}/settings.json" "${PLUGIN_HOME}/wfi-window-state.json"
  rm -rf "${PLUGIN_HOME}/cache"
fi

echo "Uninstalled DaVinci Online Media Browser."
if [[ "${KEEP_USER_DATA}" == "1" ]]; then
  echo "Kept user data in: ${PLUGIN_HOME}"
fi
