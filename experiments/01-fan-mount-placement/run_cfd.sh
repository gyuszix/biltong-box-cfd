#!/usr/bin/env bash
# Mesh + solve one biltong-box fan-mount variant with OpenFOAM, via Docker.
#
# Usage:
#   ./run_cfd.sh side_mount
#   ./run_cfd.sh lid_mount
#
# Requires setup_cfd_cases.py to have been run first (creates the case dirs
# and copies in the STL patches). Logs go to log.<step> inside the case dir.

set -euo pipefail

IMAGE="opencfd/openfoam-default:2512"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VARIANT="${1:-}"
case "$VARIANT" in
    side_mount) CASE_DIR="case-side-mount" ;;
    lid_mount)  CASE_DIR="case-top-mount" ;;
    *)
        echo "Usage: $0 <side_mount|lid_mount>" >&2
        exit 1
        ;;
esac

if [ ! -d "$ROOT_DIR/$CASE_DIR/system" ]; then
    echo "ERROR: $CASE_DIR not set up. Run 'python3 setup_cfd_cases.py' first." >&2
    exit 1
fi

run_step() {
    local step="$1"
    shift
    echo ">>> [$VARIANT] $step"
    # NB: the image's entrypoint (/openfoam/run) unconditionally cd's to
    # $HOME before exec'ing our command, so -w is ignored - cd explicitly
    # inside the command instead.
    if ! docker run --rm \
        -v "$ROOT_DIR":/work \
        "$IMAGE" \
        bash -c "set -o pipefail; cd /work/$CASE_DIR && ($* 2>&1 | tee log.$step)"; then
        echo "!!! $step FAILED for $VARIANT — see $CASE_DIR/log.$step" >&2
        exit 1
    fi
    # tee swallows the inner command's exit code from bash -c's perspective in
    # some shells; double check the log for OpenFOAM's own "FOAM FATAL ERROR".
    if grep -q "FOAM FATAL ERROR" "$ROOT_DIR/$CASE_DIR/log.$step"; then
        echo "!!! $step reported a FOAM FATAL ERROR for $VARIANT — see $CASE_DIR/log.$step" >&2
        exit 1
    fi
}

echo "=== Running CFD for variant: $VARIANT ($CASE_DIR) ==="

run_step blockMesh "blockMesh"
run_step snappyHexMesh "snappyHexMesh -overwrite"
run_step checkMesh "checkMesh"
run_step simpleFoam "simpleFoam"

echo "=== Done: $VARIANT ==="
echo "Logs in $CASE_DIR/log.{blockMesh,snappyHexMesh,checkMesh,simpleFoam}"
