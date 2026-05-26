#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACT_ROOT="${SIM_PLANE_MANUAL_PROBE_ROOT:-$REPO_ROOT/runs/manual_probes}"
REQUESTED_ROS_MASTER_PORT="${SIM_PLANE_ROS_MASTER_PORT:-}"
WORKSPACE_DIR="/home/coco/sim_plane_ws/workspaces/ros1_super"
SUPER_PROFILE="${SIM_PLANE_SUPER_PROFILE:-dense}"

source "$REPO_ROOT/scripts/process_cleanup.sh"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --profile" >&2
        exit 2
      fi
      SUPER_PROFILE="$1"
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

case "$SUPER_PROFILE" in
  dense)
    DRONE_CONFIG_NAME="dense.yaml"
    PLANNER_CONFIG_NAME="static_dense.yaml"
    ;;
  high_speed)
    DRONE_CONFIG_NAME="high_speed.yaml"
    PLANNER_CONFIG_NAME="static_high_speed.yaml"
    ;;
  *)
    echo "unsupported SUPER profile: $SUPER_PROFILE" >&2
    exit 2
    ;;
esac

if [[ -n "$REQUESTED_ROS_MASTER_PORT" ]]; then
  ROS_MASTER_PORT="$(python3 "$REPO_ROOT/scripts/select_ros_master_port.py" --requested-port "$REQUESTED_ROS_MASTER_PORT")"
else
  ROS_MASTER_PORT="$(python3 "$REPO_ROOT/scripts/select_ros_master_port.py" --base-port 11611)"
fi

ARTIFACT_DIR="$ARTIFACT_ROOT/super_benchmark_${SUPER_PROFILE}_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$ARTIFACT_DIR"

"$REPO_ROOT/scripts/build_super_ws.sh" >/dev/null

export ROS_MASTER_URI="http://127.0.0.1:$ROS_MASTER_PORT"
export ROS_HOSTNAME="127.0.0.1"

source /opt/ros/noetic/setup.bash
source "$WORKSPACE_DIR/devel/setup.bash"

ROSCORE_PID=""
MISSION_PID=""
DRONE_PID=""
FSM_PID=""
TELEMETRY_PID=""

cleanup() {
  set +e
  stop_pid_list_gracefully "$TELEMETRY_PID" "$FSM_PID" "$DRONE_PID" "$MISSION_PID"
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

python3 "$REPO_ROOT/scripts/ros_telemetry_probe.py" \
  --odom-topic /lidar_slam/odom \
  --command-topic /planning/pos_cmd \
  --pointcloud-topic /cloud_registered \
  --target-altitude-m 1.0 \
  >"$ARTIFACT_DIR/telemetry.jsonl" \
  2>"$ARTIFACT_DIR/telemetry.stderr.log" &
TELEMETRY_PID=$!

rosrun mission_planner waypoint_mission _data_name:=benchmark.txt >"$ARTIFACT_DIR/mission.log" 2>&1 &
MISSION_PID=$!
rosrun perfect_drone_sim perfect_drone _config_name:="$DRONE_CONFIG_NAME" >"$ARTIFACT_DIR/perfect_drone.log" 2>&1 &
DRONE_PID=$!
rosrun super_planner fsm_node _config_name:="$PLANNER_CONFIG_NAME" >"$ARTIFACT_DIR/fsm.log" 2>&1 &
FSM_PID=$!

sleep 8

timeout 20s rostopic echo -n 1 /planning/click_goal >"$ARTIFACT_DIR/click_goal.yaml" 2>"$ARTIFACT_DIR/click_goal.err" || true
timeout 25s rostopic echo -n 1 /planning/pos_cmd >"$ARTIFACT_DIR/pos_cmd.yaml" 2>"$ARTIFACT_DIR/pos_cmd.err" || true
sleep 5

rosnode list >"$ARTIFACT_DIR/rosnode_list.txt" 2>&1 || true
rostopic list >"$ARTIFACT_DIR/rostopic_list.txt" 2>&1 || true

python3 - <<'PY' "$ARTIFACT_DIR" "$ROS_MASTER_PORT" "$SUPER_PROFILE"
import json
import re
import sys
from pathlib import Path

artifact_dir = Path(sys.argv[1])
master_port = int(sys.argv[2])
profile = sys.argv[3]

summary = {
    "ros_master_port": master_port,
    "profile": profile,
    "click_goal_seen": (artifact_dir / "click_goal.yaml").exists() and (artifact_dir / "click_goal.yaml").stat().st_size > 0,
    "pos_cmd_seen": (artifact_dir / "pos_cmd.yaml").exists() and (artifact_dir / "pos_cmd.yaml").stat().st_size > 0,
    "telemetry_samples": 0,
}

telemetry_path = artifact_dir / "telemetry.jsonl"
if telemetry_path.exists():
    with telemetry_path.open("r", encoding="utf-8", errors="ignore") as handle:
        summary["telemetry_samples"] = sum(1 for line in handle if line.strip())

fsm_text = (artifact_dir / "fsm.log").read_text(encoding="utf-8", errors="ignore")
drone_text = (artifact_dir / "perfect_drone.log").read_text(encoding="utf-8", errors="ignore")
summary["follow_traj_seen"] = "FOLLOW_TRAJ" in fsm_text
summary["replan_success_seen"] = "ReplanOnce succeed." in fsm_text
summary["replan_success_count"] = len(re.findall(r"ReplanOnce succeed\.", fsm_text))
summary["planner_warn_count"] = len(re.findall(r"\[WARN\]", fsm_text))
summary["hard_warn_count"] = (
    len(re.findall(r"Replan failed, switch to emer\.", fsm_text))
)
summary["transient_replan_miss_count"] = (
    len(re.findall(r"GenerateExpTrajectory failed", fsm_text))
    + len(re.findall(r"generateBackupTrajectory return .* committed trajectory", fsm_text))
    + len(re.findall(r"Replan overtime", fsm_text))
)
summary["soft_optimizer_reject_count"] = (
    len(re.findall(r"Candidate rejected by dynamic or position constraints\.", fsm_text))
    + len(re.findall(r"OptimizationExpTrajInPolytopes for new path failed", fsm_text))
    + len(re.findall(r"OptimizationBakTrajInPolytopes failed, force return", fsm_text))
)
summary["intensity_warn_count"] = drone_text.count("Failed to find match for field 'intensity'.")
summary["intensity_fallback_applied"] = "Loaded PCD without intensity field, filled intensity with 0." in drone_text

(artifact_dir / "summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
probe_meta = {
    "probe_name": f"super_benchmark_{profile}",
    "retention": "keep_latest_success",
    "status": "passed" if summary["click_goal_seen"] and summary["pos_cmd_seen"] else "failed",
}
(artifact_dir / "probe_meta.json").write_text(
    json.dumps(probe_meta, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print(json.dumps({"artifact_dir": str(artifact_dir), "summary": summary}, ensure_ascii=False, indent=2))
raise SystemExit(0 if summary["click_goal_seen"] and summary["pos_cmd_seen"] else 2)
PY
