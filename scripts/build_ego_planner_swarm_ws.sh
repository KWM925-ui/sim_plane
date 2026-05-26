#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/coco/sim_plane_ws"
UPSTREAM_DIR="$ROOT_DIR/src/labs/ZJU_FAST_Lab/ego-planner-swarm"
WORKSPACE_DIR="$ROOT_DIR/workspaces/ros1_ego_swarm"
SRC_DIR="$WORKSPACE_DIR/src"
LINK_PATH="$SRC_DIR/ego-planner-swarm"

if [[ ! -d "$UPSTREAM_DIR" ]]; then
  echo "Upstream checkout not found: $UPSTREAM_DIR"
  echo "Run python3 scripts/sync_upstreams.py first."
  exit 1
fi

source /opt/ros/noetic/setup.bash

mkdir -p "$SRC_DIR"

if [[ ! -e "$SRC_DIR/CMakeLists.txt" ]]; then
  catkin_init_workspace "$SRC_DIR"
fi

if [[ -L "$LINK_PATH" ]]; then
  :
elif [[ -e "$LINK_PATH" ]]; then
  echo "Workspace path already exists and is not a symlink: $LINK_PATH"
  exit 1
else
  ln -s "$UPSTREAM_DIR" "$LINK_PATH"
fi

cd "$WORKSPACE_DIR"
catkin_make -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -j1 "$@"
