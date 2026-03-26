#!/usr/bin/env bash
set -euo pipefail

# Print UTC timestamps so rebuild logs are easy to compare across runs.
log() { printf '[%s] %s\n' "$(date -u +'%Y-%m-%d_%H-%M-%S')" "$*"; }

if [ "$#" -ne 0 ]; then
    log "ERROR: This script does not accept arguments."
    exit 2
fi

# Resolve package-local paths so this script can be executed from any working
# directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_SCRIPT="${PACKAGE_DIR}/scripts/build_stl_from_png.sh"

IMG_NAME="office_environment_1"
INPUT_IMAGE="${SCRIPT_DIR}/${IMG_NAME}.png"
OUTPUT_STL="${SCRIPT_DIR}/${IMG_NAME}.stl"
RESOLUTION="0.01258" # m/px
HEIGHT="2.5"         # m

# Validate the fixed inputs used by this environment-specific rebuild helper.
if [ ! -f "${BUILD_SCRIPT}" ]; then
    log "ERROR: build script not found: ${BUILD_SCRIPT}"
    exit 1
fi

if [ ! -f "${INPUT_IMAGE}" ]; then
    log "ERROR: input image not found: ${INPUT_IMAGE}"
    exit 1
fi

# Rebuild the office mesh using the checked-in resolution and wall height.
log "INFO: Building ${IMG_NAME} STL..."
if ! "${BUILD_SCRIPT}" "${INPUT_IMAGE}" "${OUTPUT_STL}" "${RESOLUTION}" "${HEIGHT}"; then
    log "ERROR: ${IMG_NAME} STL generation failed."
    exit 1
fi

log "INFO: ${IMG_NAME} STL created at: ${OUTPUT_STL}"
