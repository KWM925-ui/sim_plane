#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_DIR="${1:-/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1}"

source /opt/ros/noetic/setup.bash
cd "${WORKSPACE_DIR}"
catkin_make -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -j1

