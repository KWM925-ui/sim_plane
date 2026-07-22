import os
import shlex
import signal
import subprocess
import time
from pathlib import Path

from sim_plane.paths import get_platform_paths
from sim_plane.processes import process_group_exists, wait_for_process_group_exit
from sim_plane.ros_master import ensure_ros_master_uri
from sim_plane.ros_nodes import cleanup_live_ros_nodes


DEFAULT_ROS_SETUP = Path("/opt/ros/noetic/setup.bash")


def repo_root():
    return get_platform_paths().home


def resolve_workspace_dir(explicit_path=None, env_var=None, candidates=None):
    ordered = []
    if explicit_path:
        ordered.append(Path(explicit_path).expanduser())
    if env_var:
        env_path = os.environ.get(env_var)
        if env_path:
            ordered.append(Path(env_path).expanduser())
    ordered.extend(candidates or [])
    for candidate in ordered:
        if (candidate / "src").is_dir():
            return candidate.resolve()
    return None


def load_sourced_environment(setup_paths):
    command_parts = []
    for path in setup_paths:
        command_parts.append("source {0}".format(shlex.quote(str(path))))
    command_parts.append("env -0")
    raw = subprocess.check_output(["bash", "-lc", " && ".join(command_parts)])
    env = {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        key, _, value = item.partition(b"=")
        env[key.decode("utf-8")] = value.decode("utf-8")
    return env


def prepare_ros_runtime_env(base_env, artifact_dir):
    env = dict(base_env)
    artifact_root = Path(artifact_dir).resolve()
    ros_home = artifact_root / "ros_home"
    ros_log_dir = artifact_root / "ros_logs"
    ros_home.mkdir(parents=True, exist_ok=True)
    ros_log_dir.mkdir(parents=True, exist_ok=True)
    env["ROS_HOME"] = str(ros_home)
    env["ROS_LOG_DIR"] = str(ros_log_dir)
    env["ROS_HOSTNAME"] = "127.0.0.1"
    env["ROS_IP"] = "127.0.0.1"
    ensure_ros_master_uri(env)
    return env


def stop_roslaunch(process, sink, label, wait_timeout_s):
    if process is None:
        return True
    group_id = process.pid
    parent_running = process.poll() is None
    if not process_group_exists(group_id):
        return True
    sink.emit_event(
        "info",
        "stopping process",
        {"label": label, "pid": process.pid, "signal": "SIGINT"},
    )
    deadline = time.monotonic() + max(float(wait_timeout_s), 0.0)
    try:
        os.killpg(group_id, signal.SIGINT)
        if parent_running:
            process.wait(timeout=max(0.0, deadline - time.monotonic()))
        if wait_for_process_group_exit(
            group_id,
            max(0.0, deadline - time.monotonic()),
        ):
            return True
        sink.emit_event(
            "warning",
            "roslaunch process group did not exit after SIGINT",
            {"label": label, "pid": process.pid, "timeout_s": wait_timeout_s},
        )
        return False
    except subprocess.TimeoutExpired:
        sink.emit_event(
            "warning",
            "roslaunch did not exit after SIGINT",
            {"label": label, "pid": process.pid, "timeout_s": wait_timeout_s},
        )
        return False
    except ProcessLookupError:
        return True


def shutdown_ros_nodes(config, sink, env, skip_nodes=None):
    nodes = list(config.get("shutdown_nodes") or [])
    if not nodes:
        return
    skipped = set(skip_nodes or ())
    shutdown_specific_ros_nodes(
        [node for node in nodes if node not in skipped],
        sink,
        env,
        "requesting ros node shutdown",
    )


def shutdown_specific_ros_nodes(nodes, sink, env, message):
    cleanup_live_ros_nodes(
        nodes,
        sink,
        env,
        request_message=message,
    )
