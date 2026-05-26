#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/coco/sim_plane_ws/toolchains"
JDK_DIR="$ROOT_DIR/jdk-17"
ANT_DIR="$ROOT_DIR/apache-ant-1.10.17"
TMP_DIR="$ROOT_DIR/.downloads"

mkdir -p "$ROOT_DIR" "$TMP_DIR"

JDK_ARCHIVE="$TMP_DIR/temurin17.tar.gz"
ANT_ARCHIVE="$TMP_DIR/apache-ant-1.10.17-bin.tar.gz"

if [[ ! -x "$JDK_DIR/bin/java" ]]; then
  rm -rf "$JDK_DIR"
  rm -rf "$TMP_DIR"/jdk-*
  curl -L "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse" -o "$JDK_ARCHIVE"
  tar -xzf "$JDK_ARCHIVE" -C "$TMP_DIR"
  EXTRACTED_JDK="$(find "$TMP_DIR" -maxdepth 1 -type d -name 'jdk-*' | head -n 1)"
  mv "$EXTRACTED_JDK" "$JDK_DIR"
fi

if [[ ! -x "$ANT_DIR/bin/ant" ]]; then
  rm -rf "$ANT_DIR"
  curl -L "https://downloads.apache.org/ant/binaries/apache-ant-1.10.17-bin.tar.gz" -o "$ANT_ARCHIVE"
  tar -xzf "$ANT_ARCHIVE" -C "$ROOT_DIR"
fi

echo "JDK: $JDK_DIR"
echo "Ant: $ANT_DIR"
echo "Add to PATH when needed:"
echo "  export JAVA_HOME=$JDK_DIR"
echo "  export PATH=$JDK_DIR/bin:$ANT_DIR/bin:\$PATH"
