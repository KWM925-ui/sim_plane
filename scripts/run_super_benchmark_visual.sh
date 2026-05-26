#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE_DIR="/home/coco/sim_plane_ws/workspaces/ros1_super"

source "$REPO_ROOT/scripts/process_cleanup.sh"

REQUESTED_PORT="${SIM_PLANE_ROS_MASTER_PORT:-}"
if [[ -n "$REQUESTED_PORT" ]]; then
  ROS_MASTER_PORT="$(python3 "$REPO_ROOT/scripts/select_ros_master_port.py" --requested-port "$REQUESTED_PORT")"
else
  ROS_MASTER_PORT="$(python3 "$REPO_ROOT/scripts/select_ros_master_port.py" --base-port 11611)"
fi

RUNNER_PID=""
RVIZ_TOP_PID=""
RVIZ_FPV_PID=""
cleanup() {
  set +e
  stop_pid_list_gracefully "$RVIZ_TOP_PID" "$RVIZ_FPV_PID" "$RUNNER_PID"
}
trap cleanup EXIT

launch_rviz_pair() {
  set +e
  source /opt/ros/noetic/setup.bash
  source "$WORKSPACE_DIR/devel/setup.bash"
  export ROS_MASTER_URI="http://127.0.0.1:$ROS_MASTER_PORT"
  export ROS_HOSTNAME="127.0.0.1"
  for _ in $(seq 1 60); do
    if [[ -n "$RUNNER_PID" ]] && ! kill -0 "$RUNNER_PID" 2>/dev/null; then
      return 0
    fi
    if rostopic list >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! rostopic list >/dev/null 2>&1; then
    return 0
  fi
  rviz -d "$(rospack find perfect_drone_sim)/rviz/benchmark.rviz" >/tmp/sim_plane_super_top_down_rviz.log 2>&1 &
  RVIZ_TOP_PID=$!
  rviz -d "$(rospack find perfect_drone_sim)/rviz/fpv.rviz" >/tmp/sim_plane_super_fpv_rviz.log 2>&1 &
  RVIZ_FPV_PID=$!
}

SIM_PLANE_ROS_MASTER_PORT="$ROS_MASTER_PORT" "$REPO_ROOT/scripts/run_super_benchmark.sh" "$@" &
RUNNER_PID=$!
launch_rviz_pair

set +e
wait "$RUNNER_PID"
RUNNER_STATUS=$?
set -e
exit "$RUNNER_STATUS"
