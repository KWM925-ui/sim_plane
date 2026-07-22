#!/usr/bin/env bash

set -euo pipefail

PX4_DIR=${PX4_DIR:-/home/coco/sim_plane_ws/src/core/PX4-Autopilot}
REPO_ROOT=${SIM_PLANE_HOME:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}

cd "$REPO_ROOT"
python3 -m sim_plane run scenarios/px4_sih_quadx_mavsdk_action.json --artifact-root "$REPO_ROOT/runs" --px4-dir "$PX4_DIR" "$@"
