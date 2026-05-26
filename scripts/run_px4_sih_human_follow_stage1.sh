#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PX4_DIR="${PX4_AUTOPILOT_DIR:-/home/coco/sim_plane_ws/src/core/PX4-Autopilot}"

cd "${ROOT_DIR}"
python3 -m sim_plane run scenarios/px4_sih_quadx_human_follow_stage1.json --artifact-root "${ROOT_DIR}/runs" --px4-dir "${PX4_DIR}" "$@"
