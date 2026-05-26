#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/coco/sim_plane_ws"
TOOLCHAIN_DIR="$ROOT_DIR/toolchains/glfw"
SRC_DIR="$TOOLCHAIN_DIR/src"
BUILD_DIR="$TOOLCHAIN_DIR/build"
INSTALL_DIR="$TOOLCHAIN_DIR/install"
GLFW_REPO_URL="${GLFW_REPO_URL:-https://github.com/glfw/glfw.git}"
GLFW_REF="${GLFW_REF:-3.3.10}"

mkdir -p "$TOOLCHAIN_DIR"

if [[ ! -d "$SRC_DIR/.git" ]]; then
  rm -rf "$SRC_DIR"
  git clone --branch "$GLFW_REF" --depth 1 "$GLFW_REPO_URL" "$SRC_DIR"
else
  git -C "$SRC_DIR" fetch --depth 1 origin "$GLFW_REF"
  git -C "$SRC_DIR" checkout -f "$GLFW_REF"
fi

cmake -S "$SRC_DIR" -B "$BUILD_DIR" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" \
  -DGLFW_BUILD_DOCS=OFF \
  -DGLFW_BUILD_TESTS=OFF \
  -DGLFW_BUILD_EXAMPLES=OFF

cmake --build "$BUILD_DIR" -j"$(nproc)"
cmake --install "$BUILD_DIR"

echo "glfw toolchain installed at $INSTALL_DIR"
