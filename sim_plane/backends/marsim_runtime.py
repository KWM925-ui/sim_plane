import os
import shlex
import subprocess
import time
from pathlib import Path

from sim_plane.backends.base import BackendError
from sim_plane.processes import start_log_threads
from sim_plane.ros_nodes import cleanup_live_ros_nodes


DEFAULT_MARSIM_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_marsim"),
]


def preflight_ros_cleanup(config, sink, env):
    cleanup_live_ros_nodes(
        config["shutdown_nodes"],
        sink,
        env,
        request_message="stale planner-on-scene nodes detected; requesting cleanup",
        success_message="stale planner-on-scene nodes removed",
        failure_message="stale planner-on-scene nodes still present after cleanup",
    )


def launch_marsim(config, sink, env):
    command = [
        "roslaunch",
        config["marsim_ros_package"],
        config["marsim_launch_file"],
        "launch_rviz:={0}".format("true" if config["marsim_launch_rviz"] else "false"),
        "use_gpu_:={0}".format("true" if config["use_gpu"] else "false"),
    ]
    sink.emit_event(
        "info",
        "launching roslaunch",
        {
            "label": "marsim",
            "command": " ".join(shlex.quote(part) for part in command),
            "cwd": str(config["marsim_workspace_dir"]),
        },
    )
    process = subprocess.Popen(
        command,
        cwd=str(config["marsim_workspace_dir"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_log_threads(process, sink, "marsim", event_parser=parse_marsim_log_event)
    time.sleep(1.5)
    if process.poll() is not None:
        raise BackendError(
            "MARSIM roslaunch exited before the planner-on-scene stack finished startup."
        )
    return process


def parse_marsim_log_event(label, stream_name, line):
    harmless_markers = (
        "Global Pointcloud received",
        "Normal compute finished",
        "rviz version",
        "process has finished cleanly",
        "Shutdown request received",
        "Reason given for shutdown: [user request]",
    )
    if any(marker in line for marker in harmless_markers) or (
        "rvizvisualisation" in line and "escalating to SIGTERM" in line
    ):
        return {
            "level": "info",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    if "terminate called after throwing" in line or "[ERROR]" in line:
        return {
            "level": "warning",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    if "[WARN]" in line or "Failed to find match for field 'intensity'" in line:
        return {
            "level": "warning",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    return None
