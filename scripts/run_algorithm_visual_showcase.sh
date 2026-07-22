#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=${SIM_PLANE_HOME:-"$(cd "$(dirname "$0")/.." && pwd)"}
ARTIFACT_ROOT="$REPO_ROOT/runs"
MANUAL_PROBE_ROOT=""
OPEN_BROWSER=0
DASHBOARD_PORT_BASE="${SIM_PLANE_SHOWCASE_DASHBOARD_PORT_BASE:-8765}"
SHOWCASE_RETRIES="${SIM_PLANE_SHOWCASE_RETRIES:-1}"

source "$REPO_ROOT/scripts/process_cleanup.sh"
source "$REPO_ROOT/scripts/manual_probe_lifecycle.sh"

usage() {
  cat <<'EOF'
Usage: ./scripts/run_algorithm_visual_showcase.sh [--open-browser] [--artifact-root PATH] [--manual-probe-root PATH]

Runs the current visual algorithm surfaces serially, records whether GUI windows
actually appeared, and writes a retained showcase report under manual probes.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --open-browser)
      OPEN_BROWSER=1
      shift
      ;;
    --artifact-root)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --artifact-root" >&2
        exit 2
      fi
      ARTIFACT_ROOT="$1"
      shift
      ;;
    --manual-probe-root)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --manual-probe-root" >&2
        exit 2
      fi
      MANUAL_PROBE_ROOT="$1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$MANUAL_PROBE_ROOT" ]]; then
  MANUAL_PROBE_ROOT="$ARTIFACT_ROOT/manual_probes"
fi
export SIM_PLANE_MANUAL_PROBE_ROOT="$MANUAL_PROBE_ROOT"

mkdir -p "$ARTIFACT_ROOT" "$MANUAL_PROBE_ROOT"

SHOWCASE_DIR="$MANUAL_PROBE_ROOT/visual_showcase_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SHOWCASE_DIR"
manual_probe_start "$SHOWCASE_DIR"

RESULTS_TSV="$SHOWCASE_DIR/results.tsv"
printf 'label\tattempts\texit_code\tstatus\tartifact_dir\tdashboard_url\tgui_opened\tcommand_log\tgui_markers_file\tlingering_processes_file\tcommand\n' >"$RESULTS_TSV"

capture_window_markers() {
  if ! command -v xwininfo >/dev/null 2>&1; then
    return 0
  fi
  xwininfo -root -tree 2>/dev/null \
    | rg -i 'rviz|qgroundcontrol|flightgear|gazebo|jmavsim|firefox|chromium|chrome' \
    | sed 's/^[[:space:]]*//' \
    | sort -u \
    || true
}

capture_process_markers() {
  ps -eo pid=,args= \
    | rg -i '(^|/)(rviz|roscore|rosmaster|roslaunch)([[:space:]]|$)|waypoint_mission|perfect_drone|fsm_node|laserMapping|map_generator|traj_server|odom_visualization|plan_manage|global_planner|local_planner' \
    | sed 's/^[[:space:]]*//' \
    | sort -u \
    || true
}

extract_artifact_dir() {
  python3 - "$1" <<'PY'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
matches = re.findall(r"^artifact_dir:\s*(.+)$", text, re.M)
if matches:
    print(matches[-1].strip())
    raise SystemExit(0)
matches = re.findall(r'"artifact_dir"\s*:\s*"([^"]+)"', text)
if matches:
    print(matches[-1].strip())
PY
}

extract_dashboard_url() {
  python3 - "$1" <<'PY'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
matches = re.findall(r"^dashboard_url:\s*(.+)$", text, re.M)
if matches:
    print(matches[-1].strip())
PY
}

extract_status() {
  python3 - "$1" "$2" <<'PY'
import json
import sys
from pathlib import Path

artifact_dir = Path(sys.argv[1])
exit_code = sys.argv[2]
result_json = artifact_dir / "result.json"
probe_meta = artifact_dir / "probe_meta.json"

if result_json.exists():
    print(str(json.loads(result_json.read_text(encoding="utf-8")).get("status", "")))
    raise SystemExit(0)
if probe_meta.exists():
    print(str(json.loads(probe_meta.read_text(encoding="utf-8")).get("status", "")))
    raise SystemExit(0)
print("passed" if exit_code == "0" else "failed")
PY
}

escape_tsv_field() {
  printf '%s' "$1" | tr '\t\r\n' '   '
}

cleanup_new_processes() {
  local baseline_file="$1"
  local linger_file="$2"
  local current_file="$3"
  capture_process_markers >"$current_file"
  comm -13 "$baseline_file" "$current_file" >"$linger_file" || true
  if [[ ! -s "$linger_file" ]]; then
    return 0
  fi

  mapfile -t linger_pids < <(awk '{print $1}' "$linger_file" | rg '^[0-9]+$' || true)
  if [[ ${#linger_pids[@]} -eq 0 ]]; then
    return 0
  fi

  stop_pid_list_gracefully "${linger_pids[@]}"
}

BASELINE_PROCESSES="$SHOWCASE_DIR/baseline_processes.txt"
capture_process_markers >"$BASELINE_PROCESSES"

run_entry() {
  local label="$1"
  shift

  local entry_dir="$SHOWCASE_DIR/$label"
  mkdir -p "$entry_dir"

  local gui_opened=false
  local attempts=0
  local max_attempts=$((SHOWCASE_RETRIES + 1))
  local exit_code=0
  local artifact_dir=""
  local dashboard_url=""
  local status=""

  local command_log=""
  local before_windows=""
  local after_windows=""
  local gui_markers_file=""
  local linger_file=""
  local current_processes_file=""

  while (( attempts < max_attempts )); do
    attempts=$((attempts + 1))
    command_log="$entry_dir/attempt_${attempts}_command.log"
    before_windows="$entry_dir/attempt_${attempts}_windows_before.txt"
    after_windows="$entry_dir/attempt_${attempts}_windows_after.txt"
    gui_markers_file="$entry_dir/attempt_${attempts}_gui_markers.txt"
    linger_file="$entry_dir/attempt_${attempts}_lingering_processes.txt"
    current_processes_file="$entry_dir/attempt_${attempts}_processes_after.txt"

    capture_window_markers >"$before_windows"

    (
      cd "$REPO_ROOT"
      "$@"
    ) >"$command_log" 2>&1 &
    local run_pid=$!
    local attempt_gui_opened=false

    while kill -0 "$run_pid" 2>/dev/null; do
      capture_window_markers >"$after_windows"
      comm -13 "$before_windows" "$after_windows" >"$gui_markers_file" || true
      if [[ -s "$gui_markers_file" ]]; then
        attempt_gui_opened=true
        gui_opened=true
        break
      fi
      sleep 1
    done

    set +e
    wait "$run_pid"
    exit_code=$?
    set -e

    capture_window_markers >"$after_windows"
    if [[ "$attempt_gui_opened" != true ]]; then
      comm -13 "$before_windows" "$after_windows" >"$gui_markers_file" || true
      if [[ -s "$gui_markers_file" ]]; then
        gui_opened=true
      fi
    fi

    artifact_dir="$(extract_artifact_dir "$command_log" || true)"
    dashboard_url="$(extract_dashboard_url "$command_log" || true)"
    if [[ -n "$artifact_dir" && -d "$artifact_dir" ]]; then
      status="$(extract_status "$artifact_dir" "$exit_code")"
    else
      status="passed"
      if [[ "$exit_code" -ne 0 ]]; then
        status="failed"
      fi
    fi

    cleanup_new_processes "$BASELINE_PROCESSES" "$linger_file" "$current_processes_file"

    if [[ "$status" == "passed" ]]; then
      break
    fi
    if (( attempts < max_attempts )); then
      sleep 2
    fi
  done

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(escape_tsv_field "$label")" \
    "$(escape_tsv_field "$attempts")" \
    "$(escape_tsv_field "$exit_code")" \
    "$(escape_tsv_field "$status")" \
    "$(escape_tsv_field "$artifact_dir")" \
    "$(escape_tsv_field "$dashboard_url")" \
    "$(escape_tsv_field "$gui_opened")" \
    "$(escape_tsv_field "$command_log")" \
    "$(escape_tsv_field "$gui_markers_file")" \
    "$(escape_tsv_field "$linger_file")" \
    "$(escape_tsv_field "$*")" \
    >>"$RESULTS_TSV"

  return 0
}

COMMON_FLAGS=(--artifact-root "$ARTIFACT_ROOT" --no-hold-open)
VISUALIZE_FLAGS=(--visualize)
BROWSER_FLAGS=()
if [[ "$OPEN_BROWSER" -eq 1 ]]; then
  BROWSER_FLAGS=(--open-browser)
fi

run_entry "ego_planner_single_visual" \
  ./scripts/run_ego_planner_single_visual.sh \
  --port "$((DASHBOARD_PORT_BASE + 0))" \
  "${COMMON_FLAGS[@]}" \
  "${BROWSER_FLAGS[@]}"

run_entry "ego_planner_swarm_single_visual" \
  ./scripts/run_ego_planner_swarm_single_visual.sh \
  --port "$((DASHBOARD_PORT_BASE + 1))" \
  "${COMMON_FLAGS[@]}" \
  "${BROWSER_FLAGS[@]}"

run_entry "fast_lio_marsim_visual" \
  ./scripts/run_fast_lio_marsim_visual.sh \
  --port "$((DASHBOARD_PORT_BASE + 2))" \
  "${COMMON_FLAGS[@]}" \
  "${BROWSER_FLAGS[@]}"

run_entry "ego_planner_marsim_visual" \
  ./scripts/run_ego_planner_marsim_visual.sh \
  --port "$((DASHBOARD_PORT_BASE + 3))" \
  "${VISUALIZE_FLAGS[@]}" \
  "${COMMON_FLAGS[@]}" \
  "${BROWSER_FLAGS[@]}"

run_entry "ego_planner_swarm_marsim_visual" \
  ./scripts/run_ego_planner_swarm_marsim_visual.sh \
  --port "$((DASHBOARD_PORT_BASE + 4))" \
  "${VISUALIZE_FLAGS[@]}" \
  "${COMMON_FLAGS[@]}" \
  "${BROWSER_FLAGS[@]}"

run_entry "ego_planner_fast_lio_marsim_visual" \
  ./scripts/run_ego_planner_fast_lio_marsim_visual.sh \
  --port "$((DASHBOARD_PORT_BASE + 5))" \
  "${VISUALIZE_FLAGS[@]}" \
  "${COMMON_FLAGS[@]}" \
  "${BROWSER_FLAGS[@]}"

run_entry "ego_planner_swarm_fast_lio_marsim_visual" \
  ./scripts/run_ego_planner_swarm_fast_lio_marsim_visual.sh \
  --port "$((DASHBOARD_PORT_BASE + 6))" \
  "${VISUALIZE_FLAGS[@]}" \
  "${COMMON_FLAGS[@]}" \
  "${BROWSER_FLAGS[@]}"

run_entry "super_benchmark_visual" \
  ./scripts/run_super_benchmark_visual.sh

run_entry "visplanner_tracking_visual" \
  ./scripts/run_visplanner_tracking_visual.sh

python3 -m sim_plane platform-acceptance --latest --artifact-root "$ARTIFACT_ROOT" >"$SHOWCASE_DIR/platform_acceptance_latest.txt" 2>&1 || true
python3 -m sim_plane manual-probe-hygiene --artifact-root "$ARTIFACT_ROOT" >"$SHOWCASE_DIR/manual_probe_hygiene.txt" 2>&1 || true

python3 - "$RESULTS_TSV" "$SHOWCASE_DIR" <<'PY'
import csv
import json
import sys
from pathlib import Path

results_tsv = Path(sys.argv[1])
showcase_dir = Path(sys.argv[2])

rows = []
with results_tsv.open("r", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    for row in reader:
        row["attempts"] = int(row["attempts"])
        row["exit_code"] = int(row["exit_code"])
        row["gui_opened"] = row["gui_opened"].lower() == "true"
        rows.append(row)

summary = {
    "showcase_dir": str(showcase_dir),
    "entry_count": len(rows),
    "failed_labels": [row["label"] for row in rows if row["status"] != "passed"],
    "gui_missing_labels": [row["label"] for row in rows if not row["gui_opened"]],
    "rows": rows,
}
summary["status"] = "passed" if not summary["failed_labels"] and not summary["gui_missing_labels"] else "failed"

(showcase_dir / "summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

max_attempts = max((row["attempts"] for row in rows), default=0)

lines = [
    "# Visual Showcase Summary",
    "",
    f"- showcase_dir: `{showcase_dir}`",
    f"- entry_count: `{len(rows)}`",
    f"- max_attempts: `{max_attempts}`",
    f"- failed_labels: `{', '.join(summary['failed_labels']) if summary['failed_labels'] else 'none'}`",
    f"- gui_missing_labels: `{', '.join(summary['gui_missing_labels']) if summary['gui_missing_labels'] else 'none'}`",
    "",
    "| label | attempts | status | gui_opened | artifact_dir | dashboard_url |",
    "| --- | --- | --- | --- | --- | --- |",
]
for row in rows:
    lines.append(
        "| {label} | {attempts} | {status} | {gui_opened} | {artifact_dir} | {dashboard_url} |".format(
            **row
        )
    )

(showcase_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
(showcase_dir / "probe_meta.json").write_text(
    json.dumps(
        {
            "probe_name": "visual_showcase",
            "retention": "keep_latest_success",
            "status": summary["status"],
        },
        indent=2,
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)
PY

SHOWCASE_STATUS="$(python3 - "$SHOWCASE_DIR/summary.json" <<'PY'
import json
import sys
from pathlib import Path

print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["status"])
PY
)"
manual_probe_complete "$SHOWCASE_DIR" "$SHOWCASE_STATUS"

echo "showcase_dir: $SHOWCASE_DIR"
echo "summary_json: $SHOWCASE_DIR/summary.json"
echo "summary_md: $SHOWCASE_DIR/summary.md"
