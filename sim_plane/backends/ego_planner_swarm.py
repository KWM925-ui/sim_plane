import json
import os
import shlex
import signal
import subprocess
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

from sim_plane.backends.base import Backend, BackendError
from sim_plane.processes import start_log_threads, terminate_process
from sim_plane.ros_nodes import cleanup_live_ros_nodes


DEFAULT_ROS_SETUP = Path("/opt/ros/noetic/setup.bash")
DEFAULT_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm"),
]
DEFAULT_SHUTDOWN_NODES = [
    "/random_forest",
    "/drone_0_ego_planner_node",
    "/drone_0_traj_server",
    "/drone_0_poscmd_2_odom",
    "/drone_0_odom_visualization",
    "/drone_0_pcl_render_node",
]


class EgoPlannerSwarmBackend(Backend):
    name = "ego_planner_swarm"

    def validate_environment(self, scenario=None):
        config = build_runtime_config(scenario or {})
        issues = []
        if not config["ros_setup"].is_file():
            issues.append("ROS Noetic setup.bash was not found at /opt/ros/noetic/setup.bash.")
        if config["workspace_dir"] is None:
            issues.append(
                "EGO-Planner-Swarm workspace not found. Build or point to /home/coco/sim_plane_ws/workspaces/ros1_ego_swarm."
            )
        elif not config["workspace_setup"].is_file():
            issues.append(
                "EGO-Planner-Swarm workspace exists but devel/setup.bash is missing. Run ./scripts/build_ego_planner_swarm_ws.sh first."
            )
        if not config["probe_script"].is_file():
            issues.append("ROS telemetry probe script is missing from scripts/ros_telemetry_probe.py.")
        return issues

    def run(self, scenario, sink):
        config = build_runtime_config(scenario)
        issues = self.validate_environment(scenario)
        if issues:
            raise BackendError("; ".join(issues))

        env = load_sourced_environment([config["ros_setup"], config["workspace_setup"]])
        env = prepare_ros_runtime_env(env, sink.artifact_writer.artifact_dir)
        sink.emit_event(
            "info",
            "ego_planner_swarm launch plan",
            {
                "workspace_dir": str(config["workspace_dir"]),
                "launch": "{0} {1}".format(config["ros_package"], config["launch_file"]),
                "launch_rviz": config["launch_rviz"],
                "odom_topic": config["odom_topic"],
                "command_topic": config["command_topic"],
                "ros_log_dir": env["ROS_LOG_DIR"],
            },
        )

        roslaunch_process = None
        viewer_process = None
        probe_process = None
        telemetry_queue = Queue()
        try:
            roslaunch_process = launch_roslaunch(config, sink, env, config["ros_package"], config["launch_file"], "ego_swarm")
            if config["launch_rviz"]:
                viewer_process = launch_roslaunch(config, sink, env, "ego_planner", "rviz.launch", "rviz")
            probe_process = launch_telemetry_probe(config, sink, env, telemetry_queue)
            summary = stream_telemetry(config, sink, telemetry_queue, roslaunch_process)
            return {
                "status": evaluate_run_status(config["success_criteria"], summary),
                "backend": self.name,
                "vehicle": scenario["vehicle"],
                "scenario_name": scenario["name"],
                "metrics": summary,
                "notes": build_notes(config),
            }
        finally:
            terminate_process(probe_process, sink, "ros_probe", stop_signal=signal.SIGINT, wait_timeout_s=4.0)
            terminate_process(
                viewer_process,
                sink,
                "rviz",
                stop_signal=signal.SIGINT,
                wait_timeout_s=6.0,
                forced_kill_level="info",
            )
            if not stop_roslaunch(roslaunch_process, sink, "ego_swarm", wait_timeout_s=10.0):
                shutdown_ros_nodes(
                    config,
                    sink,
                    env,
                    skip_nodes={"/drone_0_pcl_render_node"},
                )
                terminate_process(roslaunch_process, sink, "ego_swarm", stop_signal=signal.SIGTERM, wait_timeout_s=4.0)


def build_runtime_config(scenario):
    backend_options = dict(scenario.get("backend_options", {}))
    workspace_dir = resolve_workspace_dir(backend_options.get("ros_workspace_dir"))
    workspace_setup = workspace_dir / "devel" / "setup.bash" if workspace_dir is not None else Path("")
    return {
        "ros_setup": Path(backend_options.get("ros_setup", DEFAULT_ROS_SETUP)).expanduser(),
        "workspace_dir": workspace_dir,
        "workspace_setup": workspace_setup,
        "ros_package": backend_options.get("ros_package", "ego_planner"),
        "launch_file": backend_options.get("launch_file", "single_run_in_sim.launch"),
        "launch_rviz": bool(backend_options.get("launch_rviz", False)),
        "probe_script": repo_root() / "scripts" / "ros_telemetry_probe.py",
        "duration_s": float(scenario.get("duration_s", 20.0)),
        "sample_hz": float(scenario.get("update_hz", 5.0)),
        "target_altitude_m": float(scenario.get("target_altitude_m", 1.0)),
        "startup_timeout_s": float(backend_options.get("startup_timeout_s", 20.0)),
        "odom_topic": backend_options.get("odom_topic", "/drone_0_visual_slam/odom"),
        "command_topic": backend_options.get("command_topic", "/drone_0_planning/pos_cmd"),
        "shutdown_nodes": list(backend_options.get("shutdown_nodes", DEFAULT_SHUTDOWN_NODES)),
        "success_criteria": backend_options.get("success_criteria", "trajectory"),
    }


def repo_root():
    return Path(__file__).resolve().parents[2]


def resolve_workspace_dir(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.environ.get("SIM_PLANE_EGO_SWARM_WS")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(DEFAULT_WORKSPACE_CANDIDATES)

    for candidate in candidates:
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
    return env


def launch_roslaunch(config, sink, env, package, launch_file, label):
    command = ["roslaunch", package, launch_file]
    sink.emit_event(
        "info",
        "launching roslaunch",
        {"label": label, "command": " ".join(shlex.quote(part) for part in command), "cwd": str(config["workspace_dir"])},
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
    start_log_threads(process, sink, label, event_parser=parse_ros_log_event)
    time.sleep(1.5)
    if process.poll() is not None:
        raise BackendError("roslaunch exited before the ROS lab stack finished startup.")
    return process


def launch_telemetry_probe(config, sink, env, telemetry_queue):
    command = [
        "python3",
        str(config["probe_script"]),
        "--odom-topic",
        config["odom_topic"],
        "--command-topic",
        config["command_topic"],
        "--sample-hz",
        str(config["sample_hz"]),
        "--target-altitude-m",
        str(config["target_altitude_m"]),
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
    thread.start()
    stderr_thread = Thread(target=stream_probe_stderr, args=(process.stderr, sink), daemon=True)
    stderr_thread.start()
    return process


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


def stream_telemetry(config, sink, telemetry_queue, roslaunch_process):
    start_wall = time.time()
    deadline = start_wall + config["duration_s"]
    telemetry_count = 0
    max_altitude_m = 0.0
    max_speed_mps = 0.0
    reached_target_altitude = False
    position_cmd_seen = False
    first_sample_seen = False
    first_sample_deadline = start_wall + config["startup_timeout_s"]

    while time.time() <= deadline:
        if roslaunch_process.poll() is not None:
            raise BackendError("roslaunch exited before the configured run duration elapsed.")
        timeout_s = 0.25 if first_sample_seen else max(0.0, min(0.25, first_sample_deadline - time.time()))
        if not first_sample_seen and timeout_s == 0.0:
            raise BackendError("Timed out waiting for /drone_0_visual_slam/odom telemetry.")
        try:
            sample = telemetry_queue.get(timeout=max(timeout_s, 0.05))
        except Empty:
            continue

        if not first_sample_seen:
            first_sample_seen = True
            sink.emit_event(
                "info",
                "ros odometry received",
                {
                    "odom_topic": config["odom_topic"],
                    "position": sample["position"],
                    "altitude_m": sample["altitude_m"],
                },
            )
        if sample.get("position_cmd_count", 0) > 0 and not position_cmd_seen:
            position_cmd_seen = True
            sink.emit_event(
                "info",
                "planner command stream detected",
                {"command_topic": config["command_topic"], "count": sample["position_cmd_count"]},
            )

        sink.emit_telemetry(sample)
        telemetry_count += 1
        max_altitude_m = max(max_altitude_m, float(sample.get("altitude_m", 0.0)))
        max_speed_mps = max(max_speed_mps, float(sample.get("speed_mps", 0.0)))
        if float(sample.get("altitude_m", 0.0)) >= config["target_altitude_m"] * 0.95:
            reached_target_altitude = True

    return {
        "telemetry_count": telemetry_count,
        "max_altitude_m": round(max_altitude_m, 3),
        "max_speed_mps": round(max_speed_mps, 3),
        "target_altitude_reached": reached_target_altitude,
        "position_cmd_seen": position_cmd_seen,
        "duration_s": config["duration_s"],
        "launch_rviz": config["launch_rviz"],
    }


def stop_roslaunch(process, sink, label, wait_timeout_s):
    if process is None or process.poll() is not None:
        return True
    sink.emit_event(
        "info",
        "stopping process",
        {"label": label, "pid": process.pid, "signal": "SIGINT"},
    )
    try:
        os.killpg(process.pid, signal.SIGINT)
        process.wait(timeout=wait_timeout_s)
        return True
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
    if not config["shutdown_nodes"]:
        return
    skip_nodes = set(skip_nodes or ())
    cleanup_live_ros_nodes(
        [node for node in config["shutdown_nodes"] if node not in skip_nodes],
        sink,
        env,
        request_message="requesting ros node shutdown",
    )


def evaluate_run_status(success_criteria, telemetry_summary):
    if success_criteria == "telemetry":
        return "passed" if telemetry_summary["telemetry_count"] > 0 else "failed"
    if success_criteria == "command":
        return "passed" if telemetry_summary["position_cmd_seen"] else "failed"
    return "passed" if telemetry_summary["target_altitude_reached"] and telemetry_summary["position_cmd_seen"] else "failed"


def build_notes(config):
    notes = [
        "The ego_planner_swarm backend launches the dedicated ROS1 catkin workspace under /home/coco/sim_plane_ws/workspaces/ros1_ego_swarm.",
        "Live telemetry is derived from /drone_0_visual_slam/odom and planner command activity on /drone_0_planning/pos_cmd.",
    ]
    if config["launch_rviz"]:
        notes.append("RViz was requested as the auxiliary viewer for the ROS lab stack.")
    return notes


def parse_ros_log_event(label, stream_name, line):
    harmless_log_markers = (
        "Finished generate random map",
        "Global Pointcloud received",
        "ready.",
        "Waiting for trigger from [n3ctrl] from RC",
        "Can't find the new base points at the opposite within the threshold",
        "base_point and control point are too close",
        "Ran out of pool, index=",
        "Unable to handle the initial or end point, force return!",
        "a star error",
        "Failed to generate direction. It doesn't matter.",
        "older format",
        "_missing_material_",
    )
    if line.startswith("[FSM]:"):
        return {"level": "info", "message": "fsm transition", "details": {"line": line, "stream": stream_name}}
    if line.startswith("[TRIG]:"):
        return {"level": "info", "message": "planner trigger", "details": {"line": line, "stream": stream_name}}
    if line.startswith("[SAFETY]:"):
        level = "warning" if "EMERGENCY_STOP" in line else "info"
        return {"level": level, "message": "planner safety transition", "details": {"line": line, "stream": stream_name}}
    if any(marker in line for marker in harmless_log_markers):
        return {"level": "info", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "[ERROR]" in line or "terminate called after throwing" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "[WARN]" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    return None


def parse_ros_probe_event(label, stream_name, line):
    if "Traceback" in line or "ERROR" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    return None
