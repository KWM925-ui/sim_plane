import math
import os
import shlex
import subprocess
import time
from pathlib import Path

from pymavlink import mavutil

from sim_plane.adapters import collect_algorithm_adapter, has_algorithm_adapter, start_algorithm_adapter, validate_algorithm_adapter
from sim_plane.backends.base import Backend, BackendError
from sim_plane.processes import start_log_threads, terminate_process
from sim_plane.px4_ulog import (
    collect_px4_ulog_artifacts_safely,
    px4_ulog_metrics,
    px4_ulog_note,
    snapshot_px4_ulog_files,
)


MODEL_BY_VEHICLE = {
    "quadrotor": "sihsim_quadx",
    "multirotor": "sihsim_quadx",
    "fixedwing": "sihsim_airplane",
    "airplane": "sihsim_airplane",
}

QGC_CANDIDATES = [
    Path("/home/coco/桌面/QGroundControl.AppImage"),
    Path("/home/coco/Desktop/QGroundControl.AppImage"),
    Path("/home/coco/QGroundControl.AppImage"),
    Path("/home/nv/QGroundControl.AppImage"),
]

PX4_CANDIDATES = [
    Path("/home/coco/PX4-Autopilot"),
    Path("/home/coco/px4-autopilot"),
    Path("/home/coco/reference_upstream/PX4-Autopilot"),
    Path("/home/coco/sim_plane_ws/src/core/PX4-Autopilot"),
    Path("/home/nv/PX4-Autopilot"),
]


class PX4SIHBackend(Backend):
    name = "px4_sih"

    def validate_environment(self, scenario=None):
        config = build_runtime_config(scenario or {})
        issues = []
        if not config["px4_dir"]:
            issues.append(
                "PX4-Autopilot checkout not found. Set PX4_AUTOPILOT_DIR, pass --px4-dir, "
                "or place the repo in a common path such as /home/coco/PX4-Autopilot."
            )
        if config["launch_qgc"] and not config["qgc_path"]:
            issues.append(
                "QGroundControl launch requested but AppImage was not found. "
                "Set QGROUNDCONTROL_PATH or place QGroundControl.AppImage in a common path."
            )
        if config["launch_jmavsim"] and not config["java_path"]:
            issues.append("jMAVSim launch requested but `java` was not found on PATH.")
        if config["launch_jmavsim"] and not config.get("ant_path"):
            issues.append("jMAVSim launch requested but `ant` was not found on PATH.")
        if config["launch_jmavsim"] and not config["jmavsim_script"]:
            issues.append(
                "jMAVSim launch requested but Tools/simulation/jmavsim/jmavsim_run.sh was not found under PX4."
            )
        if has_algorithm_adapter((scenario or {}).get("algorithm_adapter")) and config["shell_commands"]:
            issues.append("Choose one PX4 control path: algorithm_adapter or backend shell_commands, not both.")
        issues.extend(
            validate_algorithm_adapter(
                (scenario or {}).get("algorithm_adapter"),
                context=build_algorithm_adapter_context(scenario or {}, config),
            )
        )
        return issues

    def run(self, scenario, sink):
        config = build_runtime_config(scenario)
        if not config["px4_dir"]:
            raise BackendError(
                "PX4-Autopilot checkout not found. Pass --px4-dir or export PX4_AUTOPILOT_DIR first."
            )

        sink.emit_event(
            "info",
            "px4_sih launch plan",
            {
                "px4_dir": str(config["px4_dir"]),
                "model": config["model"],
                "mavlink_endpoint": config["mavlink_endpoint"],
                "launch_qgc": config["launch_qgc"],
                "launch_jmavsim": config["launch_jmavsim"],
            },
        )

        px4_process = None
        viewer_processes = []
        connection = None
        adapter_handle = None
        adapter_collected = False
        result = None
        ulog_before = snapshot_px4_ulog_files(config)
        try:
            px4_process = launch_px4(config, sink)
            if config["launch_qgc"]:
                viewer_processes.append(launch_qgc(config, sink))
            if config["launch_jmavsim"]:
                viewer_processes.append(launch_jmavsim(config, sink))

            connection = mavutil.mavlink_connection(config["mavlink_endpoint"], autoreconnect=True)
            heartbeat = wait_for_heartbeat(connection, config["connect_timeout_s"])
            sink.emit_event(
                "info",
                "px4 heartbeat received",
                {
                    "system_id": heartbeat.get_srcSystem(),
                    "component_id": heartbeat.get_srcComponent(),
                },
            )
            if has_algorithm_adapter(scenario.get("algorithm_adapter")) and config["shell_commands"]:
                raise BackendError("Choose one PX4 control path: algorithm_adapter or backend shell_commands, not both.")
            if has_algorithm_adapter(scenario.get("algorithm_adapter")):
                adapter_handle = start_algorithm_adapter(
                    scenario.get("algorithm_adapter"),
                    sink,
                    context=build_algorithm_adapter_context(scenario, config),
                )
                scenario["_sim_plane_internal_adapter_handle"] = adapter_handle
                scenario["_sim_plane_internal_backend_config"] = config
            else:
                maybe_send_shell_commands(px4_process, config, sink)
            telemetry_start_wall = time.time()

            telemetry_summary = stream_px4_telemetry(
                scenario=scenario,
                sink=sink,
                connection=connection,
                px4_process=px4_process,
                start_wall=telemetry_start_wall,
            )
            adapter_report = collect_algorithm_adapter(
                adapter_handle,
                timeout_s=float(
                    (scenario.get("algorithm_adapter") or {}).get("join_timeout_s", 3.0)
                ),
                request_stop=adapter_handle is not None,
            )
            adapter_collected = True
            telemetry_summary.update(adapter_report["metrics"])
            result = {
                "status": evaluate_run_status(config["success_criteria"], telemetry_summary),
                "backend": self.name,
                "vehicle": scenario["vehicle"],
                "scenario_name": scenario["name"],
                "metrics": telemetry_summary,
                "notes": build_notes(config, adapter_notes=adapter_report["notes"]),
            }
            return result
        except Exception:
            raise
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            if adapter_handle is not None and not adapter_collected:
                collect_algorithm_adapter(
                    adapter_handle,
                    timeout_s=float((scenario.get("algorithm_adapter") or {}).get("join_timeout_s", 3.0)),
                    request_stop=True,
                )
            for process in reversed(viewer_processes):
                terminate_process(process, sink, "viewer")
            terminate_process(px4_process, sink, "px4")
            ulog_report = collect_px4_ulog_artifacts_safely(
                config,
                sink.artifact_writer.artifact_dir,
                before_snapshot=ulog_before,
                sink=sink,
                label=self.name,
            )
            if result is not None:
                result.setdefault("metrics", {}).update(px4_ulog_metrics(ulog_report))
                result.setdefault("notes", []).append(px4_ulog_note(ulog_report))


def build_runtime_config(scenario):
    backend_options = dict(scenario.get("backend_options", {}))
    px4_dir = resolve_px4_dir(backend_options.get("px4_dir"))
    toolchain_root = resolve_toolchain_root(px4_dir)
    toolchain_bin_dirs = discover_toolchain_bin_dirs(toolchain_root)
    model = backend_options.get("model") or MODEL_BY_VEHICLE.get(scenario.get("vehicle"), "sihsim_quadx")
    build_target = backend_options.get("build_target", "px4_sitl_sih")
    qgc_path = resolve_qgc_path(backend_options.get("qgc_path"))
    jmavsim_script = resolve_jmavsim_script(px4_dir)
    java_path = resolve_executable("java", toolchain_bin_dirs)
    ant_path = resolve_executable("ant", toolchain_bin_dirs)
    connect_timeout_s = backend_options.get("connect_timeout_s")
    if connect_timeout_s is None:
        connect_timeout_s = default_connect_timeout(px4_dir, build_target)
    return {
        "px4_dir": px4_dir,
        "build_dir": px4_dir / "build" / build_target if px4_dir else None,
        "toolchain_root": toolchain_root,
        "toolchain_bin_dirs": toolchain_bin_dirs,
        "model": model,
        "build_target": build_target,
        "mavlink_endpoint": backend_options.get("mavlink_endpoint", "udpin:127.0.0.1:14540"),
        "launch_rviz": bool(backend_options.get("launch_rviz", False)),
        "launch_qgc": bool(backend_options.get("launch_qgc", False)),
        "launch_jmavsim": bool(backend_options.get("launch_jmavsim", False)),
        "qgc_path": qgc_path,
        "jmavsim_script": jmavsim_script,
        "java_path": java_path,
        "ant_path": ant_path,
        "connect_timeout_s": float(connect_timeout_s),
        "process_start_grace_s": float(backend_options.get("process_start_grace_s", 2.0)),
        "sample_hz": float(scenario.get("update_hz", 5.0)),
        "jmavsim_port": int(backend_options.get("jmavsim_port", 19410)),
        "speed_factor": float(backend_options.get("speed_factor", 1.0)),
        "shell_commands": list(backend_options.get("shell_commands", [])),
        "shell_command_delay_s": float(backend_options.get("shell_command_delay_s", 2.0)),
        "shell_command_interval_s": float(backend_options.get("shell_command_interval_s", 0.5)),
        "success_criteria": backend_options.get("success_criteria", "telemetry"),
        "allow_early_stop_on_adapter_success": bool(
            backend_options.get("allow_early_stop_on_adapter_success", False)
        ),
        "collect_ulog": bool(backend_options.get("collect_ulog", True)),
        "collect_ulog_max_files": int(backend_options.get("collect_ulog_max_files", 3)),
    }


def resolve_px4_dir(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.environ.get("PX4_AUTOPILOT_DIR")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(PX4_CANDIDATES)

    for candidate in candidates:
        if is_px4_root(candidate):
            return candidate.resolve()
    return None


def resolve_qgc_path(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.environ.get("QGROUNDCONTROL_PATH")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(QGC_CANDIDATES)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def resolve_jmavsim_script(px4_dir):
    if not px4_dir:
        return None
    candidate = px4_dir / "Tools" / "simulation" / "jmavsim" / "jmavsim_run.sh"
    return candidate if candidate.is_file() else None


def resolve_toolchain_root(px4_dir):
    if not px4_dir:
        return None
    try:
        return px4_dir.parents[2] / "toolchains"
    except IndexError:
        return None


def discover_toolchain_bin_dirs(toolchain_root):
    if toolchain_root is None or not toolchain_root.is_dir():
        return []
    bin_dirs = []
    for child in sorted(toolchain_root.iterdir()):
        candidate = child / "bin"
        if candidate.is_dir():
            bin_dirs.append(candidate)
    return bin_dirs


def resolve_executable(name, extra_bin_dirs=None):
    search_dirs = [str(path) for path in extra_bin_dirs or []]
    search_dirs.extend(os.environ.get("PATH", "").split(os.pathsep))
    for path_dir in search_dirs:
        candidate = Path(path_dir) / name
        if candidate.is_file() and os.access(str(candidate), os.X_OK):
            return candidate
    return None


def is_px4_root(path):
    candidate = Path(path)
    return (
        candidate.is_dir()
        and (candidate / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").is_file()
        and (candidate / "Tools").is_dir()
    )


def default_connect_timeout(px4_dir, build_target):
    if not px4_dir:
        return 25.0
    px4_binary = Path(px4_dir) / "build" / build_target / "bin" / "px4"
    return 45.0 if px4_binary.is_file() else 240.0


def launch_px4(config, sink):
    env = os.environ.copy()
    env["PX4_SIM_SPEED_FACTOR"] = str(config["speed_factor"])
    command = ["make", config["build_target"], config["model"]]
    sink.emit_event(
        "info",
        "launching px4_sih",
        {"command": " ".join(shlex.quote(part) for part in command), "cwd": str(config["px4_dir"])},
    )
    process = subprocess.Popen(
        command,
        cwd=str(config["px4_dir"]),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_px4_log_threads(process, sink, "px4")
    time.sleep(config["process_start_grace_s"])
    if process.poll() is not None:
        raise BackendError("PX4 exited before the MAVLink connection phase completed.")
    return process


def launch_qgc(config, sink):
    if not config["qgc_path"]:
        raise BackendError("QGroundControl launch requested, but no AppImage path was resolved.")
    ensure_executable(config["qgc_path"])
    sink.emit_event("info", "launching qgroundcontrol", {"path": str(config["qgc_path"])})
    process = subprocess.Popen(
        [str(config["qgc_path"])],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_px4_log_threads(process, sink, "qgc")
    return process


def launch_jmavsim(config, sink):
    if not config["java_path"]:
        raise BackendError("jMAVSim launch requested, but java is not installed.")
    if not config["ant_path"]:
        raise BackendError("jMAVSim launch requested, but ant is not installed.")
    if not config["jmavsim_script"]:
        raise BackendError("jMAVSim launch requested, but the PX4 jmavsim_run.sh script was not found.")

    ensure_executable(config["jmavsim_script"])
    command = [str(config["jmavsim_script"]), "-p", str(config["jmavsim_port"]), "-u", "-q", "-o"]
    if "airplane" in config["model"]:
        command.append("-a")
    sink.emit_event(
        "info",
        "launching jmavsim",
        {"command": " ".join(shlex.quote(part) for part in command), "cwd": str(config["px4_dir"])},
    )
    env = os.environ.copy()
    prepend_bin_dirs_to_path(env, config["toolchain_bin_dirs"])
    env["JAVA_HOME"] = str(config["java_path"].resolve().parent.parent)
    process = subprocess.Popen(
        command,
        cwd=str(config["px4_dir"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_px4_log_threads(process, sink, "jmavsim")
    return process


def ensure_executable(path):
    mode = path.stat().st_mode
    if not mode & 0o111:
        path.chmod(mode | 0o111)


def wait_for_heartbeat(connection, timeout_s):
    heartbeat = connection.wait_heartbeat(timeout=timeout_s)
    if heartbeat is None:
        raise BackendError("Timed out waiting for a PX4 MAVLink heartbeat on the configured endpoint.")
    return heartbeat


def stream_px4_telemetry(scenario, sink, connection, px4_process, start_wall):
    duration_s = float(scenario["duration_s"])
    sample_period = 1.0 / max(float(scenario.get("update_hz", 5.0)), 1.0)
    target_altitude_m = float(scenario.get("target_altitude_m", 10.0))
    deadline = start_wall + duration_s
    next_emit = start_wall
    state = initial_state()
    telemetry_count = 0
    mavlink_count = 0
    max_altitude_m = 0.0
    max_speed_mps = 0.0
    reached_target_altitude = False
    mode_changes = 0
    last_mode = None
    last_armed = None
    ever_armed = False
    adapter_handle = scenario.get("_sim_plane_internal_adapter_handle")
    allow_early_stop = bool(
        (scenario.get("_sim_plane_internal_backend_config") or {}).get(
            "allow_early_stop_on_adapter_success", False
        )
    )

    while time.time() <= deadline:
        if px4_process.poll() is not None:
            raise BackendError("PX4 exited before the configured run duration elapsed.")

        if allow_early_stop and adapter_handle is not None and not adapter_handle.thread.is_alive():
            sink.emit_event(
                "info",
                "px4_sih early stop on adapter success",
                {"t": round(time.time() - start_wall, 2)},
            )
            break

        message = connection.recv_match(blocking=True, timeout=0.2)
        if message is not None:
            mavlink_count += 1
            update_state_from_message(state, message)
            if state["mode"] != last_mode:
                mode_changes += 1
                last_mode = state["mode"]
                sink.emit_event("info", "px4 mode change", {"mode": state["mode"], "t": round(time.time() - start_wall, 2)})
            if state["armed"] != last_armed:
                last_armed = state["armed"]
                ever_armed = ever_armed or state["armed"]
                sink.emit_event(
                    "info",
                    "px4 arm state change",
                    {"armed": state["armed"], "t": round(time.time() - start_wall, 2)},
                )

        now = time.time()
        if now >= next_emit:
            elapsed = now - start_wall
            phase = infer_phase(state, target_altitude_m)
            sample = {
                "t": round(elapsed, 3),
                "phase": phase,
                "mode": state["mode"],
                "armed": state["armed"],
                "position": {
                    "x_m": round(state["x_m"], 3),
                    "y_m": round(state["y_m"], 3),
                    "z_m": round(state["z_m"], 3),
                },
                "altitude_m": round(state["altitude_m"], 3),
                "speed_mps": round(state["speed_mps"], 3),
                "battery_pct": round(state["battery_pct"], 2) if state["battery_pct"] is not None else None,
                "heading_deg": round(state["heading_deg"], 2),
            }
            sink.emit_telemetry(sample)
            telemetry_count += 1
            max_altitude_m = max(max_altitude_m, state["altitude_m"])
            max_speed_mps = max(max_speed_mps, state["speed_mps"])
            if state["altitude_m"] >= target_altitude_m * 0.95:
                reached_target_altitude = True
            next_emit = now + sample_period

    return {
        "telemetry_count": telemetry_count,
        "mavlink_message_count": mavlink_count,
        "max_altitude_m": round(max_altitude_m, 3),
        "max_speed_mps": round(max_speed_mps, 3),
        "target_altitude_reached": reached_target_altitude,
        "ever_armed": ever_armed,
        "mode_changes": mode_changes,
        "duration_s": duration_s,
    }


def initial_state():
    return {
        "mode": "BOOT",
        "armed": False,
        "x_m": 0.0,
        "y_m": 0.0,
        "z_m": 0.0,
        "altitude_m": 0.0,
        "have_local_position": False,
        "speed_mps": 0.0,
        "battery_pct": None,
        "heading_deg": 0.0,
    }


def update_state_from_message(state, message):
    msg_type = message.get_type()
    if msg_type == "BAD_DATA":
        return
    if msg_type == "HEARTBEAT":
        get_src_component = getattr(message, "get_srcComponent", None)
        if callable(get_src_component):
            component_id = get_src_component()
            if component_id not in (None, mavutil.mavlink.MAV_COMP_ID_AUTOPILOT1):
                return
        state["armed"] = bool(message.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        state["mode"] = mavutil.mode_string_v10(message)
        return
    if msg_type == "LOCAL_POSITION_NED":
        state["x_m"] = getattr(message, "x", state["x_m"])
        state["y_m"] = getattr(message, "y", state["y_m"])
        state["z_m"] = getattr(message, "z", state["z_m"])
        state["altitude_m"] = max(0.0, -float(state["z_m"]))
        state["have_local_position"] = True
        vx = float(getattr(message, "vx", 0.0))
        vy = float(getattr(message, "vy", 0.0))
        vz = float(getattr(message, "vz", 0.0))
        state["speed_mps"] = math.sqrt(vx * vx + vy * vy + vz * vz)
        return
    if msg_type == "GLOBAL_POSITION_INT":
        relative_alt = getattr(message, "relative_alt", None)
        if relative_alt is not None and not state["have_local_position"]:
            state["altitude_m"] = max(0.0, float(relative_alt) / 1000.0)
        hdg = getattr(message, "hdg", None)
        if hdg is not None and hdg != 65535:
            state["heading_deg"] = float(hdg) / 100.0
        return
    if msg_type == "ATTITUDE":
        yaw = float(getattr(message, "yaw", 0.0))
        state["heading_deg"] = (math.degrees(yaw) + 360.0) % 360.0
        return
    if msg_type == "VFR_HUD":
        if hasattr(message, "groundspeed"):
            state["speed_mps"] = float(message.groundspeed)
        if hasattr(message, "alt") and not state["have_local_position"]:
            state["altitude_m"] = max(0.0, float(message.alt))
        if hasattr(message, "heading"):
            state["heading_deg"] = float(message.heading)
        return
    if msg_type == "SYS_STATUS":
        battery_remaining = getattr(message, "battery_remaining", None)
        if battery_remaining is not None and battery_remaining >= 0:
            state["battery_pct"] = float(battery_remaining)


def infer_phase(state, target_altitude_m):
    if state["mode"] in {"BOOT", "INIT"}:
        return "boot"
    if not state["armed"]:
        return "standby"
    if "LAND" in state["mode"]:
        return "land"
    if state["altitude_m"] < max(1.0, target_altitude_m * 0.8):
        return "takeoff"
    return "mission"


def build_notes(config):
    notes = [
        "The px4_sih backend uses pymavlink to feed the local dashboard from live MAVLink telemetry.",
    ]
    if config["launch_qgc"]:
        notes.append("QGroundControl was requested as an auxiliary viewer.")
    if config["launch_jmavsim"]:
        notes.append("jMAVSim was requested as the 3D display-only viewer for SIH.")
    return notes


def build_notes(config, adapter_notes=None):
    notes = [
        "The px4_sih backend uses pymavlink to feed the local dashboard from live MAVLink telemetry.",
    ]
    if config["launch_qgc"]:
        notes.append("QGroundControl was requested as an auxiliary viewer.")
    if config["launch_jmavsim"]:
        notes.append("jMAVSim was requested as the 3D display-only viewer for SIH.")
    notes.extend(adapter_notes or [])
    return notes


def build_algorithm_adapter_context(scenario, config):
    return {
        "backend": "px4_sih",
        "vehicle": scenario.get("vehicle"),
        "scenario_name": scenario.get("name"),
        "launch_rviz": bool(config.get("launch_rviz", False)),
        "telemetry_endpoint": config["mavlink_endpoint"],
        "preferred_telemetry_port": 14550,
        "system_address": "udp://127.0.0.1:14580",
        "target_altitude_m": float(scenario.get("target_altitude_m", 5.0)),
        "expected_duration_s": float(scenario.get("duration_s", 20.0)),
    }


def prepend_bin_dirs_to_path(env, bin_dirs):
    if not bin_dirs:
        return
    current = env.get("PATH", "")
    env["PATH"] = os.pathsep.join([str(path) for path in bin_dirs] + [current])


def maybe_send_shell_commands(process, config, sink):
    commands = config.get("shell_commands", [])
    if not commands:
        return
    time.sleep(config["shell_command_delay_s"])
    for command in commands:
        send_px4_shell_command(process, sink, command)
        time.sleep(config["shell_command_interval_s"])


def send_px4_shell_command(process, sink, command):
    if process is None or process.stdin is None:
        raise BackendError("PX4 process stdin is not available for shell command injection.")
    sink.emit_event("info", "sending px4 shell command", {"command": command})
    process.stdin.write(command + "\n")
    process.stdin.flush()


def evaluate_run_status(success_criteria, telemetry_summary):
    if success_criteria == "takeoff":
        return "passed" if telemetry_summary["target_altitude_reached"] else "failed"
    if success_criteria == "arm":
        return "passed" if telemetry_summary["ever_armed"] else "failed"
    if success_criteria == "adapter_completed":
        return "passed" if telemetry_summary.get("algorithm_adapter_completed_successfully") else "failed"
    if success_criteria == "adapter_takeoff":
        return (
            "passed"
            if telemetry_summary.get("algorithm_adapter_completed_successfully")
            and telemetry_summary.get("algorithm_adapter_target_altitude_reached")
            and telemetry_summary.get("target_altitude_reached")
            else "failed"
        )
    return "passed" if telemetry_summary["telemetry_count"] > 0 else "failed"


def start_px4_log_threads(process, sink, prefix):
    from sim_plane.processes import start_log_threads as start_threads

    start_threads(process, sink, prefix, event_parser=parse_px4_log_event)


def parse_px4_log_event(label, stream_name, line):
    markers = ["ERROR", "WARN", "Ready", "Startup", "MAVLink", "ERROR ["]
    if not any(marker in line for marker in markers):
        return None
    transient_preflight_markers = (
        "Preflight Fail: heading estimate invalid",
        "Preflight Fail: height estimate not stable",
    )
    if any(marker in line for marker in transient_preflight_markers):
        return {"level": "info", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    level = "warning" if ("WARN" in line or "ERROR" in line or "[e]" in line.lower()) else "info"
    return {"level": level, "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
