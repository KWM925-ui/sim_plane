import json
import os
import shlex
import signal
import subprocess
from pathlib import Path

from sim_plane.adapters.base import AdapterError, AlgorithmAdapter
from sim_plane.processes import start_log_threads, terminate_process


class ExternalCommandAdapter(AlgorithmAdapter):
    name = "external_command"
    requires_dedicated_udp_port = False

    def validate_environment(self, spec=None, context=None):
        config = build_runtime_config(spec or {}, context or {}, artifact_dir=None)
        issues = []
        if not config["command"]:
            issues.append("The external_command adapter requires a non-empty command field.")
        if config["workdir"] is not None and not config["workdir"].is_dir():
            issues.append("The external_command workdir does not exist: {0}".format(config["workdir"]))
        if not config["shell"]:
            executable = config["command"][0] if isinstance(config["command"], list) and config["command"] else None
            if executable and shutil_which(executable, config["env"]) is None:
                issues.append("The external_command executable is not on PATH: {0}".format(executable))
        return issues

    def run(self, spec, sink, context):
        config = build_runtime_config(
            spec or {},
            context or {},
            artifact_dir=sink.artifact_writer.artifact_dir,
        )
        issues = self.validate_environment(spec, context)
        if issues:
            raise AdapterError("; ".join(issues))

        command_for_log = (
            config["command"]
            if isinstance(config["command"], str)
            else " ".join(shlex.quote(part) for part in config["command"])
        )
        sink.emit_event(
            "info",
            "external algorithm adapter launch plan",
            {
                "adapter": self.name,
                "command": command_for_log,
                "workdir": str(config["workdir"]) if config["workdir"] is not None else None,
                "max_runtime_s": config["max_runtime_s"],
                "result_json": str(config["result_json"]),
                "context_env_keys": sorted(config["context_env"].keys()),
            },
        )

        process = subprocess.Popen(
            config["command"],
            cwd=str(config["workdir"]) if config["workdir"] is not None else None,
            env=config["env"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            shell=config["shell"],
            preexec_fn=os.setsid if os.name != "nt" else None,
        )
        start_log_threads(process, sink, "external_algorithm")

        timed_out = False
        try:
            exit_code = process.wait(timeout=config["max_runtime_s"])
        except subprocess.TimeoutExpired:
            timed_out = True
            sink.emit_event(
                "warning",
                "external algorithm runtime exceeded limit",
                {"adapter": self.name, "max_runtime_s": config["max_runtime_s"], "pid": process.pid},
            )
            terminate_process(
                process,
                sink,
                "external_algorithm",
                stop_signal=signal.SIGINT,
                wait_timeout_s=4.0,
            )
            exit_code = process.poll()

        payload = load_result_payload(config["result_json"])
        success = bool(payload.get("success", not timed_out and exit_code in config["success_exit_codes"]))
        if timed_out and not config["allow_timeout_as_success"]:
            success = False
        if exit_code not in config["success_exit_codes"] and not payload:
            success = False

        metrics = {
            "algorithm_adapter_name": self.name,
            "algorithm_adapter_completed_successfully": success,
            "algorithm_adapter_exit_code": exit_code if exit_code is not None else -1,
            "algorithm_adapter_timed_out": timed_out,
            "algorithm_adapter_command": command_for_log,
        }
        metrics.update(payload.get("metrics", {}))
        notes = [
            "A repo-local external command adapter launched the user algorithm as a normal host process instead of forcing it to live inside an upstream simulator tree.",
            "The adapter exported stable SIM_PLANE_* environment variables so the algorithm can discover PX4 endpoints, artifact paths, and scenario metadata without hard-coded machine paths.",
        ]
        notes.extend(payload.get("notes", []))

        if not success:
            raise AdapterError(
                "external command adapter failed: exit_code={0}, timed_out={1}, result_json={2}".format(
                    exit_code,
                    timed_out,
                    str(config["result_json"]),
                )
            )

        return {
            "metrics": metrics,
            "notes": notes,
        }


def build_runtime_config(spec, context, artifact_dir):
    command = spec.get("command")
    shell = bool(spec.get("shell", False))
    workdir = resolve_path(spec.get("workdir"))
    result_json = None
    context_env = build_context_env(context or {}, artifact_dir)
    if artifact_dir is not None:
        adapter_dir = Path(artifact_dir) / "algorithm_adapter"
        adapter_dir.mkdir(parents=True, exist_ok=True)
        result_json = adapter_dir / "result.json"
        context_env["SIM_PLANE_ADAPTER_RESULT_JSON"] = str(result_json)
    elif spec.get("result_json"):
        result_json = resolve_path(spec.get("result_json"), workdir)

    env = os.environ.copy()
    env.update({key: str(value) for key, value in context_env.items() if value is not None})
    for key, value in (spec.get("env") or {}).items():
        env[str(key)] = str(value)

    if command is None:
        normalized_command = []
    elif shell:
        normalized_command = str(command)
    elif isinstance(command, str):
        normalized_command = shlex.split(command)
    elif isinstance(command, list):
        normalized_command = [str(part) for part in command]
    else:
        normalized_command = []

    max_runtime_s = float(
        spec.get(
            "max_runtime_s",
            (context or {}).get("expected_duration_s", 20.0) + 2.0,
        )
    )
    success_exit_codes = [int(code) for code in spec.get("success_exit_codes", [0])]

    return {
        "command": normalized_command,
        "shell": shell,
        "workdir": workdir,
        "env": env,
        "context_env": context_env,
        "result_json": result_json,
        "max_runtime_s": max_runtime_s,
        "success_exit_codes": success_exit_codes,
        "allow_timeout_as_success": bool(spec.get("allow_timeout_as_success", False)),
    }


def resolve_path(path, base_dir=None):
    if path is None or str(path).strip() == "":
        return None
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    if base_dir is not None:
        return (Path(base_dir) / candidate).resolve()
    return candidate.resolve()


def build_context_env(context, artifact_dir):
    env = {
        "SIM_PLANE_BACKEND": context.get("backend"),
        "SIM_PLANE_VEHICLE": context.get("vehicle"),
        "SIM_PLANE_SCENARIO_NAME": context.get("scenario_name"),
        "SIM_PLANE_TELEMETRY_ENDPOINT": context.get("telemetry_endpoint"),
        "SIM_PLANE_PREFERRED_TELEMETRY_PORT": context.get("preferred_telemetry_port"),
        "SIM_PLANE_SYSTEM_ADDRESS": context.get("system_address"),
        "SIM_PLANE_TARGET_ALTITUDE_M": context.get("target_altitude_m"),
        "SIM_PLANE_EXPECTED_DURATION_S": context.get("expected_duration_s"),
        "SIM_PLANE_ARTIFACT_DIR": str(Path(artifact_dir).resolve()) if artifact_dir is not None else None,
        "SIM_PLANE_ROS_MASTER_URI": context.get("ros_master_uri"),
        "SIM_PLANE_ROS_HOSTNAME": context.get("ros_hostname"),
        "SIM_PLANE_ROS_IP": context.get("ros_ip"),
        "SIM_PLANE_ODOM_TOPIC": context.get("odom_topic"),
        "SIM_PLANE_POINTCLOUD_TOPIC": context.get("pointcloud_topic"),
        "SIM_PLANE_COMMAND_TOPIC": context.get("command_topic"),
        "SIM_PLANE_GOAL_TOPIC": context.get("goal_topic"),
        "SIM_PLANE_MAP_TOPIC": context.get("map_topic"),
        "SIM_PLANE_ROS_SETUP": context.get("ros_setup"),
        "SIM_PLANE_LAUNCH_RVIZ": context.get("launch_rviz"),
    }
    workspace_setups = context.get("workspace_setups") or []
    if workspace_setups:
        env["SIM_PLANE_ROS_WORKSPACE_SETUPS"] = os.pathsep.join(str(path) for path in workspace_setups)
    return env


def load_result_payload(path):
    if path is None:
        return {}
    candidate = Path(path)
    if not candidate.is_file():
        return {}
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AdapterError("external command result JSON must be an object: {0}".format(candidate))
    payload.setdefault("metrics", {})
    payload.setdefault("notes", [])
    return payload


def shutil_which(executable, env):
    path_value = (env or os.environ).get("PATH", "")
    for directory in path_value.split(os.pathsep):
        if not directory:
            continue
        candidate = Path(directory) / executable
        if candidate.is_file() and os.access(str(candidate), os.X_OK):
            return str(candidate)
    return None
