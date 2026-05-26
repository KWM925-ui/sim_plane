import json
import os
import shlex
import signal
import socket
import subprocess
import time
from pathlib import Path

from sim_plane.adapters.base import AdapterError, AlgorithmAdapter
from sim_plane.processes import start_log_threads, terminate_process


DEFAULT_ROS_SETUP = Path("/opt/ros/noetic/setup.bash")
DEFAULT_FOLLOWER_WORKSPACE_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1"),
    Path("/home/coco/follwer_ws"),
]


def port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            handle.bind(("127.0.0.1", int(port)))
        except OSError:
            return False
    return True


def choose_ros_master_port(requested_port, search_span):
    requested_port = max(int(requested_port), 1024)
    if port_available(requested_port):
        return requested_port

    for offset in range(1, max(int(search_span), 0) + 1):
        candidate = requested_port + offset
        if port_available(candidate):
            return candidate

    raise AdapterError(
        "No free ROS master port found near {0} within +{1} ports.".format(
            requested_port,
            int(search_span),
        )
    )


def roslaunch_value_text(value):
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def normalize_follow_launch_args(raw_args):
    if raw_args is None:
        return [], {}

    if isinstance(raw_args, dict):
        named_args = {}
        extra_args = []
        for key, value in raw_args.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            value_text = roslaunch_value_text(value)
            named_args[key_text] = value_text
            extra_args.append("{0}:={1}".format(key_text, value_text))
        return extra_args, named_args

    if isinstance(raw_args, (list, tuple)):
        extra_args = []
        named_args = {}
        for item in raw_args:
            item_text = str(item).strip()
            if not item_text:
                continue
            extra_args.append(item_text)
            if ":=" in item_text:
                key_text, value_text = item_text.split(":=", 1)
                key_text = key_text.strip()
                if key_text:
                    named_args[key_text] = value_text.strip()
        return extra_args, named_args

    return [str(raw_args).strip()], {}


class HumanFollowROSStage1Adapter(AlgorithmAdapter):
    name = "human_follow_ros_stage1"
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
            if not config["follow_launch"].is_file():
                issues.append(
                    "Missing {0} in human_follow_bringup.".format(config["follow_launch_name"])
                )
        if not config["probe_script"].is_file():
            issues.append("ROS Stage1 follow probe is missing from scripts/ros_stage1_follow_probe.py.")
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
            "human follow ros adapter launch plan",
            {
                "adapter": self.name,
                "backend": context.get("backend"),
                "workspace_dir": str(config["workspace_dir"]),
                "ros_master_uri": env["ROS_MASTER_URI"],
                "ros_master_port_requested": config["ros_master_port_requested"],
                "ros_master_port_selected": config["ros_master_port"],
                "mavros_launch": config["mavros_launch_name"],
                "follow_launch": config["follow_launch_name"],
                "fcu_url": config["fcu_url"],
                "request_mode": config["request_mode"],
                "request_arm": config["request_arm"],
                "publish_external_odom": config["publish_external_odom"],
                "follow_launch_args": config["follow_launch_extra_args"],
            },
        )

        mavros_process = None
        follow_process = None
        probe_process = None
        try:
            mavros_process = launch_roslaunch(
                workspace_dir=config["workspace_dir"],
                env=env,
                sink=sink,
                label="human_follow_mavros_sitl",
                package="human_follow_bringup",
                launch_file=config["mavros_launch_name"],
                extra_args=[
                    "fcu_url:={0}".format(config["fcu_url"]),
                    "gcs_url:={0}".format(config["gcs_url"]),
                    "tgt_system:={0}".format(config["tgt_system"]),
                    "tgt_component:={0}".format(config["tgt_component"]),
                ],
                startup_grace_s=config["roslaunch_startup_grace_s"],
            )
            probe_process = start_probe_process(config, env, sink)
            follow_process = launch_roslaunch(
                workspace_dir=config["workspace_dir"],
                env=env,
                sink=sink,
                label="human_follow_follow_launch",
                package="human_follow_bringup",
                launch_file=config["follow_launch_name"],
                extra_args=[
                    "bridge_output_topic:={0}".format(config["setpoint_topic"]),
                    "publish_external_odom:={0}".format(str(config["publish_external_odom"]).lower()),
                    "external_odom_topic:={0}".format(config["external_odom_topic"]),
                ]
                + config["follow_launch_extra_args"],
                wait_for_master=True,
                startup_grace_s=config["roslaunch_startup_grace_s"],
            )
            report = wait_for_probe_report(
                probe_process,
                sink,
                watched_processes=[
                    ("human_follow_mavros_sitl", mavros_process),
                    ("human_follow_follow_launch", follow_process),
                ],
            )
            probe_process = None
            if not report.get("success"):
                raise AdapterError("Stage1 ROS follow probe failed at {0}".format(report.get("failure_stage", "unknown")))
            if config["expect_follow_launch_exit"]:
                follow_exit_code = wait_for_process_exit(
                    follow_process,
                    sink,
                    "human_follow_synthetic_follow",
                    timeout_s=config["follow_launch_exit_timeout_s"],
                )
                if follow_exit_code != 0:
                    raise AdapterError(
                        "Follower launch {0} exited with code {1}".format(
                            config["follow_launch_name"], follow_exit_code
                        )
                    )
            keepalive_s = float(config["post_success_keepalive_s"])
            if keepalive_s > 0.0:
                sink.emit_event(
                    "info",
                    "human follow ros adapter keepalive",
                    {"adapter": self.name, "seconds": keepalive_s},
                )
                time.sleep(keepalive_s)
            notes = build_adapter_notes(config)
            return {
                "metrics": {
                    "algorithm_adapter_name": self.name,
                    "algorithm_adapter_completed_successfully": True,
                    "algorithm_adapter_connected": bool(report.get("connected")),
                    "algorithm_adapter_offboard_requested": bool(report.get("offboard_requested")),
                    "algorithm_adapter_offboard_mode_reached": bool(report.get("offboard_mode_reached")),
                    "algorithm_adapter_cleanup_mode": report.get("cleanup_mode", ""),
                    "algorithm_adapter_cleanup_mode_requested": bool(report.get("cleanup_mode_requested")),
                    "algorithm_adapter_cleanup_mode_reached": bool(report.get("cleanup_mode_reached")),
                    "algorithm_adapter_arm_requested": bool(report.get("arm_requested")),
                    "algorithm_adapter_arm_command_sent": bool(report.get("arm_command_sent")),
                    "algorithm_adapter_armed": bool(report.get("armed")),
                    "algorithm_adapter_estimator_valid": bool(report.get("estimator_valid")),
                    "algorithm_adapter_follow_valid_command_seen": bool(report.get("follow_valid_command_seen")),
                    "algorithm_adapter_follow_state_name": report.get("follow_state_name", ""),
                    "algorithm_adapter_follow_non_hold_count": int(report.get("follow_non_hold_count", 0)),
                    "algorithm_adapter_setpoint_count": int(report.get("setpoint_count", 0)),
                    "algorithm_adapter_nonzero_setpoint_count": int(report.get("nonzero_setpoint_count", 0)),
                    "algorithm_adapter_follow_launch_expect_exit": bool(config["expect_follow_launch_exit"]),
                    "algorithm_adapter_follow_launch_name": config["follow_launch_name"],
                    "algorithm_adapter_motion_mode": config["follow_launch_named_args"].get("motion_mode", ""),
                    "algorithm_adapter_validation_case": config["follow_launch_named_args"].get("validation_case", ""),
                    "algorithm_adapter_ros_master_uri": env["ROS_MASTER_URI"],
                },
                "notes": notes,
            }
        finally:
            terminate_process(
                probe_process,
                sink,
                "stage1_follow_probe",
                stop_signal=signal.SIGINT,
                wait_timeout_s=2.0,
            )
            terminate_process(follow_process, sink, "human_follow_follow_launch", stop_signal=signal.SIGINT, wait_timeout_s=6.0)
            terminate_process(mavros_process, sink, "human_follow_mavros_sitl", stop_signal=signal.SIGINT, wait_timeout_s=6.0)


def repo_root():
    return Path(__file__).resolve().parents[2]


def resolve_workspace_dir(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.environ.get("SIM_PLANE_FOLLOWER_WS")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(DEFAULT_FOLLOWER_WORKSPACE_CANDIDATES)

    for candidate in candidates:
        if (candidate / "src").is_dir():
            return candidate.resolve()
    return None


def build_runtime_config(spec, context):
    workspace_dir = resolve_workspace_dir(spec.get("ros_workspace_dir"))
    workspace_setup = workspace_dir / "devel" / "setup.bash" if workspace_dir is not None else Path("")
    mavros_overlay_setup = workspace_dir / "env" / "source_local_mavros_overlay.bash" if workspace_dir is not None else Path("")
    bringup_launch_dir = workspace_dir / "src" / "human_follow_bringup" / "launch" if workspace_dir is not None else Path("")
    follow_launch_extra_args, follow_launch_named_args = normalize_follow_launch_args(spec.get("follow_launch_args"))
    mavros_launch_name = spec.get("mavros_launch", "stage1_px4_mavros_sitl.launch")
    follow_launch_name = spec.get("follow_launch", "stage1_sitl_synthetic_follow.launch")
    ros_master_port_requested = int(spec.get("ros_master_port", 11351))
    ros_master_port = choose_ros_master_port(
        ros_master_port_requested,
        int(spec.get("ros_master_port_search_span", 50)),
    )
    return {
        "ros_setup": Path(spec.get("ros_setup", DEFAULT_ROS_SETUP)).expanduser(),
        "workspace_dir": workspace_dir,
        "workspace_setup": workspace_setup,
        "mavros_overlay_setup": mavros_overlay_setup,
        "mavros_launch": bringup_launch_dir / mavros_launch_name,
        "mavros_launch_name": mavros_launch_name,
        "follow_launch": bringup_launch_dir / follow_launch_name,
        "follow_launch_name": follow_launch_name,
        "follow_launch_extra_args": follow_launch_extra_args,
        "follow_launch_named_args": follow_launch_named_args,
        "probe_script": repo_root() / "scripts" / "ros_stage1_follow_probe.py",
        "ros_master_port_requested": ros_master_port_requested,
        "ros_master_port": ros_master_port,
        "fcu_url": spec.get("fcu_url", "udp://:14540@127.0.0.1:14557"),
        "gcs_url": spec.get("gcs_url", ""),
        "tgt_system": int(spec.get("tgt_system", 1)),
        "tgt_component": int(spec.get("tgt_component", 1)),
        "setpoint_topic": spec.get("setpoint_topic", "/mavros/setpoint_raw/local"),
        "external_odom_topic": spec.get("external_odom_topic", "/mavros/odometry/out"),
        "publish_external_odom": bool(spec.get("publish_external_odom", True)),
        "request_mode": str(spec.get("request_mode", "OFFBOARD")),
        "request_arm": bool(spec.get("request_arm", False)),
        "cleanup_mode": str(spec.get("cleanup_mode", "AUTO.LOITER")),
        "master_timeout_s": float(spec.get("master_timeout_s", 20.0)),
        "wait_connected_timeout_s": float(spec.get("wait_connected_timeout_s", 20.0)),
        "wait_command_timeout_s": float(spec.get("wait_command_timeout_s", 20.0)),
        "ready_timeout_s": float(spec.get("ready_timeout_s", 20.0)),
        "mode_timeout_s": float(spec.get("mode_timeout_s", 10.0)),
        "arm_timeout_s": float(spec.get("arm_timeout_s", 10.0)),
        "cleanup_mode_timeout_s": float(spec.get("cleanup_mode_timeout_s", 5.0)),
        "post_success_keepalive_s": float(spec.get("post_success_keepalive_s", 10.0)),
        "setpoint_warmup_count": int(spec.get("setpoint_warmup_count", 20)),
        "require_estimator_valid": bool(spec.get("require_estimator_valid", True)),
        "expect_follow_launch_exit": bool(spec.get("expect_follow_launch_exit", False)),
        "follow_launch_exit_timeout_s": float(spec.get("follow_launch_exit_timeout_s", 10.0)),
        "roslaunch_startup_grace_s": float(spec.get("roslaunch_startup_grace_s", 0.5)),
    }


def build_adapter_notes(config):
    workspace_dir = str(config["workspace_dir"])
    follow_launch_name = config["follow_launch_name"]
    notes = []
    if follow_launch_name == "stage1_sitl_synthetic_follow.launch":
        notes.append(
            "A repo-local ROS adapter launched the Stage1 synthetic follower chain from {0} and switched PX4 SIH into OFFBOARD through MAVROS.".format(
                workspace_dir
            )
        )
    else:
        notes.append(
            "A repo-local ROS adapter launched {0} from {1} and switched PX4 SIH into OFFBOARD through MAVROS.".format(
                follow_launch_name,
                workspace_dir,
            )
        )
    notes.append(
        "This path keeps sim_plane on the light PX4 SIH backend while treating ROS as an optional adapter boundary rather than a new core backend."
    )
    return notes


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


def launch_roslaunch(
    workspace_dir,
    env,
    sink,
    label,
    package,
    launch_file,
    extra_args=None,
    wait_for_master=False,
    startup_grace_s=0.5,
):
    command = ["roslaunch"]
    if wait_for_master:
        command.append("--wait")
    command.extend([package, launch_file])
    command.extend(extra_args or [])
    sink.emit_event(
        "info",
        "launching roslaunch",
        {"label": label, "command": " ".join(shlex.quote(part) for part in command), "cwd": str(workspace_dir)},
    )
    process = subprocess.Popen(
        command,
        cwd=str(workspace_dir),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_log_threads(process, sink, label)
    time.sleep(max(float(startup_grace_s), 0.1))
    if process.poll() is not None:
        raise AdapterError("{0} exited before startup completed.".format(label))
    return process


def wait_for_process_exit(process, sink, label, timeout_s):
    deadline = time.time() + max(float(timeout_s), 0.1)
    while time.time() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            sink.emit_event(
                "info" if exit_code == 0 else "warning",
                "roslaunch exited",
                {"label": label, "exit_code": int(exit_code)},
            )
            return int(exit_code)
        time.sleep(0.2)
    raise AdapterError("{0} did not exit within {1:.1f}s".format(label, float(timeout_s)))


def build_probe_command(config):
    return [
        "python3",
        str(config["probe_script"]),
        "--master-timeout-s",
        str(config["master_timeout_s"]),
        "--wait-connected-timeout-s",
        str(config["wait_connected_timeout_s"]),
        "--wait-command-timeout-s",
        str(config["wait_command_timeout_s"]),
        "--ready-timeout-s",
        str(config["ready_timeout_s"]),
        "--mode-timeout-s",
        str(config["mode_timeout_s"]),
        "--arm-timeout-s",
        str(config["arm_timeout_s"]),
        "--setpoint-warmup-count",
        str(config["setpoint_warmup_count"]),
        "--require-estimator-valid",
        str(config["require_estimator_valid"]).lower(),
        "--request-mode",
        config["request_mode"],
        "--request-arm",
        str(config["request_arm"]).lower(),
        "--cleanup-mode",
        config["cleanup_mode"],
        "--cleanup-mode-timeout-s",
        str(config["cleanup_mode_timeout_s"]),
        "--setpoint-topic",
        config["setpoint_topic"],
    ]


def start_probe_process(config, env, sink):
    command = build_probe_command(config)
    sink.emit_event(
        "info",
        "launching stage1 follow probe",
        {"command": " ".join(shlex.quote(part) for part in command)},
    )
    return subprocess.Popen(
        command,
        cwd=str(config["workspace_dir"]),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )


def collect_probe_report(process, sink):
    stdout_text, stderr_text = process.communicate()
    for line in stdout_text.splitlines():
        sink.emit_backend_log("stdout", "[stage1_follow_probe] {0}".format(line))
    for line in stderr_text.splitlines():
        sink.emit_backend_log("stderr", "[stage1_follow_probe] {0}".format(line))
    if process.returncode not in (0, 1):
        raise AdapterError("Stage1 follow probe exited unexpectedly with code {0}".format(process.returncode))

    report = None
    for raw_line in reversed(stdout_text.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            report = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if report is None:
        raise AdapterError("Stage1 follow probe did not emit a JSON report.")
    sink.emit_event(
        "info" if report.get("success") else "warning",
        "stage1 follow probe summary",
        report,
    )
    return report


def wait_for_probe_report(process, sink, watched_processes=None, poll_interval_s=0.1):
    watched_processes = list(watched_processes or [])
    while True:
        if process.poll() is not None:
            return collect_probe_report(process, sink)
        for label, watched_process in watched_processes:
            if watched_process is None:
                continue
            exit_code = watched_process.poll()
            if exit_code is None:
                continue
            terminate_process(
                process,
                sink,
                "stage1_follow_probe",
                stop_signal=signal.SIGINT,
                wait_timeout_s=2.0,
            )
            raise AdapterError(
                "{0} exited before the Stage1 follow probe completed (exit_code={1}).".format(
                    label,
                    int(exit_code),
                )
            )
        time.sleep(max(float(poll_interval_s), 0.05))


def run_probe(config, env, sink):
    probe_process = start_probe_process(config, env, sink)
    return wait_for_probe_report(probe_process, sink)
