import os
import shlex
import socket
import subprocess
import time
from pathlib import Path

from pymavlink import mavutil

from sim_plane.adapters import collect_algorithm_adapter, has_algorithm_adapter, start_algorithm_adapter, validate_algorithm_adapter
from sim_plane.backends.base import Backend, BackendError
from sim_plane.backends.px4_sih import (
    discover_toolchain_bin_dirs,
    evaluate_run_status,
    infer_phase,
    initial_state,
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
from sim_plane.processes import start_log_threads, terminate_process
from sim_plane.px4_ulog import (
    collect_px4_ulog_artifacts_safely,
    px4_ulog_metrics,
    px4_ulog_note,
    snapshot_px4_ulog_files,
)


MODEL_BY_VEHICLE = {
    "quadrotor": "iris",
    "multirotor": "iris",
}


class PX4GazeboClassicBackend(Backend):
    name = "px4_gazebo_classic"

    def validate_environment(self, scenario=None):
        config = build_runtime_config(scenario or {})
        issues = []
        if not config["px4_dir"]:
            issues.append(
                "PX4-Autopilot checkout not found. Set PX4_AUTOPILOT_DIR, pass --px4-dir, "
                "or place the repo in a common path such as /home/coco/sim_plane_ws/src/core/PX4-Autopilot."
            )
        if not config["sitl_script"]:
            issues.append("PX4 Gazebo Classic sitl_run.sh script was not found under the PX4 checkout.")
        if not config["gazebo_source_dir"]:
            issues.append("PX4 Gazebo Classic sitl_gazebo-classic source tree was not found under the PX4 checkout.")
        if not config["world_file"]:
            issues.append(
                "PX4 Gazebo Classic world file was not found for the requested world. "
                "Use a world with a matching worlds/<WORLD>.world file under the PX4 checkout."
            )
        if not config["model_file"]:
            issues.append(
                "PX4 Gazebo Classic model file was not found for the requested model. "
                "Use a model with a matching models/<MODEL>/<MODEL>.sdf or .sdf.jinja file."
            )
        if not config["gazebo_binary"]:
            issues.append("Gazebo Classic launcher `gazebo` was not found on PATH.")
        if not config["gzserver_binary"]:
            issues.append("Gazebo Classic server `gzserver` was not found on PATH.")
        if not config["gz_binary"]:
            issues.append("Gazebo transport CLI `gz` was not found on PATH.")
        if not config["headless"] and not config["gzclient_binary"]:
            issues.append("Gazebo Classic GUI requested, but `gzclient` was not found on PATH.")
        if config["launch_qgc"] and not config["qgc_path"]:
            issues.append(
                "QGroundControl launch requested but AppImage was not found. "
                "Set QGROUNDCONTROL_PATH or place QGroundControl.AppImage in a common path."
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
        if not config["sitl_script"]:
            raise BackendError("PX4 Gazebo Classic sitl_run.sh script was not found under the selected PX4 checkout.")
        if not config["gazebo_source_dir"]:
            raise BackendError("PX4 Gazebo Classic sitl_gazebo-classic tree was not found under the selected PX4 checkout.")
        if not config["world_file"]:
            raise BackendError("PX4 Gazebo Classic world file was not found for the requested world.")
        if not config["model_file"]:
            raise BackendError("PX4 Gazebo Classic model file was not found for the requested model.")
        if not config["gazebo_binary"] or not config["gzserver_binary"] or not config["gz_binary"]:
            raise BackendError("Required Gazebo Classic executables were not found on PATH.")
        if not config["headless"] and not config["gzclient_binary"]:
            raise BackendError("Gazebo Classic GUI requested, but gzclient is not available on PATH.")

        sink.emit_event(
            "info",
            "px4_gazebo_classic launch plan",
            {
                "px4_dir": str(config["px4_dir"]),
                "model": config["model"],
                "world": config["world"],
                "gazebo_master_uri": config["gazebo_master_uri"],
                "world_file": str(config["world_file"]) if config["world_file"] else None,
                "model_file": str(config["model_file"]) if config["model_file"] else None,
                "build_target": config["build_target"],
                "simulation_target": config["simulation_target"],
                "mavlink_endpoint": config["mavlink_endpoint"],
                "headless": config["headless"],
                "launch_qgc": config["launch_qgc"],
            },
        )

        sitl_process = None
        viewer_processes = []
        connection = None
        adapter_handle = None
        result = None
        ulog_before = snapshot_px4_ulog_files(config)
        try:
            ensure_gazebo_classic_build(config, sink)
            sitl_process = launch_px4_gazebo_classic(config, sink)
            if config["launch_qgc"]:
                viewer_processes.append(launch_qgc(config, sink))

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
                maybe_send_shell_commands(sitl_process, config, sink)
            telemetry_start_wall = time.time()
            telemetry_summary = stream_gazebo_classic_telemetry(
                scenario=scenario,
                sink=sink,
                connection=connection,
                px4_process=sitl_process,
                start_wall=telemetry_start_wall,
            )
            adapter_report = collect_algorithm_adapter(
                adapter_handle,
                timeout_s=float((scenario.get("algorithm_adapter") or {}).get("join_timeout_s", 3.0)),
            )
            telemetry_summary.update(adapter_report["metrics"])
            telemetry_summary["headless"] = config["headless"]
            telemetry_summary["launch_qgc"] = config["launch_qgc"]
            telemetry_summary["gazebo_gui"] = not config["headless"]
            telemetry_summary["world"] = config["world"]
            telemetry_summary["model"] = config["model"]
            result = {
                "status": evaluate_run_status(config["success_criteria"], telemetry_summary),
                "backend": self.name,
                "vehicle": scenario["vehicle"],
                "scenario_name": scenario["name"],
                "metrics": telemetry_summary,
                "notes": build_notes(config, adapter_notes=adapter_report["notes"]),
            }
            return result
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            for process in reversed(viewer_processes):
                terminate_process(process, sink, "viewer")
            terminate_process(
                sitl_process,
                sink,
                "px4_gazebo_classic",
                wait_timeout_s=float(config["stop_wait_timeout_s"]),
            )
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
    model = backend_options.get("model") or MODEL_BY_VEHICLE.get(scenario.get("vehicle"), "iris")
    world = backend_options.get("world", "empty")
    world_file_override = backend_options.get("world_file")
    qgc_path = resolve_qgc_path(backend_options.get("qgc_path"))
    sitl_script = resolve_sitl_script(px4_dir)
    gazebo_source_dir = resolve_gazebo_source_dir(px4_dir)
    world_file = resolve_world_file(px4_dir, world, world_file_override)
    model_file = resolve_model_file(px4_dir, model)
    headless = backend_options.get("headless")
    if headless is None:
        headless = True
    connect_timeout_s = backend_options.get("connect_timeout_s")
    if connect_timeout_s is None:
        connect_timeout_s = default_connect_timeout(px4_dir)
    make_jobs = backend_options.get("make_jobs")
    if make_jobs is None:
        make_jobs = min(max(os.cpu_count() or 1, 1), 4)
    build_target = backend_options.get("build_target", "px4_sitl")
    simulation_target = backend_options.get("simulation_target") or simulation_target_for_model(model)
    return {
        "px4_dir": px4_dir,
        "toolchain_root": toolchain_root,
        "toolchain_bin_dirs": toolchain_bin_dirs,
        "gazebo_master_uri": resolve_gazebo_master_uri(backend_options.get("gazebo_master_uri")),
        "gazebo_binary": resolve_executable("gazebo", toolchain_bin_dirs),
        "gzserver_binary": resolve_executable("gzserver", toolchain_bin_dirs),
        "gzclient_binary": resolve_executable("gzclient", toolchain_bin_dirs),
        "gz_binary": resolve_executable("gz", toolchain_bin_dirs),
        "build_target": build_target,
        "simulation_target": simulation_target,
        "build_dir": px4_dir / "build" / "px4_sitl_default" if px4_dir else None,
        "px4_binary": px4_dir / "build" / "px4_sitl_default" / "bin" / "px4" if px4_dir else None,
        "sitl_script": sitl_script,
        "gazebo_source_dir": gazebo_source_dir,
        "world_file": world_file,
        "model_file": model_file,
        "model": model,
        "world": world,
        "headless": bool(headless),
        "launch_rviz": bool(backend_options.get("launch_rviz", False)),
        "mavlink_endpoint": backend_options.get("mavlink_endpoint", "udpin:127.0.0.1:14540"),
        "launch_qgc": bool(backend_options.get("launch_qgc", False)),
        "qgc_path": qgc_path,
        "connect_timeout_s": float(connect_timeout_s),
        "process_start_grace_s": float(backend_options.get("process_start_grace_s", 8.0)),
        "sample_hz": float(scenario.get("update_hz", 5.0)),
        "speed_factor": float(backend_options.get("speed_factor", 1.0)),
        "shell_commands": list(backend_options.get("shell_commands", [])),
        "shell_command_delay_s": float(backend_options.get("shell_command_delay_s", 8.0)),
        "shell_command_interval_s": float(backend_options.get("shell_command_interval_s", 2.0)),
        "success_criteria": backend_options.get("success_criteria", "telemetry"),
        "make_jobs": int(make_jobs),
        "stop_wait_timeout_s": float(backend_options.get("stop_wait_timeout_s", 15.0)),
        "home_lat": backend_options.get("home_lat"),
        "home_lon": backend_options.get("home_lon"),
        "home_alt": backend_options.get("home_alt"),
        "collect_ulog": bool(backend_options.get("collect_ulog", True)),
        "collect_ulog_max_files": int(backend_options.get("collect_ulog_max_files", 3)),
    }


def resolve_sitl_script(px4_dir):
    if not px4_dir:
        return None
    candidate = px4_dir / "Tools" / "simulation" / "gazebo-classic" / "sitl_run.sh"
    return candidate if candidate.is_file() else None


def resolve_gazebo_source_dir(px4_dir):
    if not px4_dir:
        return None
    candidate = px4_dir / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic"
    return candidate if candidate.is_dir() else None


def resolve_world_file(px4_dir, world, explicit_world_file=None):
    if explicit_world_file:
        candidate = Path(explicit_world_file).expanduser()
        return candidate.resolve() if candidate.is_file() else None
    if not px4_dir:
        return None
    candidate = (
        px4_dir / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "worlds" / f"{world}.world"
    )
    return candidate if candidate.is_file() else None


def resolve_model_file(px4_dir, model):
    if not px4_dir:
        return None
    model_dir = px4_dir / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "models" / model
    sdf_candidate = model_dir / f"{model}.sdf"
    if sdf_candidate.is_file():
        return sdf_candidate
    jinja_candidate = model_dir / f"{model}.sdf.jinja"
    return jinja_candidate if jinja_candidate.is_file() else None


def simulation_target_for_model(model):
    if model == "iris":
        return "gazebo-classic"
    return f"gazebo-classic_{model}"


def default_connect_timeout(px4_dir):
    if not px4_dir:
        return 60.0
    px4_binary = px4_dir / "build" / "px4_sitl_default" / "bin" / "px4"
    return 75.0 if px4_binary.is_file() else 300.0


def resolve_gazebo_master_uri(explicit_uri=None):
    if explicit_uri:
        return str(explicit_uri)
    return "http://127.0.0.1:{0}".format(choose_free_local_tcp_port())


def choose_free_local_tcp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        handle.listen(1)
        return int(handle.getsockname()[1])


def ensure_gazebo_classic_build(config, sink):
    command = ["make", config["build_target"], config["simulation_target"]]
    sink.emit_event(
        "info",
        "building px4_gazebo_classic dependencies",
        {"command": " ".join(shlex.quote(part) for part in command), "cwd": str(config["px4_dir"])},
    )
    env = prepare_gazebo_classic_env(config)
    env["DONT_RUN"] = "1"
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
    start_log_threads(process, sink, "gazebo_classic_build")
    return_code = process.wait()
    if return_code != 0:
        raise BackendError("PX4 Gazebo Classic build failed before launch.")
    if not config["px4_binary"] or not config["px4_binary"].is_file():
        raise BackendError("PX4 binary was not produced at the expected path after the Gazebo Classic build.")
    build_gazebo_dir = config["build_dir"] / "build_gazebo-classic" if config["build_dir"] else None
    if build_gazebo_dir is None or not build_gazebo_dir.is_dir():
        raise BackendError("Gazebo Classic plugin build directory was not produced at the expected path.")


def prepare_gazebo_classic_env(config):
    env = os.environ.copy()
    prepend_bin_dirs_to_path(env, config["toolchain_bin_dirs"])
    env["GAZEBO_MASTER_URI"] = str(config["gazebo_master_uri"])
    env["GAZEBO_MODEL_DATABASE_URI"] = ""
    env["PX4_SIM_SPEED_FACTOR"] = str(config["speed_factor"])
    if config["headless"]:
        env["HEADLESS"] = "1"
    else:
        env.pop("HEADLESS", None)
    if config["home_lat"] is not None:
        env["PX4_HOME_LAT"] = str(config["home_lat"])
    if config["home_lon"] is not None:
        env["PX4_HOME_LON"] = str(config["home_lon"])
    if config["home_alt"] is not None:
        env["PX4_HOME_ALT"] = str(config["home_alt"])
    return env


def launch_px4_gazebo_classic(config, sink):
    if not config["sitl_script"]:
        raise BackendError("PX4 Gazebo Classic sitl_run.sh script was not found.")
    if not config["px4_binary"]:
        raise BackendError("PX4 binary path is missing from the Gazebo Classic runtime config.")

    command = [
        str(config["sitl_script"]),
        str(config["px4_binary"]),
        "none",
        config["model"],
        config["world"],
        str(config["px4_dir"]),
        str(config["build_dir"]),
    ]
    sink.emit_event(
        "info",
        "launching px4_gazebo_classic",
        {"command": " ".join(shlex.quote(part) for part in command), "cwd": str(config["px4_dir"])},
    )
    process = subprocess.Popen(
        command,
        cwd=str(config["px4_dir"]),
        env=prepare_gazebo_classic_env(config),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_gazebo_classic_log_threads(process, sink, "px4_gazebo_classic")
    time.sleep(config["process_start_grace_s"])
    if process.poll() is not None:
        raise BackendError("PX4 Gazebo Classic exited before the MAVLink connection phase completed.")
    return process


def stream_gazebo_classic_telemetry(scenario, sink, connection, px4_process, start_wall):
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
            raise BackendError("PX4 Gazebo Classic exited before the configured run duration elapsed.")

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
        "The px4_gazebo_classic backend runs PX4 SITL against Gazebo Classic through PX4's upstream sitl_run.sh wrapper.",
        f"The selected Gazebo Classic world was {config['world']}.",
        "Each px4_gazebo_classic run uses a dedicated local GAZEBO_MASTER_URI so other Gazebo Classic workspaces do not pollute this surface.",
    ]
    if config["headless"]:
        notes.append("Gazebo Classic was requested in headless mode for a lighter scene-backed PX4 probe.")
    else:
        notes.append("Gazebo Classic GUI was requested as the native 3D viewer for this PX4 run.")
    if config["launch_qgc"]:
        notes.append("QGroundControl was requested as an auxiliary flight-state viewer.")
    notes.extend(adapter_notes or [])
    return notes


def build_algorithm_adapter_context(scenario, config):
    return {
        "backend": "px4_gazebo_classic",
        "vehicle": scenario.get("vehicle"),
        "scenario_name": scenario.get("name"),
        "launch_rviz": bool(config.get("launch_rviz", False)),
        "telemetry_endpoint": config["mavlink_endpoint"],
        "preferred_telemetry_port": 14550,
        "system_address": "udp://127.0.0.1:14580",
        "target_altitude_m": float(scenario.get("target_altitude_m", 5.0)),
        "expected_duration_s": float(scenario.get("duration_s", 20.0)),
    }


def start_gazebo_classic_log_threads(process, sink, prefix):
    start_log_threads(process, sink, prefix, event_parser=parse_gazebo_classic_log_event)


def parse_gazebo_classic_log_event(label, stream_name, line):
    transient_preflight_markers = (
        "Preflight Fail: ekf2 missing data",
        "Preflight Fail: system power unavailable",
    )
    harmless_gazebo_markers = (
        "Warning [parser.cc:833] XML Attribute[version] in element[sdf] not defined in SDF, ignoring.",
        "Warning [World.cc:264] Non-unique name[",
        "libcurl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to fuel.gazebosim.org:443",
    )
    if any(marker in line for marker in transient_preflight_markers):
        return {"level": "info", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    if any(marker in line for marker in harmless_gazebo_markers):
        return {"level": "info", "message": "{0} log".format(label), "details": {"line": line, "stream": stream_name}}
    return parse_px4_log_event(label, stream_name, line)
