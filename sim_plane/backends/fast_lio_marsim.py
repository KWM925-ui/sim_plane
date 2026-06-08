import json
import os
import shlex
import signal
import subprocess
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

from sim_plane.adapters import collect_algorithm_adapter, has_algorithm_adapter, start_algorithm_adapter, validate_algorithm_adapter
from sim_plane.backends.base import Backend, BackendError
from sim_plane.processes import start_log_threads, terminate_process
from sim_plane.ros_master import ensure_ros_master_uri, share_ros_master_uri
from sim_plane.ros_nodes import cleanup_live_ros_nodes


DEFAULT_ROS_SETUP = Path("/opt/ros/noetic/setup.bash")
DEFAULT_MARSIM_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_marsim"),
]
DEFAULT_FAST_LIO_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_fast_lio"),
]
DEFAULT_MARSIM_SHUTDOWN_NODES = [
    "/quad0_pcl_render_node",
    "/quad0_odom_visualization",
    "/quad0_cascadePID_node",
    "/quad0_quadrotor_dynamics",
    "/rvizvisualisation",
]


class FastLIOMARSIMBackend(Backend):
    name = "fast_lio_marsim"

    def validate_environment(self, scenario=None):
        config = build_runtime_config(scenario or {})
        issues = []
        if not config["ros_setup"].is_file():
            issues.append("ROS Noetic setup.bash was not found at /opt/ros/noetic/setup.bash.")
        if config["marsim_workspace_dir"] is None:
            issues.append(
                "MARSIM workspace not found. Build or point to /home/coco/sim_plane_ws/workspaces/ros1_marsim."
            )
        elif not config["marsim_workspace_setup"].is_file():
            issues.append(
                "MARSIM workspace exists but devel/setup.bash is missing. Run ./scripts/build_marsim_ws.sh first."
            )
        if config["fast_lio_workspace_dir"] is None:
            issues.append(
                "FAST_LIO workspace not found. Build or point to /home/coco/sim_plane_ws/workspaces/ros1_fast_lio."
            )
        elif not config["fast_lio_workspace_setup"].is_file():
            issues.append(
                "FAST_LIO workspace exists but devel/setup.bash is missing. Run ./scripts/build_fast_lio_ws.sh first."
            )
        if not config["probe_script"].is_file():
            issues.append("ROS telemetry probe script is missing from scripts/ros_telemetry_probe.py.")
        if not config["fast_lio_launch_file"].is_file():
            issues.append("FAST_LIO wrapper launch file is missing from sim_plane/ros/fast_lio_marsim.launch.")
        issues.extend(
            validate_algorithm_adapter(
                (scenario or {}).get("algorithm_adapter"),
                context=build_algorithm_adapter_context(scenario or {}, config),
            )
        )
        return issues

    def run(self, scenario, sink):
        config = build_runtime_config(scenario)
        issues = self.validate_environment(scenario)
        if issues:
            raise BackendError("; ".join(issues))

        marsim_env = load_sourced_environment([config["ros_setup"], config["marsim_workspace_setup"]])
        fast_lio_env = load_sourced_environment([config["ros_setup"], config["fast_lio_workspace_setup"]])
        probe_env = load_sourced_environment([config["ros_setup"]])
        share_ros_master_uri(marsim_env, fast_lio_env, probe_env)
        marsim_env = prepare_ros_runtime_env(marsim_env, sink.artifact_writer.artifact_dir)
        fast_lio_env = prepare_ros_runtime_env(fast_lio_env, sink.artifact_writer.artifact_dir)
        probe_env = prepare_ros_runtime_env(probe_env, sink.artifact_writer.artifact_dir)
        sink.emit_event(
            "info",
            "fast_lio_marsim launch plan",
            {
                "marsim_workspace_dir": str(config["marsim_workspace_dir"]),
                "fast_lio_workspace_dir": str(config["fast_lio_workspace_dir"]),
                "marsim_launch": "{0} {1}".format(config["marsim_ros_package"], config["marsim_launch_file"]),
                "fast_lio_launch": str(config["fast_lio_launch_file"]),
                "launch_rviz": config["launch_rviz"],
                "fast_lio_launch_rviz": config["fast_lio_launch_rviz"],
                "marsim_launch_rviz": config["marsim_launch_rviz"],
                "use_gpu": config["use_gpu"],
                "odom_topic": config["odom_topic"],
                "pointcloud_topic": config["pointcloud_topic"],
                "command_topic": config["command_topic"],
                "map_topic": config["map_topic"],
                "pcd_save_en": False,
                "ros_log_dir": marsim_env["ROS_LOG_DIR"],
            },
        )

        marsim_process = None
        fast_lio_process = None
        probe_process = None
        adapter_handle = None
        adapter_report = {"metrics": {}, "notes": []}
        adapter_collected = False
        telemetry_queue = Queue()
        try:
            marsim_process = launch_marsim(config, sink, marsim_env)
            fast_lio_process = launch_fast_lio(config, sink, fast_lio_env)
            probe_process = launch_telemetry_probe(config, sink, probe_env, telemetry_queue)
            if has_algorithm_adapter(scenario.get("algorithm_adapter")):
                adapter_handle = start_algorithm_adapter(
                    scenario.get("algorithm_adapter"),
                    sink,
                    context=build_algorithm_adapter_context(scenario, config, env=probe_env),
                )
            summary = stream_telemetry(config, sink, telemetry_queue, marsim_process, fast_lio_process)
            adapter_report = collect_algorithm_adapter(
                adapter_handle,
                timeout_s=float((scenario.get("algorithm_adapter") or {}).get("join_timeout_s", 8.0)),
                request_stop=adapter_handle is not None,
            )
            adapter_collected = True
            summary.update(adapter_report["metrics"])
            return {
                "status": evaluate_run_status(config["success_criteria"], summary),
                "backend": self.name,
                "vehicle": scenario["vehicle"],
                "scenario_name": scenario["name"],
                "metrics": summary,
                "notes": build_notes(config, adapter_notes=adapter_report["notes"]),
            }
        finally:
            if adapter_handle is not None and not adapter_collected:
                collect_algorithm_adapter(
                    adapter_handle,
                    timeout_s=float((scenario.get("algorithm_adapter") or {}).get("join_timeout_s", 8.0)),
                    request_stop=True,
                )
            terminate_process(probe_process, sink, "ros_probe", stop_signal=signal.SIGINT, wait_timeout_s=4.0)
            fast_lio_wait_timeout_s = 20.0 if config["fast_lio_launch_rviz"] else 8.0
            if not stop_roslaunch(fast_lio_process, sink, "fast_lio", wait_timeout_s=fast_lio_wait_timeout_s):
                terminate_process(fast_lio_process, sink, "fast_lio", stop_signal=signal.SIGTERM, wait_timeout_s=4.0)
            if config["marsim_launch_rviz"]:
                shutdown_specific_ros_nodes(["/rvizvisualisation"], sink, marsim_env, "pre-stopping RViz node")
            if not stop_roslaunch(marsim_process, sink, "marsim", wait_timeout_s=10.0):
                shutdown_ros_nodes(config, sink, marsim_env)
                terminate_process(marsim_process, sink, "marsim", stop_signal=signal.SIGTERM, wait_timeout_s=4.0)


def build_runtime_config(scenario):
    backend_options = dict(scenario.get("backend_options", {}))
    marsim_workspace_dir = resolve_marsim_workspace_dir(backend_options.get("marsim_workspace_dir"))
    fast_lio_workspace_dir = resolve_fast_lio_workspace_dir(
        backend_options.get("fast_lio_workspace_dir") or backend_options.get("ros_workspace_dir")
    )
    return {
        "ros_setup": Path(backend_options.get("ros_setup", DEFAULT_ROS_SETUP)).expanduser(),
        "marsim_workspace_dir": marsim_workspace_dir,
        "marsim_workspace_setup": marsim_workspace_dir / "devel" / "setup.bash"
        if marsim_workspace_dir is not None
        else Path(""),
        "fast_lio_workspace_dir": fast_lio_workspace_dir,
        "fast_lio_workspace_setup": fast_lio_workspace_dir / "devel" / "setup.bash"
        if fast_lio_workspace_dir is not None
        else Path(""),
        "marsim_ros_package": backend_options.get("marsim_ros_package", "test_interface"),
        "marsim_launch_file": backend_options.get("marsim_launch_file", "single_drone_avia.launch"),
        "fast_lio_launch_file": repo_root() / "sim_plane" / "ros" / "fast_lio_marsim.launch",
        "launch_rviz": bool(backend_options.get("launch_rviz", False)),
        "fast_lio_launch_rviz": bool(
            backend_options.get("fast_lio_launch_rviz", backend_options.get("launch_rviz", False))
        ),
        "marsim_launch_rviz": bool(backend_options.get("marsim_launch_rviz", False)),
        "use_gpu": bool(backend_options.get("use_gpu", False)),
        "probe_script": repo_root() / "scripts" / "ros_telemetry_probe.py",
        "duration_s": float(scenario.get("duration_s", 20.0)),
        "sample_hz": float(scenario.get("update_hz", 5.0)),
        "target_altitude_m": float(scenario.get("target_altitude_m", 1.0)),
        "startup_timeout_s": float(backend_options.get("startup_timeout_s", 25.0)),
        "odom_topic": backend_options.get("odom_topic", "/Odometry"),
        "pointcloud_topic": backend_options.get("pointcloud_topic", "/quad0_pcl_render_node/sensor_cloud"),
        "map_topic": backend_options.get("map_topic", "/map_generator/global_cloud"),
        "command_topic": backend_options.get("command_topic", ""),
        "shutdown_nodes": list(backend_options.get("shutdown_nodes", DEFAULT_MARSIM_SHUTDOWN_NODES)),
        "success_criteria": backend_options.get("success_criteria", "estimation"),
    }


def repo_root():
    return Path(__file__).resolve().parents[2]


def resolve_marsim_workspace_dir(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.environ.get("SIM_PLANE_MARSIM_WS")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(DEFAULT_MARSIM_WORKSPACE_CANDIDATES)

    for candidate in candidates:
        if (candidate / "src").is_dir():
            return candidate.resolve()
    return None


def resolve_fast_lio_workspace_dir(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.environ.get("SIM_PLANE_FAST_LIO_WS")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(DEFAULT_FAST_LIO_WORKSPACE_CANDIDATES)

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
    ros_home = Path(artifact_dir) / "ros_home"
    ros_log_dir = Path(artifact_dir) / "ros_logs"
    ros_home.mkdir(parents=True, exist_ok=True)
    ros_log_dir.mkdir(parents=True, exist_ok=True)
    env["ROS_HOME"] = str(ros_home)
    env["ROS_LOG_DIR"] = str(ros_log_dir)
    env["ROS_HOSTNAME"] = "127.0.0.1"
    env["ROS_IP"] = "127.0.0.1"
    ensure_ros_master_uri(env)
    return env


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
        raise BackendError("MARSIM roslaunch exited before the FAST_LIO stack finished startup.")
    return process


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


def launch_telemetry_probe(config, sink, env, telemetry_queue):
    command = [
        "python3",
        str(config["probe_script"]),
        "--odom-topic",
        config["odom_topic"],
        "--pointcloud-topic",
        config["pointcloud_topic"],
        "--sample-hz",
        str(config["sample_hz"]),
        "--target-altitude-m",
        str(config["target_altitude_m"]),
    ]
    if config["command_topic"]:
        command.extend(["--command-topic", config["command_topic"]])
    sink.emit_event(
        "info",
        "launching ros telemetry probe",
        {"command": " ".join(shlex.quote(part) for part in command)},
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


def stream_telemetry(config, sink, telemetry_queue, marsim_process, fast_lio_process):
    start_wall = time.time()
    deadline = start_wall + config["duration_s"]
    telemetry_count = 0
    max_altitude_m = 0.0
    max_speed_mps = 0.0
    reached_target_altitude = False
    pointcloud_seen = False
    max_pointcloud_width = 0
    first_sample_seen = False
    first_sample_deadline = start_wall + config["startup_timeout_s"]
    pointcloud_deadline = start_wall + config["startup_timeout_s"]
    position_cmd_seen = False
    max_position_cmd_count = 0

    while time.time() <= deadline:
        if marsim_process.poll() is not None:
            raise BackendError("MARSIM roslaunch exited before the configured FAST_LIO run duration elapsed.")
        if fast_lio_process.poll() is not None:
            raise BackendError("FAST_LIO roslaunch exited before the configured estimation run duration elapsed.")

        now = time.time()
        if not first_sample_seen and now > first_sample_deadline:
            raise BackendError("Timed out waiting for FAST_LIO /Odometry telemetry.")
        if not pointcloud_seen and now > pointcloud_deadline:
            raise BackendError("Timed out waiting for FAST_LIO input pointcloud telemetry.")

        try:
            sample = telemetry_queue.get(timeout=0.25)
        except Empty:
            continue

        if not first_sample_seen:
            first_sample_seen = True
            sink.emit_event(
                "info",
                "fast_lio odometry received",
                {
                    "odom_topic": config["odom_topic"],
                    "position": sample["position"],
                    "altitude_m": sample["altitude_m"],
                },
            )
        if sample.get("pointcloud_count", 0) > 0 and not pointcloud_seen:
            pointcloud_seen = True
            sink.emit_event(
                "info",
                "fast_lio input cloud detected",
                {
                    "pointcloud_topic": config["pointcloud_topic"],
                    "pointcloud_width": sample.get("pointcloud_width", 0),
                },
            )
        if sample.get("position_cmd_count", 0) > 0 and not position_cmd_seen:
            position_cmd_seen = True
            sink.emit_event(
                "info",
                "position command stream detected",
                {
                    "command_topic": config["command_topic"],
                    "count": sample["position_cmd_count"],
                },
            )

        sink.emit_telemetry(sample)
        telemetry_count += 1
        max_altitude_m = max(max_altitude_m, float(sample.get("altitude_m", 0.0)))
        max_speed_mps = max(max_speed_mps, float(sample.get("speed_mps", 0.0)))
        max_pointcloud_width = max(max_pointcloud_width, int(sample.get("pointcloud_width", 0) or 0))
        max_position_cmd_count = max(max_position_cmd_count, int(sample.get("position_cmd_count", 0) or 0))
        if float(sample.get("altitude_m", 0.0)) >= config["target_altitude_m"] * 0.95:
            reached_target_altitude = True

    return {
        "telemetry_count": telemetry_count,
        "odometry_seen": first_sample_seen,
        "pointcloud_seen": pointcloud_seen,
        "position_cmd_seen": position_cmd_seen,
        "max_position_cmd_count": max_position_cmd_count,
        "max_pointcloud_width": max_pointcloud_width,
        "max_altitude_m": round(max_altitude_m, 3),
        "max_speed_mps": round(max_speed_mps, 3),
        "target_altitude_reached": reached_target_altitude,
        "duration_s": config["duration_s"],
        "launch_rviz": config["launch_rviz"],
        "fast_lio_launch_rviz": config["fast_lio_launch_rviz"],
        "marsim_launch_rviz": config["marsim_launch_rviz"],
        "pcd_save_disabled": True,
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
    if not config["shutdown_nodes"]:
        return
    shutdown_specific_ros_nodes(config["shutdown_nodes"], sink, env, "requesting ros node shutdown")


def shutdown_specific_ros_nodes(nodes, sink, env, message):
    cleanup_live_ros_nodes(
        nodes,
        sink,
        env,
        request_message=message,
    )


def evaluate_run_status(success_criteria, telemetry_summary):
    if success_criteria == "telemetry":
        return "passed" if telemetry_summary["telemetry_count"] > 0 else "failed"
    if success_criteria == "command":
        return "passed" if telemetry_summary["position_cmd_seen"] else "failed"
    if success_criteria == "estimation_with_commands":
        return (
            "passed"
            if telemetry_summary["telemetry_count"] > 0
            and telemetry_summary["pointcloud_seen"]
            and telemetry_summary["position_cmd_seen"]
            else "failed"
        )
    return "passed" if telemetry_summary["telemetry_count"] > 0 and telemetry_summary["pointcloud_seen"] else "failed"


def build_notes(config, adapter_notes=None):
    notes = [
        "The fast_lio_marsim backend composes the dedicated ROS1 workspaces under /home/coco/sim_plane_ws/workspaces/ros1_marsim and /home/coco/sim_plane_ws/workspaces/ros1_fast_lio.",
        "Live telemetry is derived from FAST_LIO's /Odometry output and the MARSIM input cloud on /quad0_pcl_render_node/sensor_cloud.",
        "The repo-local wrapper launch disables FAST_LIO's default shutdown-time PCD dump so artifacts stay bounded to the run directory.",
    ]
    if config["launch_rviz"]:
        notes.append("A viewer was requested for this estimation-stack probe.")
    else:
        notes.append("All RViz viewers were disabled for a lighter headless estimation-stack probe.")
    if config["fast_lio_launch_rviz"]:
        notes.append("FAST_LIO's estimator RViz path was enabled.")
    if config["marsim_launch_rviz"]:
        notes.append("MARSIM's scene RViz path was enabled.")
    if config["command_topic"]:
        notes.append(
            "When command_topic is configured, the same MARSIM controller chain consumes /quad_0/planning/pos_cmd-compatible PositionCommand traffic from the user algorithm."
        )
    notes.extend(adapter_notes or [])
    return notes


def build_algorithm_adapter_context(scenario, config, env=None):
    runtime_env = env or {}
    return {
        "backend": FastLIOMARSIMBackend.name,
        "vehicle": scenario.get("vehicle"),
        "scenario_name": scenario.get("name"),
        "expected_duration_s": config["duration_s"],
        "startup_timeout_s": config["startup_timeout_s"],
        "ros_setup": str(config["ros_setup"]),
        "workspace_setups": [
            str(config["fast_lio_workspace_setup"]),
            str(config["marsim_workspace_setup"]),
        ],
        "ros_master_uri": runtime_env.get("ROS_MASTER_URI"),
        "ros_hostname": runtime_env.get("ROS_HOSTNAME"),
        "ros_ip": runtime_env.get("ROS_IP"),
        "odom_topic": config["odom_topic"],
        "pointcloud_topic": config["pointcloud_topic"],
        "command_topic": config["command_topic"],
        "map_topic": config["map_topic"],
        "launch_rviz": config["launch_rviz"],
    }


def parse_marsim_log_event(label, stream_name, line):
    if (
        "Global Pointcloud received" in line
        or "Normal compute finished" in line
        or "rviz version" in line
        or "process has finished cleanly" in line
        or "Shutdown request received" in line
        or "Reason given for shutdown: [user request]" in line
        or ("rvizvisualisation" in line and "escalating to SIGTERM" in line)
    ):
        return {"level": "info", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "terminate called after throwing" in line or "[ERROR]" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "[WARN]" in line or "Failed to find match for field 'intensity'" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
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


def parse_ros_probe_event(label, stream_name, line):
    if "Traceback" in line or "ERROR" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    return None
