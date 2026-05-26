#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/coco/sim_plane_ws"
UPSTREAM_DIR="$ROOT_DIR/src/labs/HKU_MARS_Lab/SUPER"
WORKSPACE_DIR="$ROOT_DIR/workspaces/ros1_super"
SRC_DIR="$WORKSPACE_DIR/src"
GLFW_TOOLCHAIN_DIR="$ROOT_DIR/toolchains/glfw/install"

if [[ ! -d "$UPSTREAM_DIR" ]]; then
  echo "Upstream checkout not found: $UPSTREAM_DIR"
  echo "Run python3 scripts/sync_upstreams.py first."
  exit 1
fi

source /opt/ros/noetic/setup.bash
export ROS_VERSION=1
export ROS_DISTRO=noetic

if [[ -d "$GLFW_TOOLCHAIN_DIR" ]]; then
  export CMAKE_PREFIX_PATH="$GLFW_TOOLCHAIN_DIR${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
  export CMAKE_INCLUDE_PATH="$GLFW_TOOLCHAIN_DIR/include${CMAKE_INCLUDE_PATH:+:$CMAKE_INCLUDE_PATH}"
  export CMAKE_LIBRARY_PATH="$GLFW_TOOLCHAIN_DIR/lib:$GLFW_TOOLCHAIN_DIR/lib64${CMAKE_LIBRARY_PATH:+:$CMAKE_LIBRARY_PATH}"
  export PKG_CONFIG_PATH="$GLFW_TOOLCHAIN_DIR/lib/pkgconfig:$GLFW_TOOLCHAIN_DIR/lib64/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
  export LD_LIBRARY_PATH="$GLFW_TOOLCHAIN_DIR/lib:$GLFW_TOOLCHAIN_DIR/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

mkdir -p "$SRC_DIR"

if [[ ! -e "$SRC_DIR/CMakeLists.txt" ]]; then
  catkin_init_workspace "$SRC_DIR"
fi

LINK_PATH="$SRC_DIR/SUPER"
if [[ -L "$LINK_PATH" ]]; then
  if [[ "$(readlink -f "$LINK_PATH")" != "$(readlink -f "$UPSTREAM_DIR")" ]]; then
    rm -f "$LINK_PATH"
    ln -s "$UPSTREAM_DIR" "$LINK_PATH"
  fi
elif [[ -e "$LINK_PATH" ]]; then
  echo "Workspace path already exists and is not a symlink: $LINK_PATH"
  exit 1
else
  ln -s "$UPSTREAM_DIR" "$LINK_PATH"
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

cd "$WORKSPACE_DIR"
catkin_make \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -j1 \
  "$@" \
  --cmake-args \
  "${EXTRA_CMAKE_ARGS[@]}"
