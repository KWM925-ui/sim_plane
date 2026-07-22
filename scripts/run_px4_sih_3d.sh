#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=${SIM_PLANE_HOME:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}
DEFAULT_PX4_DIR="/home/coco/sim_plane_ws/src/core/PX4-Autopilot"
TOOLCHAIN_ROOT="/home/coco/sim_plane_ws/toolchains"
PX4_DIR="${PX4_AUTOPILOT_DIR:-$DEFAULT_PX4_DIR}"

cd "$ROOT_DIR"

if [[ ! -f "$PX4_DIR/ROMFS/px4fmu_common/init.d-posix/rcS" ]]; then
  echo "PX4 checkout not found at: $PX4_DIR"
  echo "Set PX4_AUTOPILOT_DIR to override the default managed path."
  exit 1
fi

if [[ ! -x "$TOOLCHAIN_ROOT/jdk-17/bin/java" || ! -x "$TOOLCHAIN_ROOT/apache-ant-1.10.17/bin/ant" ]]; then
  "$ROOT_DIR/scripts/bootstrap_local_jmavsim_toolchain.sh"
fi

python3 -m sim_plane run scenarios/px4_sih_quadx_3d.json --visualize --px4-dir "$PX4_DIR" --qgc --jmavsim "$@"
