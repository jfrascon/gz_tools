#!/usr/bin/env bash
set -euo pipefail

# Print the command contract exactly as the caller should use it.
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

# Print UTC timestamps so logs stay comparable across machines and shells.
log() { printf '[%s] %s\n' "$(date -u +'%Y-%m-%d_%H-%M-%S')" "$*"; }

# Stop early when a required command is missing.
require_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        log "ERROR: Missing required command: ${cmd}"
        exit 1
    fi
}

# Install the distro package that provides `python3 -m venv`.
install_python_venv_package() {
    require_cmd apt-get

    # Some minimal Python installations do not ship `ensurepip`, so `venv`
    # exists conceptually but cannot create environments until this package is
    # installed from the OS repositories.
    log "INFO: Installing python3-venv ..."

    if ! "${SUDO_CMD[@]}" env "${APT_ENV[@]}" apt-get "${APT_GET_OPTS[@]}" update; then
        return 1
    fi

    "${SUDO_CMD[@]}" env "${APT_ENV[@]}" apt-get "${APT_GET_OPTS[@]}" install python3-venv
}

# Parse only optional flags here. The actual STL inputs remain positional.
require_cmd getopt

# Keep `sudo` optional so the same script works both as root and as a regular
# user.
SUDO_CMD=()

if [ "$(id -u)" -ne 0 ]; then
    require_cmd sudo
    SUDO_CMD=(sudo)
fi

APT_ENV=(DEBIAN_FRONTEND=noninteractive)
APT_GET_OPTS=(-y -q)

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

# The generator itself is a Python script, so Python must exist even if the
# virtual environment has not been created yet.
require_cmd python3

VENV_DIR="/tmp/build_stl_from_png"
VENV_ACTIVATED=0

# Deactivate the virtual environment on every exit path after activation.
cleanup() {
    # Always call `deactivate` if activation succeeded, even if the script
    # fails later.
    if [ "${VENV_ACTIVATED}" -eq 1 ] && declare -F deactivate >/dev/null 2>&1; then
        deactivate || true
        log "INFO: Virtual environment deactivated: ${VENV_DIR}"
    fi
}

# Register cleanup once so success and failure follow the same teardown path.
trap cleanup EXIT

# Prepare the virtual environment directory used by this workflow.
if [ -d "${VENV_DIR}" ] && [ ! -f "${VENV_DIR}/bin/activate" ]; then
    # Remove partial environments because they are usually the result of an
    # interrupted setup and are not safe to reuse.
    log "INFO: Incomplete virtual environment detected. Recreating ${VENV_DIR}..."
    rm -rf "${VENV_DIR}"
fi

# Create the environment when missing. If creation fails because the Python
# installation lacks venv support, install `python3-venv` and retry once.
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
# Source the activation script so `python` and `pip` resolve inside the virtual
# environment for the rest of this shell process.
source "${VENV_DIR}/bin/activate"
VENV_ACTIVATED=1
log "INFO: Virtual environment activated: ${VIRTUAL_ENV}"

# Install the Python packages required by the conversion pipeline.
log "INFO: Installing/updating Python dependencies in virtual environment..."
if ! python -m pip install --upgrade pip setuptools wheel; then
    log "ERROR: Failed to update pip tooling in virtual environment."
    exit 1
fi

# Keep these versions fixed so the geometry toolchain stays reproducible.
# `mapbox-earcut` provides polygon triangulation used by
# `trimesh.creation.extrude_polygon`.
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

# Execute the Python generator after the environment has been prepared.
log "INFO: Executing generator script..."

# Resolve the Python script relative to this shell script so callers can run
# this command from any working directory.
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
