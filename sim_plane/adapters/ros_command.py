import os
import shlex
import signal
import subprocess
import time
import xmlrpc.client
from pathlib import Path
from urllib.parse import urlparse

from sim_plane.adapters.base import AdapterError, AlgorithmAdapter
from sim_plane.adapters.external_command import (
    build_context_env,
    merge_payload_metrics,
    load_result_payload,
    merge_payload_success,
    resolve_path,
    shutil_which,
)
from sim_plane.processes import start_log_threads, terminate_process


DEFAULT_ROS_SETUP = Path("/opt/ros/noetic/setup.bash")


class ROSCommandAdapter(AlgorithmAdapter):
    name = "ros_command"
    requires_dedicated_udp_port = False

    def validate_environment(self, spec=None, context=None):
        config = build_runtime_config(spec or {}, context or {}, artifact_dir=None, skip_source=True)
        issues = []
        if not config["command"]:
            issues.append("The ros_command adapter requires a non-empty command field.")
        if config["workdir"] is not None and not config["workdir"].is_dir():
            issues.append("The ros_command workdir does not exist: {0}".format(config["workdir"]))
        for setup_path in config["setup_paths"]:
            if not setup_path.is_file():
                issues.append("The ros_command setup.bash was not found: {0}".format(setup_path))
        executable_env = None
        if not issues:
            executable_env = load_sourced_environment(config["setup_paths"])
        if not config["shell"]:
            executable = config["command"][0] if isinstance(config["command"], list) and config["command"] else None
            if executable and shutil_which(executable, executable_env or os.environ) is None:
                issues.append("The ros_command executable is not on PATH: {0}".format(executable))
        return issues

    def run(self, spec, sink, context):
        issues = self.validate_environment(spec, context)
        if issues:
            raise AdapterError("; ".join(issues))
        config = build_runtime_config(
            spec or {},
            context or {},
            artifact_dir=sink.artifact_writer.artifact_dir,
        )

        command_for_log = (
            config["command"]
            if isinstance(config["command"], str)
            else " ".join(shlex.quote(part) for part in config["command"])
        )
        sink.emit_event(
            "info",
            "ros algorithm adapter launch plan",
            {
                "adapter": self.name,
                "command": command_for_log,
                "workdir": str(config["workdir"]) if config["workdir"] is not None else None,
                "setup_paths": [str(path) for path in config["setup_paths"]],
                "required_published_topics": config["required_published_topics"],
                "required_subscribed_topics": config["required_subscribed_topics"],
                "ros_master_uri": config["env"].get("ROS_MASTER_URI"),
                "result_json": str(config["result_json"]),
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
        try:
            start_log_threads(process, sink, "ros_algorithm", event_parser=parse_ros_command_event)
            if config["post_launch_grace_s"] > 0.0:
                time.sleep(config["post_launch_grace_s"])
            if process.poll() is not None:
                raise AdapterError("ros_command exited before finishing startup readiness checks.")

            stop_event = context.get("adapter_stop_event")
            wait_for_ros_master(config["env"]["ROS_MASTER_URI"], config["master_timeout_s"], stop_event=stop_event)
            ready_report = wait_for_topic_bindings(
                process=process,
                master_uri=config["env"]["ROS_MASTER_URI"],
                required_published_topics=config["required_published_topics"],
                required_subscribed_topics=config["required_subscribed_topics"],
                timeout_s=config["ready_timeout_s"],
                stop_event=stop_event,
            )
            sink.emit_event(
                "info",
                "ros algorithm adapter is ready",
                {
                    "adapter": self.name,
                    "required_published_topics": ready_report["published_topics"],
                    "required_subscribed_topics": ready_report["subscribed_topics"],
                },
            )

            stop_requested = False
            timed_out = False
            start_wall = time.time()
            while process.poll() is None:
                if stop_event is not None and stop_event.wait(timeout=0.2):
                    stop_requested = True
                    break
                if config["max_runtime_s"] is not None and time.time() - start_wall > config["max_runtime_s"]:
                    timed_out = True
                    sink.emit_event(
                        "warning",
                        "ros algorithm runtime exceeded limit",
                        {"adapter": self.name, "max_runtime_s": config["max_runtime_s"], "pid": process.pid},
                    )
                    break

            if stop_requested or timed_out:
                terminate_process(
                    process,
                    sink,
                    "ros_algorithm",
                    stop_signal=config["stop_signal"],
                    wait_timeout_s=config["stop_wait_timeout_s"],
                )

            exit_code = process.poll()
            payload = load_result_payload(config["result_json"])
            process_success = determine_success(
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
                "algorithm_adapter_ready": True,
                "algorithm_adapter_stop_requested": stop_requested,
                "algorithm_adapter_command": command_for_log,
            }
            metrics = merge_payload_metrics(platform_metrics, payload)
            notes = [
                "The ros_command adapter sourced ROS and workspace overlays, then launched the user algorithm as a first-class ROS process under sim_plane.",
                "The adapter exported stable SIM_PLANE_* environment variables so the algorithm can discover topics, ROS master settings, and artifact paths without hard-coded machine paths.",
            ]
            notes.extend(payload.get("notes", []))

            if not success:
                raise AdapterError(
                    "ros_command adapter failed: exit_code={0}, stop_requested={1}, timed_out={2}, result_json={3}".format(
                        exit_code,
                        stop_requested,
                        timed_out,
                        str(config["result_json"]),
                    )
                )

            return {
                "metrics": metrics,
                "notes": notes,
            }
        except Exception:
            if process.poll() is None:
                terminate_process(
                    process,
                    sink,
                    "ros_algorithm",
                    stop_signal=config["stop_signal"],
                    wait_timeout_s=config["stop_wait_timeout_s"],
                )
            raise


def build_runtime_config(spec, context, artifact_dir, skip_source=False):
    command = spec.get("command")
    shell = bool(spec.get("shell", False))
    workdir = resolve_path(spec.get("workdir"))
    setup_paths = build_setup_paths(spec, context)
    result_json = None
    context_env = build_context_env(context or {}, artifact_dir)
    context_env["SIM_PLANE_ROS_SETUP"] = str(setup_paths[0]) if setup_paths else None
    if len(setup_paths) > 1:
        context_env["SIM_PLANE_ROS_WORKSPACE_SETUPS"] = os.pathsep.join(str(path) for path in setup_paths[1:])
    if artifact_dir is not None:
        adapter_dir = Path(artifact_dir) / "algorithm_adapter"
        adapter_dir.mkdir(parents=True, exist_ok=True)
        result_json = adapter_dir / "result.json"
        context_env["SIM_PLANE_ADAPTER_RESULT_JSON"] = str(result_json)
    elif spec.get("result_json"):
        result_json = resolve_path(spec.get("result_json"), workdir)

    env = os.environ.copy()
    if not skip_source:
        env.update(load_sourced_environment(setup_paths))
    env.update(
        {
            "ROS_MASTER_URI": str(context.get("ros_master_uri") or env.get("ROS_MASTER_URI") or "http://127.0.0.1:11311"),
            "ROS_HOSTNAME": str(context.get("ros_hostname") or env.get("ROS_HOSTNAME") or "127.0.0.1"),
            "ROS_IP": str(context.get("ros_ip") or env.get("ROS_IP") or "127.0.0.1"),
        }
    )
    if artifact_dir is not None:
        artifact_root = Path(artifact_dir).resolve()
        ros_home = artifact_root / "ros_home"
        ros_log_dir = artifact_root / "ros_logs"
        ros_home.mkdir(parents=True, exist_ok=True)
        ros_log_dir.mkdir(parents=True, exist_ok=True)
        env["ROS_HOME"] = str(ros_home)
        env["ROS_LOG_DIR"] = str(ros_log_dir)
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

    max_runtime_s = spec.get("max_runtime_s")
    if max_runtime_s is not None:
        max_runtime_s = float(max_runtime_s)

    return {
        "command": normalized_command,
        "shell": shell,
        "workdir": workdir,
        "env": env,
        "result_json": result_json,
        "setup_paths": setup_paths,
        "required_published_topics": normalize_topics(spec.get("required_published_topics")),
        "required_subscribed_topics": normalize_topics(spec.get("required_subscribed_topics")),
        "master_timeout_s": float(spec.get("master_timeout_s", context.get("startup_timeout_s", 20.0))),
        "ready_timeout_s": float(spec.get("ready_timeout_s", 10.0)),
        "post_launch_grace_s": float(spec.get("post_launch_grace_s", 1.0)),
        "stop_signal": resolve_signal(spec.get("stop_signal", "SIGINT")),
        "stop_wait_timeout_s": float(spec.get("stop_wait_timeout_s", 8.0)),
        "success_exit_codes": [int(code) for code in spec.get("success_exit_codes", [0])],
        "allow_timeout_as_success": bool(spec.get("allow_timeout_as_success", False)),
        "treat_stop_request_as_success": bool(spec.get("treat_stop_request_as_success", True)),
        "max_runtime_s": max_runtime_s,
    }


def normalize_topics(value):
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return [str(item).strip() for item in value if str(item).strip()]


def build_setup_paths(spec, context):
    ordered = []
    ros_setup = resolve_path(spec.get("ros_setup")) or resolve_path(context.get("ros_setup")) or DEFAULT_ROS_SETUP
    ordered.append(ros_setup)

    for candidate in normalize_setup_list(context.get("workspace_setups")):
        ordered.append(candidate)
    for candidate in normalize_setup_list(spec.get("workspace_setups")):
        ordered.append(candidate)
    if spec.get("workspace_setup"):
        ordered.append(resolve_path(spec.get("workspace_setup")))
    for workspace_dir in normalize_setup_list(spec.get("workspace_dirs"), assume_setup=False):
        ordered.append(workspace_dir / "devel" / "setup.bash")

    deduped = []
    seen = set()
    for candidate in ordered:
        if candidate is None:
            continue
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def normalize_setup_list(value, assume_setup=True):
    if value is None:
        return []
    items = [value] if isinstance(value, (str, Path)) else list(value)
    normalized = []
    for item in items:
        path = resolve_path(item)
        if path is None:
            continue
        if assume_setup or path.name == "setup.bash":
            normalized.append(path)
        else:
            normalized.append(path)
    return normalized


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


def wait_for_ros_master(master_uri, timeout_s, stop_event=None):
    parsed = urlparse(master_uri)
    if not parsed.scheme or not parsed.netloc:
        raise AdapterError("Invalid ROS_MASTER_URI: {0}".format(master_uri))

    deadline = time.time() + max(timeout_s, 0.1)
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            raise AdapterError("ros_command stopped before ROS master became ready.")
        try:
            proxy = xmlrpc.client.ServerProxy(master_uri)
            code, _, _ = proxy.getSystemState("/sim_plane_ros_command")
            if code == 1:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise AdapterError("Timed out waiting for ROS master at {0}".format(master_uri))


def wait_for_topic_bindings(
    process,
    master_uri,
    required_published_topics,
    required_subscribed_topics,
    timeout_s,
    stop_event=None,
):
    deadline = time.time() + max(timeout_s, 0.1)
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            raise AdapterError("ros_command stopped before required ROS topic bindings appeared.")
        if process.poll() is not None:
            raise AdapterError("ros_command exited before required ROS topic bindings appeared.")
        published_topics, subscribed_topics = fetch_topic_state(master_uri)
        if published_topics is None or subscribed_topics is None:
            time.sleep(0.2)
            continue
        missing_published = [topic for topic in required_published_topics if topic not in published_topics]
        missing_subscribed = [topic for topic in required_subscribed_topics if topic not in subscribed_topics]
        if not missing_published and not missing_subscribed:
            return {
                "published_topics": required_published_topics,
                "subscribed_topics": required_subscribed_topics,
            }
        time.sleep(0.2)
    raise AdapterError(
        "Timed out waiting for ROS topic bindings. Missing published topics: {0}; missing subscribed topics: {1}".format(
            missing_published,
            missing_subscribed,
        )
    )


def fetch_topic_state(master_uri):
    try:
        proxy = xmlrpc.client.ServerProxy(master_uri)
        code, _, state = proxy.getSystemState("/sim_plane_ros_command")
        if code != 1:
            return None, None
    except Exception:
        return None, None

    published_topics = {topic for topic, nodes in state[0] if nodes}
    subscribed_topics = {topic for topic, nodes in state[1] if nodes}
    return published_topics, subscribed_topics


def determine_success(
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
        raise AdapterError("Unknown stop signal for ros_command: {0}".format(name_or_number))
    return getattr(signal, candidate)


def parse_ros_command_event(label, stream_name, line):
    if "[ERROR]" in line or "Traceback" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "[WARN]" in line:
        return {"level": "warning", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if "shutdown request" in line.lower() or "process has finished cleanly" in line:
        return {"level": "info", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    return None
