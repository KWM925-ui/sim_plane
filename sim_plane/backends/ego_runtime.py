import json
import os
import shlex
import subprocess
from pathlib import Path
from threading import Thread

from sim_plane.backends.base import BackendError
from sim_plane.processes import register_background_threads


DEFAULT_EGO_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_ego_planner"),
]

DEFAULT_EGO_SWARM_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm"),
]


def launch_telemetry_probe(config, sink, env, telemetry_queue):
    command = [
        "python3",
        str(config["probe_script"]),
        "--odom-topic",
        config["odom_topic"],
        "--command-topic",
        config["command_topic"],
        "--pointcloud-topic",
        config["pointcloud_topic"],
        "--sample-hz",
        str(config["sample_hz"]),
        "--target-altitude-m",
        str(config["target_altitude_m"]),
        "--master-timeout-s",
        str(config["startup_timeout_s"]),
    ]
    sink.emit_event(
        "info",
        "launching ros telemetry probe",
        {"command": " ".join(shlex.quote(part) for part in command)},
    )
    process = subprocess.Popen(
        command,
        cwd=str(config["workspace_dir"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    thread = Thread(target=read_probe_stdout, args=(process.stdout, telemetry_queue), daemon=True)
    stderr_thread = Thread(target=stream_probe_stderr, args=(process.stderr, sink), daemon=True)
    register_background_threads(sink, thread, stderr_thread)
    thread.start()
    stderr_thread.start()
    return process


def run_goal_publisher(config, sink, env):
    command = [
        "python3",
        str(config["goal_script"]),
        "--goal-topic",
        config["goal_topic"],
        "--odom-topic",
        config["odom_topic"],
        "--pointcloud-topic",
        config["pointcloud_topic"],
        "--command-topic",
        config["command_topic"],
        "--frame-id",
        config["goal_frame_id"],
        "--goal-x",
        str(config["goal"]["x"]),
        "--goal-y",
        str(config["goal"]["y"]),
        "--goal-z",
        str(config["goal"]["z"]),
        "--master-timeout-s",
        str(config["startup_timeout_s"]),
        "--command-timeout-s",
        str(config["goal_timeout_s"]),
    ]
    sink.emit_event(
        "info",
        "launching ros goal publisher",
        {"command": " ".join(shlex.quote(part) for part in command)},
    )
    completed = subprocess.run(
        command,
        cwd=str(config["workspace_dir"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=config["startup_timeout_s"] + config["goal_timeout_s"] + 20.0,
    )
    if completed.stderr.strip():
        sink.emit_backend_log(
            "stderr",
            "[ros_goal_publisher_stderr] {0}".format(completed.stderr.strip()),
        )

    raw_stdout = completed.stdout.strip()
    if not raw_stdout:
        raise BackendError("ros goal publisher exited without a result.")
    try:
        result = json.loads(raw_stdout.splitlines()[-1])
    except json.JSONDecodeError as exc:
        raise BackendError("ros goal publisher emitted invalid JSON: {0}".format(exc)) from exc
    if completed.returncode != 0:
        raise BackendError(
            "ros goal publisher failed: {0}".format(json.dumps(result, ensure_ascii=False))
        )
    return result


def read_probe_stdout(stream, telemetry_queue):
    if stream is None:
        return
    for raw_line in iter(stream.readline, ""):
        line = raw_line.strip()
        if not line:
            continue
        telemetry_queue.put(json.loads(line))
    stream.close()


def stream_probe_stderr(stream, sink):
    if stream is None:
        return
    for raw_line in iter(stream.readline, ""):
        line = raw_line.rstrip()
        if not line:
            continue
        sink.emit_backend_log("stderr", "[ros_probe_stderr] {0}".format(line))
        event = parse_ros_probe_event("ros_probe_stderr", "stderr", line)
        if event:
            sink.emit_event(event["level"], event["message"], event["details"])
    stream.close()


def evaluate_run_status(success_criteria, telemetry_summary):
    if success_criteria == "telemetry":
        return "passed" if telemetry_summary["telemetry_count"] > 0 else "failed"
    if success_criteria == "command":
        return "passed" if telemetry_summary["position_cmd_seen"] else "failed"
    if success_criteria == "sensor_stack":
        return (
            "passed"
            if telemetry_summary["pointcloud_seen"] and telemetry_summary["position_cmd_seen"]
            else "failed"
        )
    return (
        "passed"
        if telemetry_summary["target_altitude_reached"]
        and telemetry_summary["position_cmd_seen"]
        and telemetry_summary["pointcloud_seen"]
        and telemetry_summary["goal_reached"]
        else "failed"
    )


def parse_ros_log_event(label, stream_name, line):
    if line.startswith("[FSM]:"):
        return {
            "level": "info",
            "message": "fsm transition",
            "details": {"line": line, "stream": stream_name},
        }
    if line.startswith("[TRIG]:"):
        return {
            "level": "info",
            "message": "planner trigger",
            "details": {"line": line, "stream": stream_name},
        }
    if line.startswith("[SAFETY]:"):
        level = "warning" if "EMERGENCY_STOP" in line else "info"
        return {
            "level": level,
            "message": "planner safety transition",
            "details": {"line": line, "stream": stream_name},
        }
    harmless_markers = (
        "Global Pointcloud received",
        "ready.",
        "Failed to generate direction. It doesn't matter.",
        "older format",
        "_missing_material_",
    )
    if any(marker in line for marker in harmless_markers):
        return {
            "level": "info",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    if "[ERROR]" in line or "terminate called after throwing" in line:
        return {
            "level": "warning",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    if "[WARN]" in line:
        return {
            "level": "warning",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    return None


def parse_ros_probe_event(label, stream_name, line):
    if "Traceback" in line or "ERROR" in line:
        return {
            "level": "warning",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    return None
