#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${SIM_PLANE_HOME:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}
cd "$REPO_ROOT"
python3 -m sim_plane run scenarios/basic_takeoff.json --artifact-root "$REPO_ROOT/runs" --visualize "$@"
