#!/usr/bin/env bash

set -euo pipefail

TOOLCHAIN_ROOT="/home/coco/sim_plane_ws/toolchains/flightgear"
INSTALL_ROOT="$TOOLCHAIN_ROOT/install"
DOWNLOAD_ROOT="$TOOLCHAIN_ROOT/downloads"
WRAPPER_DIR="$TOOLCHAIN_ROOT/bin"

PACKAGES=(
  flightgear
  flightgear-data-base
  flightgear-data-models
  flightgear-data-ai
  libopenscenegraph160
  libopenthreads21
  libplib1
  libhtsengine1
  libudns0
)

mkdir -p "$INSTALL_ROOT" "$DOWNLOAD_ROOT" "$WRAPPER_DIR"

cd "$DOWNLOAD_ROOT"
for pkg in "${PACKAGES[@]}"; do
  if ! ls "${pkg}"_*.deb >/dev/null 2>&1; then
    apt download "$pkg"
  fi
done

for deb in ./*.deb; do
  dpkg-deb -x "$deb" "$INSTALL_ROOT"
done

cat >"$WRAPPER_DIR/fgfs" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TOOLCHAIN_ROOT=$(cd "$SELF_DIR/.." && pwd)
INSTALL_ROOT="$TOOLCHAIN_ROOT/install"
REAL_BINARY="$INSTALL_ROOT/usr/games/fgfs"
FG_ROOT_DEFAULT="$INSTALL_ROOT/usr/share/games/flightgear"
LIB_DIRS=(
  "$INSTALL_ROOT/usr/lib/x86_64-linux-gnu"
  "$INSTALL_ROOT/lib/x86_64-linux-gnu"
  "$INSTALL_ROOT/usr/lib"
  "$INSTALL_ROOT/lib"
)

if [[ ! -x "$REAL_BINARY" ]]; then
  echo "FlightGear binary missing at $REAL_BINARY" >&2
  exit 1
fi

export FG_ROOT="${FG_ROOT:-$FG_ROOT_DEFAULT}"
export FG_HOME="${FG_HOME:-$TOOLCHAIN_ROOT/home}"
mkdir -p "$FG_HOME"

EXTRA_LD=""
for dir in "${LIB_DIRS[@]}"; do
  if [[ -d "$dir" ]]; then
    if [[ -z "$EXTRA_LD" ]]; then
      EXTRA_LD="$dir"
    else
      EXTRA_LD="$EXTRA_LD:$dir"
    fi
  fi
done
if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
  export LD_LIBRARY_PATH="$EXTRA_LD:$LD_LIBRARY_PATH"
else
  export LD_LIBRARY_PATH="$EXTRA_LD"
fi

exec "$REAL_BINARY" "$@"
EOF

chmod +x "$WRAPPER_DIR/fgfs"

echo "FlightGear local toolchain prepared under $TOOLCHAIN_ROOT"
echo "Binary wrapper: $WRAPPER_DIR/fgfs"
echo "FG_ROOT: $INSTALL_ROOT/usr/share/games/flightgear"
