#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PX4_DIR="${PX4_AUTOPILOT_DIR:-/home/coco/sim_plane_ws/src/core/PX4-Autopilot}"

"${ROOT_DIR}/scripts/sync_human_follow_stage1_workspace.sh"
"${ROOT_DIR}/scripts/build_human_follow_stage1_ws.sh"

cd "${ROOT_DIR}"
python3 -m sim_plane run \
  scenarios/px4_sih_quadx_human_follow_user_planning_ingress.json \
  --artifact-root "${ROOT_DIR}/runs" \
  --px4-dir "${PX4_DIR}" \
  --no-hold-open \
  "$@"
