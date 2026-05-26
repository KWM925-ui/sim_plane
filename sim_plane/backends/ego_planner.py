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
    Path("/home/coco/sim_plane_ws/workspaces/ros1_ego_planner"),
]
DEFAULT_SHUTDOWN_NODES = [
    "/mockamap_node",
    "/quadrotor_simulator_so3",
    "/so3_control",
    "/odom_visualization",
    "/pcl_render_node",
    "/ego_planner_node",
    "/traj_server",
    "/waypoint_generator",
]


class EgoPlannerBackend(Backend):
    name = "ego_planner"

    def validate_environment(self, scenario=None):
        config = build_runtime_config(scenario or {})
        issues = []
        if not config["ros_setup"].is_file():
            issues.append("ROS Noetic setup.bash was not found at /opt/ros/noetic/setup.bash.")
        if config["workspace_dir"] is None:
            issues.append(
                "Legacy EGO-Planner workspace not found. Build or point to /home/coco/sim_plane_ws/workspaces/ros1_ego_planner."
            )
        elif not config["workspace_setup"].is_file():
            issues.append(
                "Legacy EGO-Planner workspace exists but devel/setup.bash is missing. Run ./scripts/build_ego_planner_ws.sh first."
            )
        if not config["probe_script"].is_file():
            issues.append("ROS telemetry probe script is missing from scripts/ros_telemetry_probe.py.")
        if not config["goal_script"].is_file():
            issues.append("ROS goal publisher script is missing from scripts/ros_goal_publisher.py.")
        return issues

    def run(self, scenario, sink):
        config = build_runtime_config(scenario)
        issues = self.validate_environment(scenario)
        if issues:
            raise BackendError("; ".join(issues))

        env = load_sourced_environment([config["ros_setup"], config["workspace_setup"]])
        env = prepare_ros_runtime_env(env, sink.artifact_writer.artifact_dir)
        preflight_ros_cleanup(config, sink, env)
        sink.emit_event(
            "info",
            "ego_planner launch plan",
            {
                "workspace_dir": str(config["workspace_dir"]),
                "launch": "{0} {1}".format(config["ros_package"], config["launch_file"]),
                "launch_rviz": config["launch_rviz"],
                "odom_topic": config["odom_topic"],
                "pointcloud_topic": config["pointcloud_topic"],
                "command_topic": config["command_topic"],
                "goal": config["goal"],
                "ros_log_dir": env["ROS_LOG_DIR"],
            },
        )

        roslaunch_process = None
        viewer_process = None
        probe_process = None
        telemetry_queue = Queue()
        try:
            roslaunch_process = launch_roslaunch(config, sink, env, config["ros_package"], config["launch_file"], "ego_planner")
            if config["launch_rviz"]:
                viewer_process = launch_roslaunch(config, sink, env, "ego_planner", "rviz.launch", "rviz")
            probe_process = launch_telemetry_probe(config, sink, env, telemetry_queue)
            goal_result = run_goal_publisher(config, sink, env)
            sink.emit_event("info", "manual goal trigger finished", goal_result)
            summary = stream_telemetry(config, sink, telemetry_queue, roslaunch_process)
            summary["goal_publisher"] = goal_result
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
            if not stop_roslaunch(roslaunch_process, sink, "ego_planner", wait_timeout_s=10.0):
                shutdown_ros_nodes(config, sink, env)
                terminate_process(roslaunch_process, sink, "ego_planner", stop_signal=signal.SIGTERM, wait_timeout_s=4.0)


def build_runtime_config(scenario):
    backend_options = dict(scenario.get("backend_options", {}))
    workspace_dir = resolve_workspace_dir(backend_options.get("ros_workspace_dir"))
    workspace_setup = workspace_dir / "devel" / "setup.bash" if workspace_dir is not None else Path("")
    mission = dict(scenario.get("mission", {}))
    default_goal = {"x": 5.0, "y": 0.0, "z": 1.0}
    configured_goal = mission.get("goal", {})
    goal = {
        "x": float(configured_goal.get("x", backend_options.get("goal_x", default_goal["x"]))),
        "y": float(configured_goal.get("y", backend_options.get("goal_y", default_goal["y"]))),
        "z": float(configured_goal.get("z", backend_options.get("goal_z", default_goal["z"]))),
    }
    return {
        "ros_setup": Path(backend_options.get("ros_setup", DEFAULT_ROS_SETUP)).expanduser(),
        "workspace_dir": workspace_dir,
        "workspace_setup": workspace_setup,
        "ros_package": backend_options.get("ros_package", "ego_planner"),
        "launch_file": backend_options.get("launch_file", "run_in_sim.launch"),
        "launch_rviz": bool(backend_options.get("launch_rviz", False)),
        "probe_script": repo_root() / "scripts" / "ros_telemetry_probe.py",
        "goal_script": repo_root() / "scripts" / "ros_goal_publisher.py",
        "duration_s": float(scenario.get("duration_s", 18.0)),
        "sample_hz": float(scenario.get("update_hz", 5.0)),
        "target_altitude_m": float(scenario.get("target_altitude_m", goal["z"])),
        "startup_timeout_s": float(backend_options.get("startup_timeout_s", 25.0)),
        "goal_timeout_s": float(backend_options.get("goal_timeout_s", 12.0)),
        "goal_reach_tolerance_m": float(backend_options.get("goal_reach_tolerance_m", 0.6)),
        "goal_settle_speed_mps": float(backend_options.get("goal_settle_speed_mps", 0.25)),
        "goal_settle_hold_s": float(backend_options.get("goal_settle_hold_s", 1.0)),
        "odom_topic": backend_options.get("odom_topic", "/visual_slam/odom"),
        "pointcloud_topic": backend_options.get("pointcloud_topic", "/pcl_render_node/cloud"),
        "command_topic": backend_options.get("command_topic", "/planning/pos_cmd"),
        "goal_topic": backend_options.get("goal_topic", "/move_base_simple/goal"),
        "goal_frame_id": backend_options.get("goal_frame_id", "world"),
        "goal": goal,
        "shutdown_nodes": list(backend_options.get("shutdown_nodes", DEFAULT_SHUTDOWN_NODES)),
        "success_criteria": backend_options.get("success_criteria", "trajectory"),
    }


def repo_root():
    return Path(__file__).resolve().parents[2]


def resolve_workspace_dir(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.environ.get("SIM_PLANE_EGO_PLANNER_WS")
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
        raise BackendError("roslaunch exited before the legacy EGO-Planner stack finished startup.")
    return process


def preflight_ros_cleanup(config, sink, env):
    cleanup_live_ros_nodes(
        config["shutdown_nodes"],
        sink,
        env,
        request_message="stale legacy ego_planner nodes detected; requesting cleanup",
        success_message="stale legacy ego_planner nodes removed",
        failure_message="stale legacy ego_planner nodes still present after cleanup",
    )


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
    thread.start()
    stderr_thread = Thread(target=stream_probe_stderr, args=(process.stderr, sink), daemon=True)
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
        sink.emit_backend_log("stderr", "[ros_goal_publisher_stderr] {0}".format(completed.stderr.strip()))

    raw_stdout = completed.stdout.strip()
    if not raw_stdout:
        raise BackendError("ros goal publisher exited without a result.")
    try:
        result = json.loads(raw_stdout.splitlines()[-1])
    except json.JSONDecodeError as exc:
        raise BackendError("ros goal publisher emitted invalid JSON: {0}".format(exc)) from exc
    if completed.returncode != 0:
        raise BackendError("ros goal publisher failed: {0}".format(json.dumps(result, ensure_ascii=False)))
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


def stream_telemetry(config, sink, telemetry_queue, roslaunch_process):
    start_wall = time.time()
    deadline = start_wall + config["duration_s"]
    telemetry_count = 0
    max_altitude_m = 0.0
    max_speed_mps = 0.0
    max_pointcloud_width = 0
    reached_target_altitude = False
    position_cmd_seen = False
    pointcloud_seen = False
    goal_reached = False
    min_goal_distance_m = None
    goal_settled_since = None
    first_sample_seen = False
    first_sample_deadline = start_wall + config["startup_timeout_s"]

    while time.time() <= deadline:
        if roslaunch_process.poll() is not None:
            raise BackendError("roslaunch exited before the configured run duration elapsed.")
        timeout_s = 0.25 if first_sample_seen else max(0.0, min(0.25, first_sample_deadline - time.time()))
        if not first_sample_seen and timeout_s == 0.0:
            raise BackendError("Timed out waiting for /visual_slam/odom telemetry.")
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
        if sample.get("pointcloud_count", 0) > 0 and not pointcloud_seen:
            pointcloud_seen = True
            sink.emit_event(
                "info",
                "local sensing pointcloud detected",
                {
                    "pointcloud_topic": config["pointcloud_topic"],
                    "width": sample.get("pointcloud_width", 0),
                },
            )

        sink.emit_telemetry(sample)
        telemetry_count += 1
        max_altitude_m = max(max_altitude_m, float(sample.get("altitude_m", 0.0)))
        max_speed_mps = max(max_speed_mps, float(sample.get("speed_mps", 0.0)))
        max_pointcloud_width = max(max_pointcloud_width, int(sample.get("pointcloud_width", 0) or 0))
        goal_distance_m = compute_goal_distance_m(config["goal"], sample)
        min_goal_distance_m = (
            goal_distance_m if min_goal_distance_m is None else min(min_goal_distance_m, goal_distance_m)
        )
        if float(sample.get("altitude_m", 0.0)) >= config["target_altitude_m"] * 0.95:
            reached_target_altitude = True
        if goal_distance_m <= config["goal_reach_tolerance_m"] and float(sample.get("speed_mps", 0.0)) <= config["goal_settle_speed_mps"]:
            if goal_settled_since is None:
                goal_settled_since = time.time()
            elif time.time() - goal_settled_since >= config["goal_settle_hold_s"]:
                goal_reached = True
                sink.emit_event(
                    "info",
                    "goal reached",
                    {
                        "goal": config["goal"],
                        "goal_distance_m": round(goal_distance_m, 3),
                        "speed_mps": sample.get("speed_mps", 0.0),
                    },
                )
                break
        else:
            goal_settled_since = None

    return {
        "telemetry_count": telemetry_count,
        "max_altitude_m": round(max_altitude_m, 3),
        "max_speed_mps": round(max_speed_mps, 3),
        "max_pointcloud_width": max_pointcloud_width,
        "pointcloud_seen": pointcloud_seen,
        "target_altitude_reached": reached_target_altitude,
        "position_cmd_seen": position_cmd_seen,
        "goal_reached": goal_reached,
        "min_goal_distance_m": round(min_goal_distance_m, 3) if min_goal_distance_m is not None else None,
        "duration_s": round(time.time() - start_wall, 3),
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


def shutdown_ros_nodes(config, sink, env):
    cleanup_live_ros_nodes(
        config["shutdown_nodes"],
        sink,
        env,
        request_message="requesting ros node shutdown",
    )


def evaluate_run_status(success_criteria, telemetry_summary):
    if success_criteria == "telemetry":
        return "passed" if telemetry_summary["telemetry_count"] > 0 else "failed"
    if success_criteria == "command":
        return "passed" if telemetry_summary["position_cmd_seen"] else "failed"
    if success_criteria == "sensor_stack":
        return "passed" if telemetry_summary["pointcloud_seen"] and telemetry_summary["position_cmd_seen"] else "failed"
    return (
        "passed"
        if telemetry_summary["target_altitude_reached"]
        and telemetry_summary["position_cmd_seen"]
        and telemetry_summary["pointcloud_seen"]
        and telemetry_summary["goal_reached"]
        else "failed"
    )


def build_notes(config):
    notes = [
        "The ego_planner backend launches the dedicated ROS1 catkin workspace under /home/coco/sim_plane_ws/workspaces/ros1_ego_planner.",
        "It auto-publishes a bounded /move_base_simple/goal so the legacy upstream manual-goal launch can run unattended through the shared control surface.",
        "Live telemetry is derived from /visual_slam/odom, /planning/pos_cmd, and /pcl_render_node/cloud.",
    ]
    if config["launch_rviz"]:
        notes.append("RViz was requested as the auxiliary 3D viewer for the legacy planner stack.")
    return notes


def compute_goal_distance_m(goal, sample):
    dx = float(sample["position"]["x_m"]) - float(goal["x"])
    dy = float(sample["position"]["y_m"]) - float(goal["y"])
    dz = float(sample["altitude_m"]) - float(goal["z"])
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def parse_ros_log_event(label, stream_name, line):
    if line.startswith("[FSM]:"):
        return {"level": "info", "message": "fsm transition", "details": {"line": line, "stream": stream_name}}
    if line.startswith("[TRIG]:"):
        return {"level": "info", "message": "planner trigger", "details": {"line": line, "stream": stream_name}}
    if line.startswith("[SAFETY]:"):
        level = "warning" if "EMERGENCY_STOP" in line else "info"
        return {"level": level, "message": "planner safety transition", "details": {"line": line, "stream": stream_name}}
    if (
        "Global Pointcloud received" in line
        or "ready." in line
        or "Failed to generate direction. It doesn't matter." in line
        or "older format" in line
        or "_missing_material_" in line
    ):
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
