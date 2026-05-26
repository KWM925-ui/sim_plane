#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/coco/sim_plane_ws"
UPSTREAM_DIR="$ROOT_DIR/src/labs/HKU_MARS_Lab/MARSIM"
UTILS_DIR="$ROOT_DIR/src/labs/ZJU_FAST_Lab/ego-planner-swarm/src/uav_simulator/Utils/cmake_utils"
WORKSPACE_DIR="$ROOT_DIR/workspaces/ros1_marsim"
SRC_DIR="$WORKSPACE_DIR/src"
GLFW_TOOLCHAIN_DIR="$ROOT_DIR/toolchains/glfw/install"

if [[ ! -d "$UPSTREAM_DIR" ]]; then
  echo "Upstream checkout not found: $UPSTREAM_DIR"
  echo "Run python3 scripts/sync_upstreams.py first."
  exit 1
fi

if [[ ! -d "$UTILS_DIR" ]]; then
  echo "Required cmake_utils checkout not found: $UTILS_DIR"
  echo "Ensure ego-planner-swarm has been synced under /home/coco/sim_plane_ws/src first."
  exit 1
fi

source /opt/ros/noetic/setup.bash

if [[ -d "$GLFW_TOOLCHAIN_DIR" ]]; then
  export CMAKE_PREFIX_PATH="$GLFW_TOOLCHAIN_DIR${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
  export CMAKE_INCLUDE_PATH="$GLFW_TOOLCHAIN_DIR/include${CMAKE_INCLUDE_PATH:+:$CMAKE_INCLUDE_PATH}"
  export CMAKE_LIBRARY_PATH="$GLFW_TOOLCHAIN_DIR/lib:$GLFW_TOOLCHAIN_DIR/lib64${CMAKE_LIBRARY_PATH:+:$CMAKE_LIBRARY_PATH}"
  export PKG_CONFIG_PATH="$GLFW_TOOLCHAIN_DIR/lib/pkgconfig:$GLFW_TOOLCHAIN_DIR/lib64/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
  export LD_LIBRARY_PATH="$GLFW_TOOLCHAIN_DIR/lib:$GLFW_TOOLCHAIN_DIR/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  echo "Using local glfw toolchain from $GLFW_TOOLCHAIN_DIR"
fi

declare -a EXTRA_CMAKE_ARGS=()
if [[ -d "$GLFW_TOOLCHAIN_DIR/lib/cmake/glfw3" ]]; then
  EXTRA_CMAKE_ARGS+=("-Dglfw3_DIR=$GLFW_TOOLCHAIN_DIR/lib/cmake/glfw3")
fi
if [[ -f "$GLFW_TOOLCHAIN_DIR/include/GLFW/glfw3.h" ]]; then
  EXTRA_CMAKE_ARGS+=("-DGLFW3_INCLUDE_DIR=$GLFW_TOOLCHAIN_DIR/include")
fi
if [[ -f "$GLFW_TOOLCHAIN_DIR/lib/libglfw3.a" ]]; then
  EXTRA_CMAKE_ARGS+=("-DGLFW3_LIBRARY=$GLFW_TOOLCHAIN_DIR/lib/libglfw3.a")
fi

mkdir -p "$SRC_DIR"

if [[ ! -e "$SRC_DIR/CMakeLists.txt" ]]; then
  catkin_init_workspace "$SRC_DIR"
fi

declare -a LINKS=(
  "cascadePID:$UPSTREAM_DIR/cascadePID"
  "local_sensing:$UPSTREAM_DIR/local_sensing"
  "map_generator:$UPSTREAM_DIR/map_generator"
  "mars_drone_sim:$UPSTREAM_DIR/mars_drone_sim"
  "mars_quadrotor_msgs:$UPSTREAM_DIR/Utils/mars_quadrotor_msgs"
  "odom_visualization:$UPSTREAM_DIR/Utils/odom_visualization"
  "pose_utils:$UPSTREAM_DIR/Utils/pose_utils"
  "rviz_plugins:$UPSTREAM_DIR/Utils/rviz_plugins"
  "test_interface:$UPSTREAM_DIR/test_interface"
  "uav_utils:$UPSTREAM_DIR/Utils/uav_utils"
  "waypoint_generator:$UPSTREAM_DIR/Utils/waypoint_generator"
  "cmake_utils:$UTILS_DIR"
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
  "${EXTRA_CMAKE_ARGS[@]}" \
  -Wno-dev \
  -Wno-deprecated
