import os
import signal
import shlex
import subprocess
import time
from pathlib import Path
from queue import Queue

from sim_plane.backends.base import Backend, BackendError
from sim_plane.backends.ego_planner import (
    DEFAULT_ROS_SETUP,
    evaluate_run_status,
    launch_telemetry_probe,
    parse_ros_log_event as parse_ego_log_event,
    run_goal_publisher,
)
from sim_plane.backends.ego_planner_marsim import (
    launch_marsim,
    preflight_ros_cleanup,
    repo_root,
    resolve_workspace_dir,
    stream_telemetry,
)
from sim_plane.backends.marsim import (
    load_sourced_environment,
    prepare_ros_runtime_env,
    shutdown_specific_ros_nodes,
    shutdown_ros_nodes,
    stop_roslaunch,
)
from sim_plane.processes import start_log_threads, terminate_process


DEFAULT_MARSIM_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_marsim"),
]
DEFAULT_EGO_SWARM_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm"),
]
DEFAULT_SHUTDOWN_NODES = [
    "/quad0_pcl_render_node",
    "/quad0_odom_visualization",
    "/quad0_cascadePID_node",
    "/quad0_quadrotor_dynamics",
    "/rvizvisualisation",
    "/drone_0_ego_planner_node",
    "/drone_0_traj_server",
    "/drone_0_poscmd_2_odom",
    "/drone_0_odom_visualization",
    "/drone_0_pcl_render_node",
    "/random_forest",
    "/waypoint_generator",
]


class EgoPlannerSwarmMARSIMBackend(Backend):
    name = "ego_planner_swarm_marsim"

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
        if config["ego_swarm_workspace_dir"] is None:
            issues.append(
                "EGO-Planner-Swarm workspace not found. Build or point to /home/coco/sim_plane_ws/workspaces/ros1_ego_swarm."
            )
        elif not config["ego_swarm_workspace_setup"].is_file():
            issues.append(
                "EGO-Planner-Swarm workspace exists but devel/setup.bash is missing. Run ./scripts/build_ego_planner_swarm_ws.sh first."
            )
        if not config["probe_script"].is_file():
            issues.append("ROS telemetry probe script is missing from scripts/ros_telemetry_probe.py.")
        if not config["goal_script"].is_file():
            issues.append("ROS goal publisher script is missing from scripts/ros_goal_publisher.py.")
        if not config["planner_launch_file"].is_file():
            issues.append(
                "The repo-local swarm planner-on-scene launch wrapper is missing from sim_plane/ros/ego_planner_swarm_marsim.launch."
            )
        return issues

    def run(self, scenario, sink):
        config = build_runtime_config(scenario)
        issues = self.validate_environment(scenario)
        if issues:
            raise BackendError("; ".join(issues))

        marsim_env = load_sourced_environment([config["ros_setup"], config["marsim_workspace_setup"]])
        swarm_env = load_sourced_environment([config["ros_setup"], config["ego_swarm_workspace_setup"]])
        marsim_env = prepare_ros_runtime_env(marsim_env, sink.artifact_writer.artifact_dir)
        swarm_env = prepare_ros_runtime_env(swarm_env, sink.artifact_writer.artifact_dir)
        preflight_ros_cleanup(config, sink, marsim_env)

        sink.emit_event(
            "info",
            "ego_planner_swarm_marsim launch plan",
            {
                "marsim_workspace_dir": str(config["marsim_workspace_dir"]),
                "ego_swarm_workspace_dir": str(config["ego_swarm_workspace_dir"]),
                "marsim_launch": "{0} {1}".format(config["marsim_ros_package"], config["marsim_launch_file"]),
                "planner_launch": str(config["planner_launch_file"]),
                "launch_rviz": config["launch_rviz"],
                "use_gpu": config["use_gpu"],
                "odom_topic": config["odom_topic"],
                "pointcloud_topic": config["pointcloud_topic"],
                "command_topic": config["command_topic"],
                "goal": config["goal"],
                "manual_goal_mode": True,
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
            planner_process = launch_planner(config, sink, swarm_env)
            probe_process = launch_telemetry_probe(config, sink, swarm_env, telemetry_queue)
            goal_result = run_goal_publisher(config, sink, swarm_env)
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
            if not stop_roslaunch(planner_process, sink, "ego_swarm_planner", wait_timeout_s=10.0):
                shutdown_ros_nodes(config, sink, swarm_env)
                terminate_process(
                    planner_process,
                    sink,
                    "ego_swarm_planner",
                    stop_signal=signal.SIGTERM,
                    wait_timeout_s=4.0,
                )
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
    ego_swarm_workspace_dir = resolve_workspace_dir(
        explicit_path=backend_options.get("ego_swarm_workspace_dir")
        or backend_options.get("ego_workspace_dir")
        or backend_options.get("ros_workspace_dir"),
        env_var="SIM_PLANE_EGO_SWARM_WS",
        candidates=DEFAULT_EGO_SWARM_WORKSPACE_CANDIDATES,
    )
    launch_rviz = bool(backend_options.get("launch_rviz", False))
    return {
        "ros_setup": Path(backend_options.get("ros_setup", DEFAULT_ROS_SETUP)).expanduser(),
        "marsim_workspace_dir": marsim_workspace_dir,
        "marsim_workspace_setup": marsim_workspace_dir / "devel" / "setup.bash"
        if marsim_workspace_dir is not None
        else Path(""),
        "ego_swarm_workspace_dir": ego_swarm_workspace_dir,
        "ego_swarm_workspace_setup": ego_swarm_workspace_dir / "devel" / "setup.bash"
        if ego_swarm_workspace_dir is not None
        else Path(""),
        "workspace_dir": ego_swarm_workspace_dir,
        "marsim_ros_package": backend_options.get("marsim_ros_package", "test_interface"),
        "marsim_launch_file": backend_options.get("marsim_launch_file", "single_drone_avia.launch"),
        "planner_launch_file": repo_root() / "sim_plane" / "ros" / "ego_planner_swarm_marsim.launch",
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


def launch_planner(config, sink, env):
    command = ["roslaunch", str(config["planner_launch_file"])]
    sink.emit_event(
        "info",
        "launching roslaunch",
        {
            "label": "ego_swarm_planner",
            "command": " ".join(shlex.quote(part) for part in command),
            "cwd": str(config["ego_swarm_workspace_dir"]),
        },
    )
    process = subprocess.Popen(
        command,
        cwd=str(config["ego_swarm_workspace_dir"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_log_threads(process, sink, "ego_swarm_planner", event_parser=parse_ego_log_event)
    time.sleep(1.5)
    if process.poll() is not None:
        raise BackendError("The swarm planner-on-scene roslaunch exited before the composition finished startup.")
    return process


def build_notes(config):
    notes = [
        "The ego_planner_swarm_marsim backend composes the dedicated ROS1 workspaces under /home/coco/sim_plane_ws/workspaces/ros1_marsim and /home/coco/sim_plane_ws/workspaces/ros1_ego_swarm.",
        "The repo-local wrapper keeps EGO-Planner-Swarm in manual-goal mode and does not launch the upstream swarm simulator stack or waypoint generator.",
        "This composition is intentionally cloud-only: the wrapper remaps swarm GridMap onto MARSIM's odometry and pointcloud topics while disabling the depth filter to avoid the retired false-obstacle chain.",
    ]
    if config["launch_rviz"]:
        notes.append("RViz was requested through the MARSIM scene viewer path.")
    else:
        notes.append("RViz was disabled for a lighter headless planner-on-scene probe.")
    return notes
