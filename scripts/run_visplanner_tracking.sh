#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACT_ROOT="${SIM_PLANE_MANUAL_PROBE_ROOT:-$REPO_ROOT/runs/manual_probes}"
ARTIFACT_DIR="$ARTIFACT_ROOT/visplanner_tracking_$(date +%Y%m%d_%H%M%S)"
REQUESTED_ROS_MASTER_PORT="${SIM_PLANE_ROS_MASTER_PORT:-}"
WORKSPACE_DIR="/home/coco/sim_plane_ws/workspaces/ros1_visplanner"

source "$REPO_ROOT/scripts/process_cleanup.sh"

if [[ -n "$REQUESTED_ROS_MASTER_PORT" ]]; then
  ROS_MASTER_PORT="$(python3 "$REPO_ROOT/scripts/select_ros_master_port.py" --requested-port "$REQUESTED_ROS_MASTER_PORT")"
else
  ROS_MASTER_PORT="$(python3 "$REPO_ROOT/scripts/select_ros_master_port.py" --base-port 11621)"
fi

mkdir -p "$ARTIFACT_DIR"

"$REPO_ROOT/scripts/build_visplanner_ws.sh" >/dev/null

export ROS_MASTER_URI="http://127.0.0.1:$ROS_MASTER_PORT"
export ROS_HOSTNAME="127.0.0.1"

source /opt/ros/noetic/setup.bash
source "$WORKSPACE_DIR/devel/setup.bash"

ROSCORE_PID=""
LAUNCH_PID=""
TRACKER_TELEM_PID=""
TARGET_TELEM_PID=""
BG_PIDS=()

cleanup() {
  set +e
  stop_pid_list_gracefully "${BG_PIDS[@]}"
  stop_pid_list_gracefully "$TARGET_TELEM_PID" "$TRACKER_TELEM_PID" "$LAUNCH_PID"
  stop_pid_gracefully "$ROSCORE_PID"
}
trap cleanup EXIT

roscore -p "$ROS_MASTER_PORT" >"$ARTIFACT_DIR/roscore.log" 2>&1 &
ROSCORE_PID=$!

for _ in $(seq 1 30); do
  if ! kill -0 "$ROSCORE_PID" 2>/dev/null; then
    echo "roscore exited early, see $ARTIFACT_DIR/roscore.log" >&2
    exit 2
  fi
  if rostopic list >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

roslaunch -p "$ROS_MASTER_PORT" ego_planner tracking.launch >"$ARTIFACT_DIR/launch.log" 2>&1 &
LAUNCH_PID=$!

for _ in $(seq 1 40); do
  if rosnode list >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

python3 "$REPO_ROOT/scripts/ros_telemetry_probe.py" \
  --odom-topic /drone_0_visual_slam/odom \
  --command-topic /drone_0_planning/pos_cmd \
  --sample-hz 5.0 \
  --target-altitude-m 1.0 \
  >"$ARTIFACT_DIR/tracker_telemetry.jsonl" \
  2>"$ARTIFACT_DIR/tracker_telemetry.stderr.log" &
TRACKER_TELEM_PID=$!

python3 "$REPO_ROOT/scripts/ros_telemetry_probe.py" \
  --odom-topic /drone_1_visual_slam/odom \
  --command-topic /drone_1_planning/pos_cmd \
  --sample-hz 5.0 \
  --target-altitude-m 1.0 \
  >"$ARTIFACT_DIR/target_telemetry.jsonl" \
  2>"$ARTIFACT_DIR/target_telemetry.stderr.log" &
TARGET_TELEM_PID=$!

sleep 6

timeout 30s rostopic echo -n 1 /drone_1_planning/bspline >"$ARTIFACT_DIR/target_bspline.yaml" 2>"$ARTIFACT_DIR/target_bspline.err" &
BG_PIDS+=("$!")
timeout 30s rostopic echo -n 1 /drone_1_planning/pos_cmd >"$ARTIFACT_DIR/target_pos_cmd.yaml" 2>"$ARTIFACT_DIR/target_pos_cmd.err" &
BG_PIDS+=("$!")
timeout 30s rostopic echo -n 1 /drone_0_planning/pos_cmd >"$ARTIFACT_DIR/tracker_pos_cmd.yaml" 2>"$ARTIFACT_DIR/tracker_pos_cmd.err" &
BG_PIDS+=("$!")

python3 "$REPO_ROOT/scripts/ros_goal_publisher.py" \
  --goal-topic /goal \
  --odom-topic /drone_1_visual_slam/odom \
  --command-topic /drone_1_planning/pos_cmd \
  --frame-id world \
  --goal-x 8.0 \
  --goal-y 0.0 \
  --goal-z 1.0 \
  --publish-count 10 \
  --publish-interval-s 0.5 \
  --command-timeout-s 20.0 \
  >"$ARTIFACT_DIR/goal_summary.json" \
  2>"$ARTIFACT_DIR/goal_summary.stderr.log" || true

sleep 18

rosnode list >"$ARTIFACT_DIR/rosnode_list.txt" 2>&1 || true
rostopic list >"$ARTIFACT_DIR/rostopic_list.txt" 2>&1 || true

python3 - <<'PY' "$ARTIFACT_DIR" "$ROS_MASTER_PORT"
import json
import re
import sys
from pathlib import Path

artifact_dir = Path(sys.argv[1])
master_port = int(sys.argv[2])
launch_text = (artifact_dir / "launch.log").read_text(encoding="utf-8", errors="ignore")

def file_seen(name):
    path = artifact_dir / name
    return path.exists() and path.stat().st_size > 0

summary = {
    "ros_master_port": master_port,
    "target_pos_cmd_seen": file_seen("target_pos_cmd.yaml"),
    "tracker_pos_cmd_seen": file_seen("tracker_pos_cmd.yaml"),
    "target_bspline_seen": file_seen("target_bspline.yaml"),
    "target_bspline_drone_id_line": "",
    "wait_target_count": len(re.findall(r"\\bWAIT_TARGET\\b", launch_text)),
    "tracker_left_wait_target": ("from WAIT_TARGET to GEN_NEW_TRAJ" in launch_text) or ("from WAIT_TARGET to SEQUENTIAL_START" in launch_text),
    "tracker_exec_traj": ("from GEN_NEW_TRAJ to EXEC_TRAJ" in launch_text) or ("from SEQUENTIAL_START to EXEC_TRAJ" in launch_text),
    "predict_callback_seen": "Triggered!Predict!" in launch_text,
    "local_target_seen": "Get Local Target!" in launch_text,
    "warn_count": len(re.findall(r"\[WARN\]", launch_text)),
}

target_bspline_path = artifact_dir / "target_bspline.yaml"
if target_bspline_path.exists():
    for line in target_bspline_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("drone_id:"):
            summary["target_bspline_drone_id_line"] = line.strip()
            break

(artifact_dir / "summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
probe_meta = {
    "probe_name": "visplanner_tracking",
    "retention": "keep_latest_success",
    "status": "passed" if summary["target_pos_cmd_seen"] and summary["tracker_pos_cmd_seen"] and summary["tracker_exec_traj"] else "failed",
}
(artifact_dir / "probe_meta.json").write_text(
    json.dumps(probe_meta, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print(json.dumps({"artifact_dir": str(artifact_dir), "summary": summary}, ensure_ascii=False, indent=2))
raise SystemExit(
    0 if summary["target_pos_cmd_seen"] and summary["tracker_pos_cmd_seen"] and summary["tracker_exec_traj"] else 2
)
PY
