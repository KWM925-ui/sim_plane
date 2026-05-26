import json
import os
import shlex
import signal
import subprocess
import time
from pathlib import Path

from sim_plane.adapters.base import AdapterError, AlgorithmAdapter
from sim_plane.adapters.human_follow_ros import (
    DEFAULT_ROS_SETUP,
    load_sourced_environment,
    normalize_follow_launch_args,
    prepare_ros_runtime_env,
    repo_root,
    resolve_workspace_dir,
)
from sim_plane.processes import start_log_threads, terminate_process


class HumanFollowROSStage2Adapter(AlgorithmAdapter):
    name = "human_follow_ros_stage2"
    requires_dedicated_udp_port = False

    def validate_environment(self, spec=None, context=None):
        config = build_runtime_config(spec or {}, context or {})
        issues = []
        if not config["ros_setup"].is_file():
            issues.append("ROS Noetic setup.bash was not found at /opt/ros/noetic/setup.bash.")
        if config["workspace_dir"] is None:
            issues.append(
                "Follower workspace not found. Build or point to /home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1."
            )
        else:
            if not config["workspace_setup"].is_file():
                issues.append(
                    "Follower workspace exists but devel/setup.bash is missing. Run catkin_make in {0} first.".format(
                        config["workspace_dir"]
                    )
                )
            if not config["mavros_overlay_setup"].is_file():
                issues.append(
                    "Follower workspace is missing env/source_local_mavros_overlay.bash for the local MAVROS overlay."
                )
            if not config["mavros_launch"].is_file():
                issues.append(
                    "Missing {0} in human_follow_bringup.".format(config["mavros_launch_name"])
                )
            if not config["quadrotor_msgs_dir"].is_dir():
                issues.append(
                    "Managed workspace is missing quadrotor_msgs. Run python3 scripts/sync_human_follow_stage1_workspace.py first."
                )
            if config["stage2_variant"] == "real_ego":
                missing_vendor_packages = [
                    package_dir.name
                    for package_dir in config["required_vendor_package_dirs"]
                    if not package_dir.is_dir()
                ]
                if missing_vendor_packages:
                    issues.append(
                        "Managed workspace is missing Stage2 real EGO vendor packages: {0}. "
                        "Run python3 scripts/sync_human_follow_stage1_workspace.py first.".format(
                            ", ".join(missing_vendor_packages)
                        )
                    )
        if not config["stage2_launch_path"].is_file():
            issues.append("Missing Stage2 managed launch: {0}".format(config["stage2_launch_path"]))
            if not config["probe_script"].is_file():
                issues.append(
                    "ROS Stage2 integrated probe is missing from scripts/ros_stage2_integrated_probe.py."
                )
        return issues

    def run(self, spec, sink, context):
        config = build_runtime_config(spec or {}, context or {})
        issues = self.validate_environment(spec, context)
        if issues:
            raise AdapterError("; ".join(issues))

        env = load_sourced_environment(
            [
                config["ros_setup"],
                config["workspace_setup"],
                config["mavros_overlay_setup"],
            ]
        )
        env = prepare_ros_runtime_env(env, sink.artifact_writer.artifact_dir)
        env["ROS_MASTER_URI"] = "http://127.0.0.1:{0}".format(config["ros_master_port"])
        env["ROS_HOSTNAME"] = "127.0.0.1"
        env["ROS_IP"] = "127.0.0.1"

        sink.emit_event(
            "info",
            "human follow stage2 ros adapter launch plan",
            {
                "adapter": self.name,
                "backend": context.get("backend"),
                "workspace_dir": str(config["workspace_dir"]),
                "ros_master_uri": env["ROS_MASTER_URI"],
                "mavros_launch": config["mavros_launch_name"],
                "stage2_launch_path": str(config["stage2_launch_path"]),
                "stage2_variant": config["stage2_variant"],
                "fcu_url": config["fcu_url"],
                "request_arm": config["request_arm"],
                "request_mode": config["request_mode"],
                "cleanup_mode": config["cleanup_mode"],
                "stage2_launch_args": config["stage2_launch_extra_args"],
            },
        )

        mavros_process = None
        stage2_process = None
        try:
            mavros_process = launch_roslaunch_package(
                workspace_dir=config["workspace_dir"],
                env=env,
                sink=sink,
                label="human_follow_stage2_mavros_sitl",
                package="human_follow_bringup",
                launch_file=config["mavros_launch_name"],
                extra_args=[
                    "fcu_url:={0}".format(config["fcu_url"]),
                    "gcs_url:={0}".format(config["gcs_url"]),
                    "tgt_system:={0}".format(config["tgt_system"]),
                    "tgt_component:={0}".format(config["tgt_component"]),
                ],
            )
            stage2_process = launch_roslaunch_path(
                workspace_dir=config["workspace_dir"],
                env=env,
                sink=sink,
                label="human_follow_stage2_integrated_chain",
                launch_path=config["stage2_launch_path"],
                extra_args=config["stage2_launch_extra_args"],
                wait_for_master=True,
            )
            report = run_probe(config, env, sink)
            if not report.get("success"):
                raise AdapterError(
                    "Stage2 integrated ROS probe failed at {0}".format(
                        report.get("failure_stage", "unknown")
                    )
                )
            keepalive_s = float(config["post_success_keepalive_s"])
            if keepalive_s > 0.0:
                sink.emit_event(
                    "info",
                    "human follow stage2 ros adapter keepalive",
                    {"adapter": self.name, "seconds": keepalive_s},
                )
                time.sleep(keepalive_s)
            return {
                "metrics": {
                    "algorithm_adapter_name": self.name,
                    "algorithm_adapter_completed_successfully": True,
                    "algorithm_adapter_connected": bool(report.get("connected")),
                    "algorithm_adapter_arm_requested": bool(report.get("arm_requested")),
                    "algorithm_adapter_arm_command_sent": bool(report.get("arm_command_sent")),
                    "algorithm_adapter_armed": bool(report.get("armed")),
                    "algorithm_adapter_estimator_valid": bool(report.get("estimator_valid")),
                    "algorithm_adapter_offboard_requested": False,
                    "algorithm_adapter_offboard_mode_reached": bool(report.get("offboard_mode_reached")),
                    "algorithm_adapter_cleanup_mode": report.get("cleanup_mode", ""),
                    "algorithm_adapter_cleanup_mode_requested": bool(report.get("cleanup_mode_requested")),
                    "algorithm_adapter_cleanup_mode_reached": bool(report.get("cleanup_mode_reached")),
                    "algorithm_adapter_stage2_goal_count": int(report.get("stage2_goal_count", 0)),
                    "algorithm_adapter_stage2_ego_goal_count": int(report.get("ego_goal_count", 0)),
                    "algorithm_adapter_stage2_ego_cmd_count": int(report.get("ego_cmd_count", 0)),
                    "algorithm_adapter_stage2_bridge_setpoint_count": int(
                        report.get("bridge_setpoint_count", 0)
                    ),
                    "algorithm_adapter_stage2_mavros_setpoint_count": int(
                        report.get("mavros_setpoint_count", 0)
                    ),
                    "algorithm_adapter_stage2_nonzero_bridge_setpoint_count": int(
                        report.get("nonzero_bridge_setpoint_count", 0)
                    ),
                    "algorithm_adapter_stage2_nonzero_mavros_setpoint_count": int(
                        report.get("nonzero_mavros_setpoint_count", 0)
                    ),
                    "algorithm_adapter_stage2_gate_owned_offboard_inferred": bool(
                        report.get("gate_owned_offboard_inferred")
                    ),
                    "algorithm_adapter_stage2_follow_goal_count": int(
                        report.get("follow_goal_count", 0)
                    ),
                    "algorithm_adapter_stage2_follow_goal_observed": bool(
                        report.get("follow_goal_observed")
                    ),
                    "algorithm_adapter_stage2_search_goal_observed": bool(
                        report.get("search_goal_observed")
                    ),
                    "algorithm_adapter_stage2_search_goal_count": int(
                        report.get("search_goal_count", 0)
                    ),
                    "algorithm_adapter_stage2_hold_goal_count": int(
                        report.get("hold_goal_count", 0)
                    ),
                    "algorithm_adapter_stage2_lost_hold_observed": bool(
                        report.get("lost_hold_observed")
                    ),
                    "algorithm_adapter_stage2_real_ego_path_observed": bool(
                        report.get("real_ego_path_observed")
                    ),
                    "algorithm_adapter_stage2_waypoint_count": int(report.get("waypoint_count", 0)),
                    "algorithm_adapter_stage2_distinct_goal_count": int(
                        report.get("distinct_goal_count", 0)
                    ),
                    "algorithm_adapter_stage2_distinct_ego_cmd_count": int(
                        report.get("distinct_ego_cmd_count", 0)
                    ),
                    "algorithm_adapter_stage2_launch_name": config["stage2_launch_path"].name,
                    "algorithm_adapter_stage2_variant": config["stage2_variant"],
                    "algorithm_adapter_ros_master_uri": env["ROS_MASTER_URI"],
                },
                "notes": build_adapter_notes(config),
            }
        finally:
            terminate_process(
                stage2_process,
                sink,
                "human_follow_stage2_integrated_chain",
                stop_signal=signal.SIGINT,
                wait_timeout_s=6.0,
            )
            terminate_process(
                mavros_process,
                sink,
                "human_follow_stage2_mavros_sitl",
                stop_signal=signal.SIGINT,
                wait_timeout_s=6.0,
            )


def build_runtime_config(spec, context):
    workspace_dir = resolve_workspace_dir(spec.get("ros_workspace_dir"))
    workspace_setup = workspace_dir / "devel" / "setup.bash" if workspace_dir is not None else Path("")
    mavros_overlay_setup = (
        workspace_dir / "env" / "source_local_mavros_overlay.bash"
        if workspace_dir is not None
        else Path("")
    )
    bringup_launch_dir = workspace_dir / "src" / "human_follow_bringup" / "launch" if workspace_dir is not None else Path("")
    stage2_launch_extra_args, stage2_launch_named_args = normalize_follow_launch_args(
        spec.get("stage2_launch_args")
    )
    if context.get("launch_rviz"):
        stage2_launch_named_args["rviz"] = "true"
        stage2_launch_extra_args = [
            arg for arg in stage2_launch_extra_args if not str(arg).strip().startswith("rviz:=")
        ]
        stage2_launch_extra_args.append("rviz:=true")
    mavros_launch_name = spec.get("mavros_launch", "stage1_px4_mavros_sitl.launch")
    stage2_launch_path = resolve_stage2_launch_path(spec.get("stage2_launch_path"))
    stage2_variant = classify_stage2_variant(stage2_launch_path)
    return {
        "ros_setup": Path(spec.get("ros_setup", DEFAULT_ROS_SETUP)).expanduser(),
        "workspace_dir": workspace_dir,
        "workspace_setup": workspace_setup,
        "mavros_overlay_setup": mavros_overlay_setup,
        "mavros_launch": bringup_launch_dir / mavros_launch_name,
        "mavros_launch_name": mavros_launch_name,
        "quadrotor_msgs_dir": workspace_dir / "src" / "quadrotor_msgs" if workspace_dir is not None else Path(""),
        "stage2_launch_path": stage2_launch_path,
        "stage2_variant": stage2_variant,
        "stage2_launch_extra_args": stage2_launch_extra_args,
        "stage2_launch_named_args": stage2_launch_named_args,
        "probe_script": repo_root() / "scripts" / "ros_stage2_integrated_probe.py",
        "required_vendor_package_dirs": [
            workspace_dir / "src" / "ego_planner_vendor" / "plan_env"
            if workspace_dir is not None
            else Path(""),
            workspace_dir / "src" / "ego_planner_vendor" / "path_searching"
            if workspace_dir is not None
            else Path(""),
            workspace_dir / "src" / "ego_planner_vendor" / "bspline_opt"
            if workspace_dir is not None
            else Path(""),
            workspace_dir / "src" / "ego_planner_vendor" / "traj_utils"
            if workspace_dir is not None
            else Path(""),
            workspace_dir / "src" / "ego_planner_vendor" / "ego_planner"
            if workspace_dir is not None
            else Path(""),
        ],
        "ros_master_port": int(spec.get("ros_master_port", 11371)),
        "fcu_url": spec.get("fcu_url", "udp://:14540@127.0.0.1:14557"),
        "gcs_url": spec.get("gcs_url", ""),
        "tgt_system": int(spec.get("tgt_system", 1)),
        "tgt_component": int(spec.get("tgt_component", 1)),
        "request_mode": str(spec.get("request_mode", "OFFBOARD")),
        "request_arm": bool(spec.get("request_arm", True)),
        "cleanup_mode": str(spec.get("cleanup_mode", "AUTO.LOITER")),
        "master_timeout_s": float(spec.get("master_timeout_s", 20.0)),
        "wait_connected_timeout_s": float(spec.get("wait_connected_timeout_s", 20.0)),
        "wait_estimator_timeout_s": float(spec.get("wait_estimator_timeout_s", 20.0)),
        "wait_goal_timeout_s": float(spec.get("wait_goal_timeout_s", 20.0)),
        "wait_command_timeout_s": float(spec.get("wait_command_timeout_s", 20.0)),
        "mode_timeout_s": float(spec.get("mode_timeout_s", 15.0)),
        "arm_timeout_s": float(spec.get("arm_timeout_s", 10.0)),
        "cleanup_mode_timeout_s": float(spec.get("cleanup_mode_timeout_s", 5.0)),
        "require_estimator_valid": bool(spec.get("require_estimator_valid", True)),
        "min_goal_count": int(spec.get("min_goal_count", 2)),
        "min_command_count": int(spec.get("min_command_count", 2)),
        "min_nonzero_setpoint_count": int(spec.get("min_nonzero_setpoint_count", 10)),
        "require_follow_goal_observed": bool(spec.get("require_follow_goal_observed", False)),
        "require_search_goal_observed": bool(spec.get("require_search_goal_observed", False)),
        "require_lost_hold_observed": bool(spec.get("require_lost_hold_observed", False)),
        "semantic_timeout_s": float(spec.get("semantic_timeout_s", 20.0)),
        "post_success_keepalive_s": float(spec.get("post_success_keepalive_s", 0.0)),
    }


def resolve_stage2_launch_path(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    candidates.append(repo_root() / "sim_plane" / "ros" / "human_follow_stage2_real_ego_managed.launch")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return candidates[0]


def classify_stage2_variant(stage2_launch_path):
    launch_name = stage2_launch_path.name
    if "real_ego" in launch_name:
        return "real_ego"
    return "custom"


def build_adapter_notes(config):
    if config["stage2_variant"] == "real_ego":
        return [
            "A repo-local ROS adapter launched the managed Stage2 real-EGO chain on top of real PX4 SIH + MAVROS from {0}.".format(
                config["workspace_dir"]
            ),
            "This proof consumes the project-side stage2_real_ego.launch contract, including rolling follow goals, search goals after target loss, lost/hold behavior after search timeout, real EGO waypoint/path generation, PositionCommand bridge, and OFFBOARD gate.",
            "This is sim-plane managed evidence for the project-side real Stage2 chain, not a sim-plane independent ego_planner baseline.",
        ]
    return [
        "A repo-local ROS adapter launched an explicit non-standard Stage2 launch on top of real PX4 SIH + MAVROS from {0}.".format(
            config["workspace_dir"]
        ),
        "The current platform-mainline Stage2 proof is the real-EGO launch; custom Stage2 launch paths are outside the frozen acceptance surface unless a separate matrix row is added.",
    ]


def launch_roslaunch_package(workspace_dir, env, sink, label, package, launch_file, extra_args=None):
    return launch_roslaunch_command(
        workspace_dir=workspace_dir,
        env=env,
        sink=sink,
        label=label,
        command=["roslaunch", package, launch_file] + list(extra_args or []),
    )


def launch_roslaunch_path(workspace_dir, env, sink, label, launch_path, extra_args=None, wait_for_master=False):
    command = ["roslaunch"]
    if wait_for_master:
        command.append("--wait")
    command.append(str(launch_path))
    command.extend(extra_args or [])
    return launch_roslaunch_command(
        workspace_dir=workspace_dir,
        env=env,
        sink=sink,
        label=label,
        command=command,
    )


def launch_roslaunch_command(workspace_dir, env, sink, label, command):
    sink.emit_event(
        "info",
        "launching roslaunch",
        {"label": label, "command": " ".join(shlex.quote(part) for part in command), "cwd": str(workspace_dir)},
    )
    process = subprocess.Popen(
        command,
        cwd=str(workspace_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_log_threads(process, sink, label)
    time.sleep(1.5)
    if process.poll() is not None:
        raise AdapterError("{0} exited before startup completed.".format(label))
    return process


def run_probe(config, env, sink):
    command = [
        "python3",
        str(config["probe_script"]),
        "--master-timeout-s",
        str(config["master_timeout_s"]),
        "--wait-connected-timeout-s",
        str(config["wait_connected_timeout_s"]),
        "--wait-estimator-timeout-s",
        str(config["wait_estimator_timeout_s"]),
        "--wait-goal-timeout-s",
        str(config["wait_goal_timeout_s"]),
        "--wait-command-timeout-s",
        str(config["wait_command_timeout_s"]),
        "--arm-timeout-s",
        str(config["arm_timeout_s"]),
        "--mode-timeout-s",
        str(config["mode_timeout_s"]),
        "--cleanup-mode-timeout-s",
        str(config["cleanup_mode_timeout_s"]),
        "--require-estimator-valid",
        str(config["require_estimator_valid"]).lower(),
        "--request-arm",
        str(config["request_arm"]).lower(),
        "--request-mode",
        config["request_mode"],
        "--cleanup-mode",
        config["cleanup_mode"],
        "--min-goal-count",
        str(config["min_goal_count"]),
        "--min-command-count",
        str(config["min_command_count"]),
        "--min-nonzero-setpoint-count",
        str(config["min_nonzero_setpoint_count"]),
        "--require-follow-goal-observed",
        str(config["require_follow_goal_observed"]).lower(),
        "--require-search-goal-observed",
        str(config["require_search_goal_observed"]).lower(),
        "--require-lost-hold-observed",
        str(config["require_lost_hold_observed"]).lower(),
        "--semantic-timeout-s",
        str(config["semantic_timeout_s"]),
    ]
    sink.emit_event(
        "info",
        "launching stage2 integrated probe",
        {"command": " ".join(shlex.quote(part) for part in command)},
    )
    completed = subprocess.run(
        command,
        cwd=str(config["workspace_dir"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for line in completed.stdout.splitlines():
        sink.emit_backend_log("stdout", "[stage2_integrated_probe] {0}".format(line))
    for line in completed.stderr.splitlines():
        sink.emit_backend_log("stderr", "[stage2_integrated_probe] {0}".format(line))
    if completed.returncode not in (0, 1):
        raise AdapterError(
            "Stage2 integrated probe exited unexpectedly with code {0}".format(
                completed.returncode
            )
        )

    report = None
    for raw_line in reversed(completed.stdout.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            report = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if report is None:
        raise AdapterError("Stage2 integrated probe did not emit a JSON report.")
    sink.emit_event(
        "info" if report.get("success") else "warning",
        "stage2 integrated probe summary",
        report,
    )
    return report
