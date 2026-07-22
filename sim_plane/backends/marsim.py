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
from sim_plane.backends.marsim_runtime import parse_marsim_log_event as parse_ros_log_event
from sim_plane.backends.ros_runtime import (
    DEFAULT_ROS_SETUP,
    load_sourced_environment,
    prepare_ros_runtime_env,
    repo_root,
    resolve_workspace_dir as resolve_ros_workspace_dir,
    shutdown_ros_nodes,
    shutdown_specific_ros_nodes,
    stop_roslaunch,
)
from sim_plane.processes import register_background_threads, start_log_threads, terminate_process


DEFAULT_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_marsim"),
]
DEFAULT_SHUTDOWN_NODES = [
    "/quad0_pcl_render_node",
    "/quad0_odom_visualization",
    "/quad0_cascadePID_node",
    "/quad0_quadrotor_dynamics",
    "/rvizvisualisation",
]


class MARSIMBackend(Backend):
    name = "marsim"

    def validate_environment(self, scenario=None):
        config = build_runtime_config(scenario or {})
        issues = []
        if not config["ros_setup"].is_file():
            issues.append("ROS Noetic setup.bash was not found at /opt/ros/noetic/setup.bash.")
        if config["workspace_dir"] is None:
            issues.append(
                "MARSIM workspace not found. Build or point to /home/coco/sim_plane_ws/workspaces/ros1_marsim."
            )
        elif not config["workspace_setup"].is_file():
            issues.append(
                "MARSIM workspace exists but devel/setup.bash is missing. Run ./scripts/build_marsim_ws.sh first."
            )
        if not config["probe_script"].is_file():
            issues.append("ROS telemetry probe script is missing from scripts/ros_telemetry_probe.py.")
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

        env = load_sourced_environment([config["ros_setup"], config["workspace_setup"]])
        env = prepare_ros_runtime_env(env, sink.artifact_writer.artifact_dir)
        sink.emit_event(
            "info",
            "marsim launch plan",
            {
                "workspace_dir": str(config["workspace_dir"]),
                "launch": "{0} {1}".format(config["ros_package"], config["launch_file"]),
                "launch_rviz": config["launch_rviz"],
                "use_gpu": config["use_gpu"],
                "odom_topic": config["odom_topic"],
                "pointcloud_topic": config["pointcloud_topic"],
                "command_topic": config["command_topic"],
                "map_topic": config["map_topic"],
                "ros_log_dir": env["ROS_LOG_DIR"],
            },
        )

        roslaunch_process = None
        probe_process = None
        adapter_handle = None
        adapter_report = {"metrics": {}, "notes": []}
        adapter_collected = False
        telemetry_queue = Queue()
        try:
            roslaunch_process = launch_roslaunch(config, sink, env)
            probe_process = launch_telemetry_probe(config, sink, env, telemetry_queue)
            if has_algorithm_adapter(scenario.get("algorithm_adapter")):
                adapter_handle = start_algorithm_adapter(
                    scenario.get("algorithm_adapter"),
                    sink,
                    context=build_algorithm_adapter_context(scenario, config, env=env),
                )
            summary = stream_telemetry(config, sink, telemetry_queue, roslaunch_process)
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
            if config["launch_rviz"]:
                shutdown_specific_ros_nodes(["/rvizvisualisation"], sink, env, "pre-stopping RViz node")
            roslaunch_wait_timeout_s = 20.0 if config["launch_rviz"] and config["use_gpu"] else 10.0
            if not stop_roslaunch(roslaunch_process, sink, "marsim", wait_timeout_s=roslaunch_wait_timeout_s):
                shutdown_ros_nodes(config, sink, env)
                terminate_process(roslaunch_process, sink, "marsim", stop_signal=signal.SIGTERM, wait_timeout_s=4.0)


def build_runtime_config(scenario):
    backend_options = dict(scenario.get("backend_options", {}))
    workspace_dir = resolve_workspace_dir(backend_options.get("ros_workspace_dir"))
    workspace_setup = workspace_dir / "devel" / "setup.bash" if workspace_dir is not None else Path("")
    return {
        "ros_setup": Path(backend_options.get("ros_setup", DEFAULT_ROS_SETUP)).expanduser(),
        "workspace_dir": workspace_dir,
        "workspace_setup": workspace_setup,
        "ros_package": backend_options.get("ros_package", "test_interface"),
        "launch_file": backend_options.get("launch_file", "single_drone_avia.launch"),
        "launch_rviz": bool(backend_options.get("launch_rviz", True)),
        "use_gpu": bool(backend_options.get("use_gpu", False)),
        "probe_script": repo_root() / "scripts" / "ros_telemetry_probe.py",
        "duration_s": float(scenario.get("duration_s", 18.0)),
        "sample_hz": float(scenario.get("update_hz", 5.0)),
        "target_altitude_m": float(scenario.get("target_altitude_m", 1.0)),
        "startup_timeout_s": float(backend_options.get("startup_timeout_s", 20.0)),
        "odom_topic": backend_options.get("odom_topic", "/quad_0/lidar_slam/odom"),
        "pointcloud_topic": backend_options.get("pointcloud_topic", "/quad0_pcl_render_node/cloud"),
        "map_topic": backend_options.get("map_topic", "/map_generator/global_cloud"),
        "command_topic": backend_options.get("command_topic", ""),
        "shutdown_nodes": list(backend_options.get("shutdown_nodes", DEFAULT_SHUTDOWN_NODES)),
        "success_criteria": backend_options.get("success_criteria", "sensor_stack"),
    }


def resolve_workspace_dir(explicit_path=None):
    return resolve_ros_workspace_dir(
        explicit_path,
        env_var="SIM_PLANE_MARSIM_WS",
        candidates=DEFAULT_WORKSPACE_CANDIDATES,
    )


def launch_roslaunch(config, sink, env):
    command = [
        "roslaunch",
        config["ros_package"],
        config["launch_file"],
        "launch_rviz:={0}".format("true" if config["launch_rviz"] else "false"),
        "use_gpu_:={0}".format("true" if config["use_gpu"] else "false"),
    ]
    sink.emit_event(
        "info",
        "launching roslaunch",
        {"label": "marsim", "command": " ".join(shlex.quote(part) for part in command), "cwd": str(config["workspace_dir"])},
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
    start_log_threads(process, sink, "marsim", event_parser=parse_ros_log_event)
    time.sleep(1.5)
    if process.poll() is not None:
        raise BackendError("roslaunch exited before the MARSIM stack finished startup.")
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
    local_cloud_seen = False
    max_pointcloud_width = 0
    first_sample_seen = False
    first_sample_deadline = start_wall + config["startup_timeout_s"]
    pointcloud_deadline = start_wall + config["startup_timeout_s"]
    position_cmd_seen = False
    max_position_cmd_count = 0

    while time.time() <= deadline:
        if roslaunch_process.poll() is not None:
            raise BackendError("roslaunch exited before the configured MARSIM run duration elapsed.")

        now = time.time()
        if not first_sample_seen and now > first_sample_deadline:
            raise BackendError("Timed out waiting for MARSIM odometry telemetry.")
        if not local_cloud_seen and now > pointcloud_deadline:
            raise BackendError("Timed out waiting for MARSIM local cloud telemetry.")

        try:
            sample = telemetry_queue.get(timeout=0.25)
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
        if sample.get("pointcloud_count", 0) > 0 and not local_cloud_seen:
            local_cloud_seen = True
            sink.emit_event(
                "info",
                "local cloud stream detected",
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
        "pointcloud_seen": local_cloud_seen,
        "position_cmd_seen": position_cmd_seen,
        "max_position_cmd_count": max_position_cmd_count,
        "max_pointcloud_width": max_pointcloud_width,
        "max_altitude_m": round(max_altitude_m, 3),
        "max_speed_mps": round(max_speed_mps, 3),
        "target_altitude_reached": reached_target_altitude,
        "duration_s": config["duration_s"],
        "launch_rviz": config["launch_rviz"],
        "use_gpu": config["use_gpu"],
    }


def evaluate_run_status(success_criteria, telemetry_summary):
    if success_criteria == "telemetry":
        return "passed" if telemetry_summary["telemetry_count"] > 0 else "failed"
    if success_criteria == "command":
        return "passed" if telemetry_summary["position_cmd_seen"] else "failed"
    if success_criteria == "sensor_stack_with_commands":
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
        "The marsim backend launches the dedicated ROS1 catkin workspace under /home/coco/sim_plane_ws/workspaces/ros1_marsim.",
        "Live telemetry is derived from /quad_0/lidar_slam/odom and the local sensing cloud on /quad0_pcl_render_node/cloud.",
    ]
    if config["launch_rviz"]:
        notes.append("RViz was requested through MARSIM's built-in 3D launch path.")
    else:
        notes.append("RViz was disabled for a lighter headless sensor-stack probe.")
    if config["use_gpu"]:
        notes.append("The GPU local sensing path was requested for this MARSIM run.")
    if config["command_topic"]:
        notes.append(
            "When command_topic is configured, the same MARSIM controller chain consumes /quad_0/planning/pos_cmd-compatible PositionCommand traffic from the user algorithm."
        )
    notes.extend(adapter_notes or [])
    return notes


def build_algorithm_adapter_context(scenario, config, env=None):
    runtime_env = env or {}
    return {
        "backend": MARSIMBackend.name,
        "vehicle": scenario.get("vehicle"),
        "scenario_name": scenario.get("name"),
        "expected_duration_s": config["duration_s"],
        "startup_timeout_s": config["startup_timeout_s"],
        "ros_setup": str(config["ros_setup"]),
        "workspace_setups": [str(config["workspace_setup"])],
        "ros_master_uri": runtime_env.get("ROS_MASTER_URI"),
        "ros_hostname": runtime_env.get("ROS_HOSTNAME"),
        "ros_ip": runtime_env.get("ROS_IP"),
        "odom_topic": config["odom_topic"],
        "pointcloud_topic": config["pointcloud_topic"],
        "command_topic": config["command_topic"],
        "map_topic": config["map_topic"],
        "launch_rviz": config["launch_rviz"],
    }


def parse_ros_probe_event(label, stream_name, line):
    if "Traceback" in line or "ERROR" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    return None
