#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/coco/sim_plane_ws"
FAST_LIO_DIR="$ROOT_DIR/src/labs/HKU_MARS_Lab/FAST_LIO"
LIVOX_DRIVER_REPO="$ROOT_DIR/src/deps/Livox_SDK/livox_ros_driver"
LIVOX_DRIVER_PKG="$LIVOX_DRIVER_REPO/livox_ros_driver"
WORKSPACE_DIR="$ROOT_DIR/workspaces/ros1_fast_lio"
SRC_DIR="$WORKSPACE_DIR/src"

if [[ ! -d "$FAST_LIO_DIR" ]]; then
  echo "FAST_LIO checkout not found: $FAST_LIO_DIR"
  echo "Run python3 scripts/sync_upstreams.py --names FAST_LIO first."
  exit 1
fi

if [[ ! -d "$LIVOX_DRIVER_PKG" ]]; then
  echo "livox_ros_driver package not found: $LIVOX_DRIVER_PKG"
  echo "Run python3 scripts/sync_upstreams.py --names livox_ros_driver first."
  exit 1
fi

source /opt/ros/noetic/setup.bash

mkdir -p "$SRC_DIR"

if [[ ! -e "$SRC_DIR/CMakeLists.txt" ]]; then
  catkin_init_workspace "$SRC_DIR"
fi

declare -a LINKS=(
  "FAST_LIO:$FAST_LIO_DIR"
  "livox_ros_driver:$LIVOX_DRIVER_PKG"
)

for entry in "${LINKS[@]}"; do
  name="${entry%%:*}"
  target="${entry#*:}"
  link_path="$SRC_DIR/$name"
  if [[ -L "$link_path" ]]; then
    if [[ "$(readlink -f "$link_path")" == "$(readlink -f "$target")" ]]; then
      continue
    fi
    rm -f "$link_path"
  elif [[ -e "$link_path" ]]; then
    echo "Workspace path already exists and is not a symlink: $link_path"
    exit 1
  fi
  ln -s "$target" "$link_path"
done

cd "$WORKSPACE_DIR"
catkin_make \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -j1 \
  "$@" \
  --cmake-args \
  -Wno-dev \
  -Wno-deprecated
