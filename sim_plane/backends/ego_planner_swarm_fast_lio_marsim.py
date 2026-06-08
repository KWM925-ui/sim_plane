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
from sim_plane.backends.ego_planner_fast_lio_marsim import (
    launch_aligned_odom_adapter,
    parse_aligned_odom_log_event,
    stream_telemetry,
)
from sim_plane.backends.ego_planner_marsim import (
    DEFAULT_MARSIM_WORKSPACE_CANDIDATES,
    launch_marsim,
    preflight_ros_cleanup,
    repo_root,
    resolve_workspace_dir,
)
from sim_plane.backends.fast_lio_marsim import (
    DEFAULT_FAST_LIO_WORKSPACE_CANDIDATES,
    launch_fast_lio,
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


DEFAULT_EGO_SWARM_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm"),
]
DEFAULT_SHUTDOWN_NODES = [
    "/quad0_pcl_render_node",
    "/quad0_odom_visualization",
    "/quad0_cascadePID_node",
    "/quad0_quadrotor_dynamics",
    "/rvizvisualisation",
    "/laserMapping",
    "/rviz",
    "/sim_plane_fast_lio_world_odom",
    "/drone_0_ego_planner_node",
    "/drone_0_traj_server",
]


class EgoPlannerSwarmFastLIOMARSIMBackend(Backend):
    name = "ego_planner_swarm_fast_lio_marsim"

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
        if not config["aligned_odom_script"].is_file():
            issues.append("ROS aligned odometry adapter script is missing from scripts/ros_align_odometry.py.")
        if not config["planner_launch_file"].is_file():
            issues.append(
                "The repo-local swarm planner-on-estimator launch wrapper is missing from sim_plane/ros/ego_planner_swarm_fast_lio_marsim.launch."
            )
        if not config["fast_lio_launch_file"].is_file():
            issues.append("FAST_LIO wrapper launch file is missing from sim_plane/ros/fast_lio_marsim.launch.")
        return issues

    def run(self, scenario, sink):
        config = build_runtime_config(scenario)
        issues = self.validate_environment(scenario)
        if issues:
            raise BackendError("; ".join(issues))

        marsim_env = load_sourced_environment([config["ros_setup"], config["marsim_workspace_setup"]])
        fast_lio_env = load_sourced_environment([config["ros_setup"], config["fast_lio_workspace_setup"]])
        swarm_env = load_sourced_environment([config["ros_setup"], config["ego_swarm_workspace_setup"]])
        share_ros_master_uri(marsim_env, fast_lio_env, swarm_env)
        marsim_env = prepare_ros_runtime_env(marsim_env, sink.artifact_writer.artifact_dir)
        fast_lio_env = prepare_ros_runtime_env(fast_lio_env, sink.artifact_writer.artifact_dir)
        swarm_env = prepare_ros_runtime_env(swarm_env, sink.artifact_writer.artifact_dir)
        preflight_ros_cleanup(config, sink, marsim_env)

        sink.emit_event(
            "info",
            "ego_planner_swarm_fast_lio_marsim launch plan",
            {
                "marsim_workspace_dir": str(config["marsim_workspace_dir"]),
                "fast_lio_workspace_dir": str(config["fast_lio_workspace_dir"]),
                "ego_swarm_workspace_dir": str(config["ego_swarm_workspace_dir"]),
                "marsim_launch": "{0} {1}".format(config["marsim_ros_package"], config["marsim_launch_file"]),
                "fast_lio_launch": str(config["fast_lio_launch_file"]),
                "planner_launch": str(config["planner_launch_file"]),
                "aligned_odom_script": str(config["aligned_odom_script"]),
                "launch_rviz": config["launch_rviz"],
                "marsim_launch_rviz": config["marsim_launch_rviz"],
                "fast_lio_launch_rviz": config["fast_lio_launch_rviz"],
                "use_gpu": config["use_gpu"],
                "odom_topic": config["odom_topic"],
                "source_odom_topic": config["source_odom_topic"],
                "reference_odom_topic": config["reference_odom_topic"],
                "pointcloud_topic": config["pointcloud_topic"],
                "command_topic": config["command_topic"],
                "goal": config["goal"],
                "manual_goal_mode": True,
                "cloud_only": True,
                "ros_log_dir": marsim_env["ROS_LOG_DIR"],
            },
        )

        marsim_process = None
        fast_lio_process = None
        aligned_odom_process = None
        planner_process = None
        probe_process = None
        telemetry_queue = Queue()
        try:
            marsim_process = launch_marsim(config, sink, marsim_env)
            fast_lio_process = launch_fast_lio(config, sink, fast_lio_env)
            aligned_odom_process = launch_aligned_odom_adapter(config, sink, swarm_env)
            planner_process = launch_planner(config, sink, swarm_env)
            probe_process = launch_telemetry_probe(config, sink, swarm_env, telemetry_queue)
            goal_result = run_goal_publisher(config, sink, swarm_env)
            sink.emit_event("info", "manual goal trigger finished", goal_result)
            summary = stream_telemetry(
                config,
                sink,
                telemetry_queue,
                marsim_process,
                fast_lio_process,
                planner_process,
            )
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
            terminate_process(
                aligned_odom_process,
                sink,
                "aligned_odom",
                stop_signal=signal.SIGINT,
                wait_timeout_s=4.0,
            )
            if config["fast_lio_launch_rviz"]:
                shutdown_specific_ros_nodes(["/rviz"], sink, fast_lio_env, "pre-stopping FAST_LIO RViz node")
            if not stop_roslaunch(fast_lio_process, sink, "fast_lio", wait_timeout_s=8.0):
                shutdown_ros_nodes(config, sink, fast_lio_env)
                terminate_process(fast_lio_process, sink, "fast_lio", stop_signal=signal.SIGTERM, wait_timeout_s=4.0)
            marsim_wait_timeout_s = 20.0 if config["marsim_launch_rviz"] else 10.0
            if config["marsim_launch_rviz"]:
                shutdown_specific_ros_nodes(["/rvizvisualisation"], sink, marsim_env, "pre-stopping MARSIM RViz node")
            if not stop_roslaunch(marsim_process, sink, "marsim", wait_timeout_s=marsim_wait_timeout_s):
                shutdown_ros_nodes(config, sink, marsim_env)
                terminate_process(marsim_process, sink, "marsim", stop_signal=signal.SIGTERM, wait_timeout_s=4.0)


def build_runtime_config(scenario):
    backend_options = dict(scenario.get("backend_options", {}))
    mission = dict(scenario.get("mission", {}))
    configured_goal = dict(mission.get("goal", {}))
    default_goal = {"x": 2.5, "y": 0.0, "z": 1.0}
    launch_rviz = bool(backend_options.get("launch_rviz", False))
    marsim_workspace_dir = resolve_workspace_dir(
        explicit_path=backend_options.get("marsim_workspace_dir"),
        env_var="SIM_PLANE_MARSIM_WS",
        candidates=DEFAULT_MARSIM_WORKSPACE_CANDIDATES,
    )
    fast_lio_workspace_dir = resolve_workspace_dir(
        explicit_path=backend_options.get("fast_lio_workspace_dir") or backend_options.get("ros_workspace_dir"),
        env_var="SIM_PLANE_FAST_LIO_WS",
        candidates=DEFAULT_FAST_LIO_WORKSPACE_CANDIDATES,
    )
    ego_swarm_workspace_dir = resolve_workspace_dir(
        explicit_path=backend_options.get("ego_swarm_workspace_dir")
        or backend_options.get("ego_workspace_dir"),
        env_var="SIM_PLANE_EGO_SWARM_WS",
        candidates=DEFAULT_EGO_SWARM_WORKSPACE_CANDIDATES,
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
        "ego_swarm_workspace_dir": ego_swarm_workspace_dir,
        "ego_swarm_workspace_setup": ego_swarm_workspace_dir / "devel" / "setup.bash"
        if ego_swarm_workspace_dir is not None
        else Path(""),
        "ego_workspace_dir": ego_swarm_workspace_dir,
        "workspace_dir": ego_swarm_workspace_dir,
        "marsim_ros_package": backend_options.get("marsim_ros_package", "test_interface"),
        "marsim_launch_file": backend_options.get("marsim_launch_file", "single_drone_avia.launch"),
        "fast_lio_launch_file": repo_root() / "sim_plane" / "ros" / "fast_lio_marsim.launch",
        "planner_launch_file": repo_root() / "sim_plane" / "ros" / "ego_planner_swarm_fast_lio_marsim.launch",
        "aligned_odom_script": repo_root() / "scripts" / "ros_align_odometry.py",
        "launch_rviz": launch_rviz,
        "marsim_launch_rviz": bool(backend_options.get("marsim_launch_rviz", launch_rviz)),
        "fast_lio_launch_rviz": bool(backend_options.get("fast_lio_launch_rviz", False)),
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
        "odom_topic": backend_options.get("odom_topic", "/sim_plane/fast_lio_world_odom"),
        "source_odom_topic": backend_options.get("source_odom_topic", "/Odometry"),
        "reference_odom_topic": backend_options.get("reference_odom_topic", "/quad_0/lidar_slam/odom"),
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
        raise BackendError("The swarm planner-on-estimator roslaunch exited before the composition finished startup.")
    return process


def build_notes(config):
    notes = [
        "The ego_planner_swarm_fast_lio_marsim backend composes the dedicated ROS1 workspaces under /home/coco/sim_plane_ws/workspaces/ros1_marsim, /home/coco/sim_plane_ws/workspaces/ros1_fast_lio, and /home/coco/sim_plane_ws/workspaces/ros1_ego_swarm.",
        "The repo-local wrapper keeps EGO-Planner-Swarm in manual-goal mode and reuses the aligned FAST_LIO world-odom adapter instead of feeding raw /Odometry directly into the swarm planner.",
        "This composition stays cloud-only on purpose so the retired dual-input depth-plus-cloud false-obstacle chain does not reopen.",
    ]
    if config["launch_rviz"]:
        notes.append("A viewer was requested for this swarm planner-on-estimator probe.")
    else:
        notes.append("All RViz viewers were disabled for a lighter swarm planner-on-estimator probe.")
    if config["marsim_launch_rviz"]:
        notes.append("MARSIM's scene RViz path was enabled.")
    if config["fast_lio_launch_rviz"]:
        notes.append("FAST_LIO's estimator RViz path was enabled.")
    return notes
