#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PX4_DIR="${PX4_AUTOPILOT_DIR:-/home/coco/sim_plane_ws/src/core/PX4-Autopilot}"

SCENARIOS=(
  "scenarios/px4_sih_quadx_human_follow_case_acquire_center.json"
  "scenarios/px4_sih_quadx_human_follow_case_search_reacquire_right.json"
  "scenarios/px4_sih_quadx_human_follow_case_search_reacquire_left.json"
  "scenarios/px4_sih_quadx_human_follow_case_person_approach_retreat.json"
  "scenarios/px4_sih_quadx_human_follow_case_person_depart_follow.json"
  "scenarios/px4_sih_quadx_human_follow_case_lateral_left_track.json"
  "scenarios/px4_sih_quadx_human_follow_case_lateral_right_track.json"
)

cd "${ROOT_DIR}"

for scenario in "${SCENARIOS[@]}"; do
  echo "[stage1_behavior_matrix] running ${scenario}"
  python3 -m sim_plane run "${scenario}" --artifact-root "${ROOT_DIR}/runs" --px4-dir "${PX4_DIR}" --no-hold-open "$@"
done
