#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_PX4_DIR="/home/coco/sim_plane_ws/src/core/PX4-Autopilot"
PX4_DIR="${PX4_AUTOPILOT_DIR:-$DEFAULT_PX4_DIR}"

cd "$ROOT_DIR"

if [[ ! -f "$PX4_DIR/ROMFS/px4fmu_common/init.d-posix/rcS" ]]; then
  echo "PX4 checkout not found at: $PX4_DIR"
  echo "Set PX4_AUTOPILOT_DIR to override the default managed path."
  exit 1
fi

python3 -m sim_plane run scenarios/px4_sih_quadx.json --visualize --px4-dir "$PX4_DIR" --qgc "$@"
