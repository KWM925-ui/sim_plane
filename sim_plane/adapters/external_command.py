import json
import os
import shlex
import signal
import subprocess
import time
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

        stop_event = context.get("adapter_stop_event")
        stop_requested = False
        timed_out = False
        start_wall = time.time()
        while process.poll() is None:
            if stop_event is not None and stop_event.wait(timeout=0.2):
                stop_requested = True
                break
            if time.time() - start_wall > config["max_runtime_s"]:
                timed_out = True
                sink.emit_event(
                    "warning",
                    "external algorithm runtime exceeded limit",
                    {"adapter": self.name, "max_runtime_s": config["max_runtime_s"], "pid": process.pid},
                )
                break

        if stop_requested or timed_out:
            terminate_process(
                process,
                sink,
                "external_algorithm",
                stop_signal=config["stop_signal"],
                wait_timeout_s=config["stop_wait_timeout_s"],
            )

        exit_code = process.poll()
        payload = load_result_payload(config["result_json"])
        process_success = determine_process_success(
            exit_code=exit_code,
            stop_requested=stop_requested,
            timed_out=timed_out,
            success_exit_codes=config["success_exit_codes"],
            allow_timeout_as_success=config["allow_timeout_as_success"],
            treat_stop_request_as_success=config["treat_stop_request_as_success"],
            stop_signal=config["stop_signal"],
        )
        success = merge_payload_success(process_success, payload)

        platform_metrics = {
            "algorithm_adapter_name": self.name,
            "algorithm_adapter_completed_successfully": success,
            "algorithm_adapter_exit_code": exit_code if exit_code is not None else -1,
            "algorithm_adapter_timed_out": timed_out,
            "algorithm_adapter_stop_requested": stop_requested,
            "algorithm_adapter_command": command_for_log,
        }
        metrics = merge_payload_metrics(platform_metrics, payload)
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
        "treat_stop_request_as_success": bool(spec.get("treat_stop_request_as_success", True)),
        "stop_signal": resolve_signal(spec.get("stop_signal", "SIGINT")),
        "stop_wait_timeout_s": float(spec.get("stop_wait_timeout_s", 4.0)),
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
    if "success" in payload and not isinstance(payload["success"], bool):
        raise AdapterError("external command result JSON success must be a boolean: {0}".format(candidate))
    if not isinstance(payload["metrics"], dict):
        raise AdapterError("external command result JSON metrics must be an object: {0}".format(candidate))
    if not isinstance(payload["notes"], list):
        raise AdapterError("external command result JSON notes must be a list: {0}".format(candidate))
    return payload


def determine_process_success(
    exit_code,
    stop_requested,
    timed_out,
    success_exit_codes,
    allow_timeout_as_success,
    treat_stop_request_as_success,
    stop_signal=signal.SIGINT,
):
    if timed_out:
        return bool(allow_timeout_as_success)
    if stop_requested and treat_stop_request_as_success:
        return exit_code in success_exit_codes or exit_code in (-stop_signal, 128 + stop_signal)
    return exit_code in success_exit_codes


def merge_payload_success(process_success, payload):
    if not payload or "success" not in payload:
        return bool(process_success)
    if not isinstance(payload["success"], bool):
        raise AdapterError("external command result JSON success must be a boolean.")
    return bool(process_success and payload["success"])


def merge_payload_metrics(platform_metrics, payload):
    merged = {}
    for key, value in (payload.get("metrics", {}) if payload else {}).items():
        merged[str(key)] = value
    merged.update(platform_metrics)
    return merged


def resolve_signal(name_or_number):
    if isinstance(name_or_number, int):
        return name_or_number
    candidate = str(name_or_number).strip()
    if not candidate:
        return signal.SIGINT
    if candidate.isdigit():
        return int(candidate)
    if not candidate.startswith("SIG"):
        candidate = "SIG{0}".format(candidate.upper())
    if not hasattr(signal, candidate):
        raise AdapterError("Unknown stop signal for external_command: {0}".format(name_or_number))
    return getattr(signal, candidate)


def shutil_which(executable, env):
    path_value = (env or os.environ).get("PATH", "")
    for directory in path_value.split(os.pathsep):
        if not directory:
            continue
        candidate = Path(directory) / executable
        if candidate.is_file() and os.access(str(candidate), os.X_OK):
            return str(candidate)
    return None
