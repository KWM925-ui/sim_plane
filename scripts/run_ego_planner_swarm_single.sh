#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${SIM_PLANE_HOME:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}
cd "$REPO_ROOT"

./scripts/build_ego_planner_swarm_ws.sh >/dev/null
python3 -m sim_plane run scenarios/ego_planner_swarm_single.json --artifact-root "$REPO_ROOT/runs" "$@"
