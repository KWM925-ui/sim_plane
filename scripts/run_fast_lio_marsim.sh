#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

./scripts/build_marsim_ws.sh >/dev/null
./scripts/build_fast_lio_ws.sh >/dev/null
python3 -m sim_plane run scenarios/fast_lio_marsim.json --artifact-root /home/coco/sim_plane/runs "$@"
