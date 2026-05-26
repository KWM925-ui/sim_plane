#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/coco/sim_plane_ws"
UPSTREAM_DIR="$ROOT_DIR/src/labs/ZJU_FAST_Lab/visPlanner"
WORKSPACE_DIR="$ROOT_DIR/workspaces/ros1_visplanner"
SRC_DIR="$WORKSPACE_DIR/src"
LINK_TARGET="$UPSTREAM_DIR/src"
LINK_PATH="$SRC_DIR/visPlanner_src"

if [[ ! -d "$UPSTREAM_DIR" ]]; then
  echo "Upstream checkout not found: $UPSTREAM_DIR"
  echo "Run python3 scripts/sync_upstreams.py first."
  exit 1
fi

if [[ ! -d "$LINK_TARGET" ]]; then
  echo "Expected source tree not found: $LINK_TARGET"
  exit 1
fi

source /opt/ros/noetic/setup.bash

mkdir -p "$SRC_DIR"

if [[ ! -e "$SRC_DIR/CMakeLists.txt" ]]; then
  catkin_init_workspace "$SRC_DIR"
fi

if [[ -L "$LINK_PATH" ]]; then
  if [[ "$(readlink -f "$LINK_PATH")" != "$(readlink -f "$LINK_TARGET")" ]]; then
    rm -f "$LINK_PATH"
    ln -s "$LINK_TARGET" "$LINK_PATH"
  fi
elif [[ -e "$LINK_PATH" ]]; then
  echo "Workspace path already exists and is not a symlink: $LINK_PATH"
  exit 1
else
  ln -s "$LINK_TARGET" "$LINK_PATH"
fi

cd "$WORKSPACE_DIR"
catkin_make \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -j1 \
  "$@"
