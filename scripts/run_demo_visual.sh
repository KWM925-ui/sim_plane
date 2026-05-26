#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 -m sim_plane run scenarios/basic_takeoff.json --visualize
