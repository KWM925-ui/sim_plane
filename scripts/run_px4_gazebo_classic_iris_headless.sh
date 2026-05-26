#!/usr/bin/env bash

set -euo pipefail

PX4_DIR=${PX4_DIR:-/home/coco/sim_plane_ws/src/core/PX4-Autopilot}

cd /home/coco/sim_plane
python3 -m sim_plane run scenarios/px4_gazebo_classic_iris_headless.json --artifact-root /home/coco/sim_plane/runs --px4-dir "$PX4_DIR" "$@"
