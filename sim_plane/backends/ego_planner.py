import os
import shlex
import signal
import subprocess
import time
from pathlib import Path
from queue import Empty, Queue

from sim_plane.backends.base import Backend, BackendError
from sim_plane.backends.ego_runtime import (
    DEFAULT_EGO_WORKSPACE_CANDIDATES,
    evaluate_run_status,
    launch_telemetry_probe,
    parse_ros_log_event,
    run_goal_publisher,
)
from sim_plane.backends.planner_goal import (
    compute_goal_distance_m,
    finalize_goal_reach_diagnostics,
    make_goal_reach_diagnostics,
    sample_time_seconds,
    update_goal_reach_diagnostics,
    update_goal_reach_state,
)
from sim_plane.backends.ros_runtime import (
    DEFAULT_ROS_SETUP,
    load_sourced_environment,
    prepare_ros_runtime_env,
    repo_root,
    resolve_workspace_dir as resolve_ros_workspace_dir,
    shutdown_ros_nodes,
    stop_roslaunch,
)
from sim_plane.processes import start_log_threads, terminate_process
from sim_plane.ros_nodes import cleanup_live_ros_nodes


DEFAULT_WORKSPACE_CANDIDATES = DEFAULT_EGO_WORKSPACE_CANDIDATES
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


def resolve_workspace_dir(explicit_path=None):
    return resolve_ros_workspace_dir(
        explicit_path,
        env_var="SIM_PLANE_EGO_PLANNER_WS",
        candidates=DEFAULT_WORKSPACE_CANDIDATES,
    )


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
    goal_diagnostics = make_goal_reach_diagnostics(
        tolerance_m=config["goal_reach_tolerance_m"],
        settle_speed_mps=config["goal_settle_speed_mps"],
        settle_hold_s=config["goal_settle_hold_s"],
    )
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
    }
    summary.update(finalize_goal_reach_diagnostics(goal_diagnostics, goal_reached=goal_reached))
    return summary


def build_notes(config):
    notes = [
        "The ego_planner backend launches the dedicated ROS1 catkin workspace under /home/coco/sim_plane_ws/workspaces/ros1_ego_planner.",
        "It auto-publishes a bounded /move_base_simple/goal so the legacy upstream manual-goal launch can run unattended through the shared control surface.",
        "Live telemetry is derived from /visual_slam/odom, /planning/pos_cmd, and /pcl_render_node/cloud.",
    ]
    if config["launch_rviz"]:
        notes.append("RViz was requested as the auxiliary 3D viewer for the legacy planner stack.")
    return notes
