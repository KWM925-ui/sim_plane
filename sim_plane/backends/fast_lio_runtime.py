import os
import shlex
import subprocess
import time
from pathlib import Path

from sim_plane.backends.base import BackendError
from sim_plane.processes import start_log_threads


DEFAULT_FAST_LIO_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_fast_lio"),
]


def launch_fast_lio(config, sink, env):
    command = [
        "roslaunch",
        str(config["fast_lio_launch_file"]),
        "rviz:={0}".format("true" if config["fast_lio_launch_rviz"] else "false"),
    ]
    sink.emit_event(
        "info",
        "launching roslaunch",
        {
            "label": "fast_lio",
            "command": " ".join(shlex.quote(part) for part in command),
            "cwd": str(config["fast_lio_workspace_dir"]),
        },
    )
    process = subprocess.Popen(
        command,
        cwd=str(config["fast_lio_workspace_dir"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_log_threads(process, sink, "fast_lio", event_parser=parse_fast_lio_log_event)
    time.sleep(1.5)
    if process.poll() is not None:
        raise BackendError("FAST_LIO roslaunch exited before the estimation stack finished startup.")
    return process


def launch_aligned_odom_adapter(config, sink, env):
    command = [
        "python3",
        str(config["aligned_odom_script"]),
        "--source-odom-topic",
        config["source_odom_topic"],
        "--reference-odom-topic",
        config["reference_odom_topic"],
        "--output-topic",
        config["odom_topic"],
        "--frame-id",
        "world",
        "--child-frame-id",
        "body",
        "--master-timeout-s",
        str(config["startup_timeout_s"]),
    ]
    sink.emit_event(
        "info",
        "launching aligned odometry adapter",
        {"command": " ".join(shlex.quote(part) for part in command)},
    )
    process = subprocess.Popen(
        command,
        cwd=str(config["ego_workspace_dir"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_log_threads(process, sink, "aligned_odom", event_parser=parse_aligned_odom_log_event)
    time.sleep(0.5)
    if process.poll() is not None:
        raise BackendError(
            "The aligned odometry adapter exited before the planner-on-estimator stack finished startup."
        )
    return process


def parse_aligned_odom_log_event(label, stream_name, line):
    if "locked initial transform" in line or "publishing aligned odometry" in line:
        return {
            "level": "info",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    if "ERROR" in line or "Traceback" in line:
        return {
            "level": "warning",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    return None


def parse_fast_lio_log_event(label, stream_name, line):
    if "No point, skip this scan!" in line:
        return {"level": "info", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "catch sig 2" in line:
        return {"level": "info", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "current scan saved to /PCD/" in line:
        return {"level": "warning", "message": "unexpected fast_lio pcd write", "details": {"line": line, "stream": stream_name}}
    if "publish odom" in line or "Imu Initialization Done" in line:
        return {"level": "info", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "[ERROR]" in line or "terminate called after throwing" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "[WARN]" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    return None
