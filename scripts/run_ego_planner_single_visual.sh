#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

./scripts/build_ego_planner_ws.sh >/dev/null
python3 -m sim_plane run scenarios/ego_planner_single_visual.json --artifact-root /home/coco/sim_plane/runs --visualize "$@"
