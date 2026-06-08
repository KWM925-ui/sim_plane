import os
import signal
import shlex
import subprocess
import time
from pathlib import Path
from queue import Empty, Queue

from sim_plane.backends.base import Backend, BackendError
from sim_plane.backends.ego_planner import (
    DEFAULT_ROS_SETUP,
    evaluate_run_status,
    launch_telemetry_probe,
    parse_ros_log_event as parse_ego_log_event,
    run_goal_publisher,
)
from sim_plane.backends.fast_lio_marsim import parse_marsim_log_event
from sim_plane.backends.planner_goal import (
    finalize_goal_reach_diagnostics,
    make_goal_reach_diagnostics,
    sample_time_seconds,
    update_goal_reach_diagnostics,
    update_goal_reach_state,
)
from sim_plane.backends.marsim import (
    load_sourced_environment,
    prepare_ros_runtime_env,
    shutdown_specific_ros_nodes,
    shutdown_ros_nodes,
    stop_roslaunch,
)
from sim_plane.processes import start_log_threads, terminate_process
from sim_plane.ros_master import share_ros_master_uri
from sim_plane.ros_nodes import cleanup_live_ros_nodes


DEFAULT_MARSIM_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_marsim"),
]
DEFAULT_EGO_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_ego_planner"),
]
DEFAULT_SHUTDOWN_NODES = [
    "/quad0_pcl_render_node",
    "/quad0_odom_visualization",
    "/quad0_cascadePID_node",
    "/quad0_quadrotor_dynamics",
    "/rvizvisualisation",
    "/ego_planner_node",
    "/traj_server",
    "/waypoint_generator",
]


class EgoPlannerMARSIMBackend(Backend):
    name = "ego_planner_marsim"

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
        if config["ego_workspace_dir"] is None:
            issues.append(
                "Legacy EGO-Planner workspace not found. Build or point to /home/coco/sim_plane_ws/workspaces/ros1_ego_planner."
            )
        elif not config["ego_workspace_setup"].is_file():
            issues.append(
                "Legacy EGO-Planner workspace exists but devel/setup.bash is missing. Run ./scripts/build_ego_planner_ws.sh first."
            )
        if not config["probe_script"].is_file():
            issues.append("ROS telemetry probe script is missing from scripts/ros_telemetry_probe.py.")
        if not config["goal_script"].is_file():
            issues.append("ROS goal publisher script is missing from scripts/ros_goal_publisher.py.")
        if not config["planner_launch_file"].is_file():
            issues.append("The repo-local planner-on-scene launch wrapper is missing from sim_plane/ros/ego_planner_marsim.launch.")
        return issues

    def run(self, scenario, sink):
        config = build_runtime_config(scenario)
        issues = self.validate_environment(scenario)
        if issues:
            raise BackendError("; ".join(issues))

        marsim_env = load_sourced_environment([config["ros_setup"], config["marsim_workspace_setup"]])
        ego_env = load_sourced_environment([config["ros_setup"], config["ego_workspace_setup"]])
        share_ros_master_uri(marsim_env, ego_env)
        marsim_env = prepare_ros_runtime_env(marsim_env, sink.artifact_writer.artifact_dir)
        ego_env = prepare_ros_runtime_env(ego_env, sink.artifact_writer.artifact_dir)
        preflight_ros_cleanup(config, sink, marsim_env)

        sink.emit_event(
            "info",
            "ego_planner_marsim launch plan",
            {
                "marsim_workspace_dir": str(config["marsim_workspace_dir"]),
                "ego_workspace_dir": str(config["ego_workspace_dir"]),
                "marsim_launch": "{0} {1}".format(config["marsim_ros_package"], config["marsim_launch_file"]),
                "planner_launch": str(config["planner_launch_file"]),
                "launch_rviz": config["launch_rviz"],
                "use_gpu": config["use_gpu"],
                "odom_topic": config["odom_topic"],
                "pointcloud_topic": config["pointcloud_topic"],
                "command_topic": config["command_topic"],
                "goal": config["goal"],
                "cloud_only": True,
                "ros_log_dir": marsim_env["ROS_LOG_DIR"],
            },
        )

        marsim_process = None
        planner_process = None
        probe_process = None
        telemetry_queue = Queue()
        try:
            marsim_process = launch_marsim(config, sink, marsim_env)
            planner_process = launch_planner(config, sink, ego_env)
            probe_process = launch_telemetry_probe(config, sink, ego_env, telemetry_queue)
            goal_result = run_goal_publisher(config, sink, ego_env)
            sink.emit_event("info", "manual goal trigger finished", goal_result)
            summary = stream_telemetry(config, sink, telemetry_queue, marsim_process, planner_process)
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
            if not stop_roslaunch(planner_process, sink, "ego_planner", wait_timeout_s=10.0):
                shutdown_ros_nodes(config, sink, ego_env)
                terminate_process(planner_process, sink, "ego_planner", stop_signal=signal.SIGTERM, wait_timeout_s=4.0)
            marsim_wait_timeout_s = 20.0 if config["marsim_launch_rviz"] else 10.0
            if config["marsim_launch_rviz"]:
                shutdown_specific_ros_nodes(["/rvizvisualisation"], sink, marsim_env, "pre-stopping RViz node")
            if not stop_roslaunch(marsim_process, sink, "marsim", wait_timeout_s=marsim_wait_timeout_s):
                shutdown_ros_nodes(config, sink, marsim_env)
                terminate_process(marsim_process, sink, "marsim", stop_signal=signal.SIGTERM, wait_timeout_s=4.0)


def build_runtime_config(scenario):
    backend_options = dict(scenario.get("backend_options", {}))
    mission = dict(scenario.get("mission", {}))
    configured_goal = dict(mission.get("goal", {}))
    default_goal = {"x": 2.5, "y": 0.0, "z": 1.0}
    marsim_workspace_dir = resolve_workspace_dir(
        explicit_path=backend_options.get("marsim_workspace_dir"),
        env_var="SIM_PLANE_MARSIM_WS",
        candidates=DEFAULT_MARSIM_WORKSPACE_CANDIDATES,
    )
    ego_workspace_dir = resolve_workspace_dir(
        explicit_path=backend_options.get("ego_workspace_dir") or backend_options.get("ros_workspace_dir"),
        env_var="SIM_PLANE_EGO_PLANNER_WS",
        candidates=DEFAULT_EGO_WORKSPACE_CANDIDATES,
    )
    launch_rviz = bool(backend_options.get("launch_rviz", False))
    return {
        "ros_setup": Path(backend_options.get("ros_setup", DEFAULT_ROS_SETUP)).expanduser(),
        "marsim_workspace_dir": marsim_workspace_dir,
        "marsim_workspace_setup": marsim_workspace_dir / "devel" / "setup.bash"
        if marsim_workspace_dir is not None
        else Path(""),
        "ego_workspace_dir": ego_workspace_dir,
        "ego_workspace_setup": ego_workspace_dir / "devel" / "setup.bash" if ego_workspace_dir is not None else Path(""),
        "workspace_dir": ego_workspace_dir,
        "marsim_ros_package": backend_options.get("marsim_ros_package", "test_interface"),
        "marsim_launch_file": backend_options.get("marsim_launch_file", "single_drone_avia.launch"),
        "planner_launch_file": repo_root() / "sim_plane" / "ros" / "ego_planner_marsim.launch",
        "launch_rviz": launch_rviz,
        "marsim_launch_rviz": bool(backend_options.get("marsim_launch_rviz", launch_rviz)),
        "use_gpu": bool(backend_options.get("use_gpu", False)),
        "probe_script": repo_root() / "scripts" / "ros_telemetry_probe.py",
        "goal_script": repo_root() / "scripts" / "ros_goal_publisher.py",
        "duration_s": float(scenario.get("duration_s", 20.0)),
        "sample_hz": float(scenario.get("update_hz", 5.0)),
        "target_altitude_m": float(scenario.get("target_altitude_m", configured_goal.get("z", default_goal["z"]))),
        "startup_timeout_s": float(backend_options.get("startup_timeout_s", 25.0)),
        "goal_timeout_s": float(backend_options.get("goal_timeout_s", 12.0)),
        "goal_reach_tolerance_m": float(backend_options.get("goal_reach_tolerance_m", 0.6)),
        "goal_settle_speed_mps": float(backend_options.get("goal_settle_speed_mps", 0.25)),
        "goal_settle_hold_s": float(backend_options.get("goal_settle_hold_s", 1.0)),
        "odom_topic": backend_options.get("odom_topic", "/quad_0/lidar_slam/odom"),
        "pointcloud_topic": backend_options.get("pointcloud_topic", "/quad0_pcl_render_node/cloud"),
        "command_topic": backend_options.get("command_topic", "/quad_0/planning/pos_cmd"),
        "goal_topic": backend_options.get("goal_topic", "/move_base_simple/goal"),
        "goal_frame_id": backend_options.get("goal_frame_id", "world"),
        "goal": {
            "x": float(configured_goal.get("x", backend_options.get("goal_x", default_goal["x"]))),
            "y": float(configured_goal.get("y", backend_options.get("goal_y", default_goal["y"]))),
            "z": float(configured_goal.get("z", backend_options.get("goal_z", default_goal["z"]))),
        },
        "shutdown_nodes": list(backend_options.get("shutdown_nodes", DEFAULT_SHUTDOWN_NODES)),
        "success_criteria": backend_options.get("success_criteria", "trajectory"),
    }


def repo_root():
    return Path(__file__).resolve().parents[2]


def resolve_workspace_dir(explicit_path, env_var, candidates):
    ordered = []
    if explicit_path:
        ordered.append(Path(explicit_path).expanduser())
    env_raw = os.environ.get(env_var)
    if env_raw:
        ordered.append(Path(env_raw).expanduser())
    ordered.extend(candidates)
    for candidate in ordered:
        if (candidate / "src").is_dir():
            return candidate.resolve()
    return None


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
        {"label": "marsim", "command": " ".join(shlex.quote(part) for part in command), "cwd": str(config["marsim_workspace_dir"])},
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
        raise BackendError("MARSIM roslaunch exited before the planner-on-scene stack finished startup.")
    return process


def launch_planner(config, sink, env):
    command = ["roslaunch", str(config["planner_launch_file"])]
    sink.emit_event(
        "info",
        "launching roslaunch",
        {"label": "ego_planner", "command": " ".join(shlex.quote(part) for part in command), "cwd": str(config["ego_workspace_dir"])},
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
    start_log_threads(process, sink, "ego_planner", event_parser=parse_ego_log_event)
    time.sleep(1.5)
    if process.poll() is not None:
        raise BackendError("The planner-on-scene roslaunch exited before the composition finished startup.")
    return process


def stream_telemetry(config, sink, telemetry_queue, marsim_process, planner_process):
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
    goal_diagnostics = make_goal_reach_diagnostics(
        tolerance_m=config["goal_reach_tolerance_m"],
        settle_speed_mps=config["goal_settle_speed_mps"],
        settle_hold_s=config["goal_settle_hold_s"],
    )
    first_sample_seen = False
    first_sample_deadline = start_wall + config["startup_timeout_s"]

    while time.time() <= deadline:
        if marsim_process.poll() is not None:
            raise BackendError("MARSIM roslaunch exited before the configured planner-on-scene run duration elapsed.")
        if planner_process.poll() is not None:
            raise BackendError("The planner roslaunch exited before the configured planner-on-scene run duration elapsed.")
        timeout_s = 0.25 if first_sample_seen else max(0.0, min(0.25, first_sample_deadline - time.time()))
        if not first_sample_seen and timeout_s == 0.0:
            raise BackendError("Timed out waiting for MARSIM odometry telemetry.")
        try:
            sample = telemetry_queue.get(timeout=max(timeout_s, 0.05))
        except Empty:
            continue

        if not first_sample_seen:
            first_sample_seen = True
            sink.emit_event(
                "info",
                "planner-on-scene odometry received",
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
                "scene pointcloud detected",
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
        min_goal_distance_m = goal_distance_m if min_goal_distance_m is None else min(min_goal_distance_m, goal_distance_m)
        sample_now = sample_time_seconds(sample, fallback=time.time() - start_wall)
        if float(sample.get("altitude_m", 0.0)) >= config["target_altitude_m"] * 0.95:
            reached_target_altitude = True
        sample_goal_reached, goal_settled_since = update_goal_reach_state(
            goal_distance_m=goal_distance_m,
            speed_mps=float(sample.get("speed_mps", 0.0)),
            tolerance_m=config["goal_reach_tolerance_m"],
            settle_speed_mps=config["goal_settle_speed_mps"],
            settle_hold_s=config["goal_settle_hold_s"],
            settled_since=goal_settled_since,
            now=sample_now,
        )
        update_goal_reach_diagnostics(
            goal_diagnostics,
            goal_distance_m=goal_distance_m,
            speed_mps=float(sample.get("speed_mps", 0.0)),
            settled_since=goal_settled_since,
            now=sample_now,
        )
        if sample_goal_reached:
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

    summary = {
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
        "cloud_only": True,
    }
    summary.update(finalize_goal_reach_diagnostics(goal_diagnostics, goal_reached=goal_reached))
    return summary


def build_notes(config):
    notes = [
        "The ego_planner_marsim backend composes the dedicated ROS1 workspaces under /home/coco/sim_plane_ws/workspaces/ros1_marsim and /home/coco/sim_plane_ws/workspaces/ros1_ego_planner.",
        "The repo-local wrapper drives legacy EGO-Planner against MARSIM's /quad_0/lidar_slam/odom plus /quad0_pcl_render_node/cloud contract without starting the legacy upstream simulator stack.",
        "This composition is intentionally cloud-only: the wrapper disables the depth path because feeding both MARSIM depth and cloud into GridMap caused repeated false obstacle and emergency-stop churn.",
    ]
    if config["launch_rviz"]:
        notes.append("RViz was requested through the MARSIM scene viewer path.")
    else:
        notes.append("RViz was disabled for a lighter headless planner-on-scene probe.")
    return notes


def compute_goal_distance_m(goal, sample):
    dx = float(sample["position"]["x_m"]) - float(goal["x"])
    dy = float(sample["position"]["y_m"]) - float(goal["y"])
    dz = float(sample["altitude_m"]) - float(goal["z"])
    return (dx * dx + dy * dy + dz * dz) ** 0.5
