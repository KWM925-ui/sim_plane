import os
import shlex
import subprocess
import time
from pathlib import Path

from pymavlink import mavutil

from sim_plane.adapters import collect_algorithm_adapter, has_algorithm_adapter, start_algorithm_adapter, validate_algorithm_adapter
from sim_plane.backends.base import Backend, BackendError
from sim_plane.backends.px4_common import (
    discover_toolchain_bin_dirs,
    ensure_executable,
    evaluate_run_status,
    infer_phase,
    initial_state,
    is_px4_root,
    launch_qgc,
    maybe_send_shell_commands,
    parse_px4_log_event,
    prepend_bin_dirs_to_path,
    resolve_executable,
    resolve_px4_dir,
    resolve_qgc_path,
    resolve_toolchain_root,
    start_px4_log_threads,
    update_state_from_message,
    wait_for_heartbeat,
)
from sim_plane.processes import terminate_process
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
            else:
                maybe_send_shell_commands(px4_process, config, sink)
            telemetry_start_wall = time.time()

            telemetry_summary = stream_px4_telemetry(
                scenario=scenario,
                sink=sink,
                connection=connection,
                px4_process=px4_process,
                start_wall=telemetry_start_wall,
                adapter_handle=adapter_handle,
                allow_early_stop=config.get("allow_early_stop_on_adapter_success", False),
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

def resolve_jmavsim_script(px4_dir):
    if not px4_dir:
        return None
    candidate = px4_dir / "Tools" / "simulation" / "jmavsim" / "jmavsim_run.sh"
    return candidate if candidate.is_file() else None


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


def stream_px4_telemetry(
    scenario,
    sink,
    connection,
    px4_process,
    start_wall,
    adapter_handle=None,
    allow_early_stop=False,
):
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
