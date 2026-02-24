#!/usr/bin/env bash
set -euo pipefail

# Print command usage and argument descriptions.
usage() {
    cat <<'EOF'
Usage:
  ./build_stl_from_png.sh <image_path> <output_path> <resolution_m_per_px> <height_m>

Description:
  Creates (re-uses) a virtual environment in /tmp/build_stl_from_png, installs
  required Python dependencies there, and executes the Python script to
  generate an STL from a PNG floor plan.
  The input image must use black for obstacles and white for free space.

Positional arguments (required):
  image_path           Path to the input PNG image.
  output_path          Path to the output STL file.
  resolution_m_per_px  Resolution in meters per pixel (float > 0).
  height_m             Height of the walls in meters (float > 0).
EOF
}

# Emit timestamped log messages in UTC.
log() { printf '[%s] %s\n' "$(date -u +'%Y-%m-%d_%H-%M-%S')" "$*"; }

# Fail fast when a required command is not available.
require_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        log "ERROR: Missing required command: ${cmd}"
        exit 1
    fi
}

# Install system package that provides python3 venv support.
install_python_venv_package() {
    require_cmd apt-get

    # Install venv support from distro packages when ensurepip is missing.
    log "INFO: Installing python3-venv ..."

    if ! "${SUDO_CMD[@]}" env "${APT_ENV[@]}" apt-get "${APT_GET_OPTS[@]}" update; then
        return 1
    fi

    "${SUDO_CMD[@]}" env "${APT_ENV[@]}" apt-get "${APT_GET_OPTS[@]}" install python3-venv
}

# Argument parsing (required positional args)
require_cmd getopt

# Keep sudo invocation optional so the same command works as root and non-root.
SUDO_CMD=()

if [ "$(id -u)" -ne 0 ]; then
    require_cmd sudo
    SUDO_CMD=(sudo)
fi

APT_ENV=(DEBIAN_FRONTEND=noninteractive)
APT_GET_OPTS=(-y -q)

# Parse only help flags; script inputs are required positional parameters.
SHORT_OPTS="h"
LONG_OPTS="help"
PARSED_ARGS="$(getopt --options "${SHORT_OPTS}" --longoptions "${LONG_OPTS}" --name "$0" -- "$@")" || {
    usage
    exit 2
}

eval set -- "${PARSED_ARGS}"

while true; do
    case "$1" in
    -h | --help)
        usage
        exit 0
        ;;
    --)
        shift
        break
        ;;
    *)
        log "ERROR: Unexpected option: $1"
        usage
        exit 2
        ;;
    esac
done

if [ "$#" -ne 4 ]; then
    log "ERROR: Expected 4 required positional arguments: <image_path> <output_path> <resolution_m_per_px> <height_m>"
    usage
    exit 2
fi

IMAGE="${1}"
OUTPUT="${2}"
RESOLUTION="${3}"
HEIGHT="${4}"

# Python runtime check
require_cmd python3

VENV_DIR="/tmp/build_stl_from_png"
VENV_ACTIVATED=0

# Deactivate virtual environment on exit when it was activated.
cleanup() {
    # Always deactivate if activation succeeded, even on failures.
    if [ "${VENV_ACTIVATED}" -eq 1 ] && declare -F deactivate >/dev/null 2>&1; then
        deactivate || true
        log "INFO: Virtual environment deactivated: ${VENV_DIR}"
    fi
}

# Ensure cleanup runs on every script exit path (success or failure).
trap cleanup EXIT

# Create and activate virtual environment
if [ -d "${VENV_DIR}" ] && [ ! -f "${VENV_DIR}/bin/activate" ]; then
    # Remove broken leftovers so creation starts from a clean state.
    log "INFO: Incomplete virtual environment detected. Recreating ${VENV_DIR}..."
    rm -rf "${VENV_DIR}"
fi

# Create the virtual environment when missing; if creation fails due to missing
# venv support, install python3-venv and retry once.
if [ ! -d "${VENV_DIR}" ]; then
    log "INFO: Creating virtual environment at ${VENV_DIR}..."

    if ! python3 -m venv "${VENV_DIR}"; then
        log "INFO: python3 -m venv failed. Installing system venv package and retrying..."
        rm -rf "${VENV_DIR}"

        if ! install_python_venv_package; then
            log "ERROR: Failed to install required python venv package."
            exit 1
        fi

        if ! python3 -m venv "${VENV_DIR}"; then
            log "ERROR: Failed to create virtual environment at ${VENV_DIR} after installing venv package."
            exit 1
        fi
    fi
else
    log "INFO: Reusing existing virtual environment: ${VENV_DIR}"
fi

if [ ! -f "${VENV_DIR}/bin/activate" ]; then
    log "ERROR: Virtual environment is incomplete: ${VENV_DIR}/bin/activate not found."
    exit 1
fi

# shellcheck disable=SC1091
# Source activation script to bind python/pip to the virtual environment.
source "${VENV_DIR}/bin/activate"
VENV_ACTIVATED=1
log "INFO: Virtual environment activated: ${VIRTUAL_ENV}"

# Install dependencies inside virtual environment
log "INFO: Installing/updating Python dependencies in virtual environment..."
if ! python -m pip install --upgrade pip setuptools wheel; then
    log "ERROR: Failed to update pip tooling in virtual environment."
    exit 1
fi

# Use fixed package versions to keep a reproducible and compatible geometry toolchain.
# mapbox-earcut provides polygon triangulation required by trimesh.extrude_polygon.
PYTHON_DEPS=(
    "numpy==1.26.4"
    "scipy==1.11.4"
    "opencv-python==4.10.0.84"
    "trimesh==4.11.2"
    "shapely==2.1.2"
    "mapbox-earcut==2.0.0"
)

if ! python -m pip install --upgrade "${PYTHON_DEPS[@]}"; then
    log "ERROR: Failed to install Python dependencies in virtual environment."
    exit 1
fi

# Execute Python script
log "INFO: Executing generator script..."

# Resolve Python script relative to this shell script so it works from any cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/build_stl_from_png.py"

if [ ! -f "${PY_SCRIPT}" ]; then
    log "ERROR: Python script not found: ${PY_SCRIPT}"
    exit 1
fi

if ! python "${PY_SCRIPT}" "${IMAGE}" "${RESOLUTION}" "${HEIGHT}" --output "${OUTPUT}"; then
    log "ERROR: The Python script failed to execute properly."
    exit 1
fi

log "INFO: Workflow completed successfully."
