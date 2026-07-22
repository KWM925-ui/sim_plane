import math
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
    evaluate_run_status,
    infer_phase,
    initial_state,
    launch_qgc,
    maybe_send_shell_commands,
    prepend_bin_dirs_to_path,
    resolve_px4_dir,
    resolve_qgc_path,
    resolve_toolchain_root,
    start_px4_log_threads,
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
    "quadrotor": "quadrotor_x",
    "multirotor": "quadrotor_x",
    "fixedwing": "rascal",
    "airplane": "rascal",
}

JSBSIM_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/toolchains/jsbsim"),
    Path("/home/coco/jsbsim"),
    Path("/usr/local"),
    Path("/usr"),
]

FLIGHTGEAR_BINARY_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/toolchains/flightgear/bin/fgfs"),
    Path("/usr/games/fgfs"),
    Path("/usr/bin/fgfs"),
]


class PX4JSBSimBackend(Backend):
    name = "px4_jsbsim"

    def validate_environment(self, scenario=None):
        config = build_runtime_config(scenario or {})
        issues = []
        if not config["px4_dir"]:
            issues.append(
                "PX4-Autopilot checkout not found. Set PX4_AUTOPILOT_DIR, pass --px4-dir, "
                "or place the repo in a common path such as /home/coco/sim_plane_ws/src/core/PX4-Autopilot."
            )
        if not config["jsbsim_root_dir"]:
            issues.append(
                "Local JSBSim toolchain not found. Set JSBSIM_ROOT_DIR, pass backend_options.jsbsim_root_dir, "
                "or place the extracted toolchain under /home/coco/sim_plane_ws/toolchains/jsbsim."
            )
        if not config["sitl_script"]:
            issues.append("PX4 JSBSim sitl_run.sh script was not found under the PX4 checkout.")
        if (
            config["px4_dir"]
            and config["build_dir"]
            and config["build_dir"].is_dir()
            and config["px4_binary"]
            and not config["px4_binary"].is_file()
        ):
            issues.append(
                "PX4 JSBSim binary is missing at {0}. Run this backend once to build it, or build "
                "`px4_sitl_default` manually before relying on doctor/list-backends readiness.".format(
                    config["px4_binary"]
                )
            )
        if (
            config["px4_dir"]
            and config["build_dir"]
            and config["build_dir"].is_dir()
            and config["jsbsim_bridge_binary"]
            and not config["jsbsim_bridge_binary"].is_file()
        ):
            issues.append(
                "PX4 JSBSim bridge binary is missing at {0}. Run this backend once to configure/build "
                "`jsbsim_bridge`, or rebuild PX4 SITL with JSBSIM_ROOT_DIR set.".format(
                    config["jsbsim_bridge_binary"]
                )
            )
        if config["build_dir"] and config["build_dir"].is_dir() and cmake_cache_needs_jsbsim_reconfigure(config):
            issues.append(
                "PX4 JSBSim CMake cache did not discover JSBSim. Reconfigure with JSBSIM_ROOT_DIR={0} before "
                "treating px4_jsbsim as ready.".format(config["jsbsim_root_dir"])
            )
        if config["px4_dir"] and (not config["build_dir"] or not config["build_dir"].is_dir()):
            issues.append(
                "PX4 JSBSim build directory was not found at {0}. Run the PX4 SITL configure/build step first, "
                "for example `make px4_sitl_default`, before running this backend.".format(config["build_dir"])
            )
        if not config["scene_file"]:
            issues.append(
                "PX4 JSBSim bridge scene XML was not found for the requested world. "
                "Use a world with a matching scene/<WORLD>.xml file under the PX4 checkout."
            )
        if config["launch_qgc"] and not config["qgc_path"]:
            issues.append(
                "QGroundControl launch requested but AppImage was not found. "
                "Set QGROUNDCONTROL_PATH or place QGroundControl.AppImage in a common path."
            )
        if not config["headless"] and not config["flightgear_binary"]:
            issues.append(
                "FlightGear viewer launch requested for JSBSim, but no fgfs binary was found. "
                "Run ./scripts/build_flightgear_toolchain.sh or set FG_BINARY."
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
        if not config["jsbsim_root_dir"]:
            raise BackendError(
                "Local JSBSim toolchain not found. Export JSBSIM_ROOT_DIR or place it under /home/coco/sim_plane_ws/toolchains/jsbsim."
            )
        if not config["sitl_script"]:
            raise BackendError("PX4 JSBSim sitl_run.sh script was not found under the selected PX4 checkout.")
        if not config["build_dir"] or not config["build_dir"].is_dir():
            raise BackendError(
                "PX4 JSBSim build directory was not found at {0}. Run `make px4_sitl_default` in the PX4 checkout first.".format(
                    config["build_dir"]
                )
            )
        if not config["scene_file"]:
            raise BackendError(
                "PX4 JSBSim bridge scene XML was not found for the requested world under "
                "Tools/simulation/jsbsim/jsbsim_bridge/scene."
            )

        sink.emit_event(
            "info",
            "px4_jsbsim launch plan",
            {
                "px4_dir": str(config["px4_dir"]),
                "jsbsim_root_dir": str(config["jsbsim_root_dir"]),
                "model": config["model"],
                "world": config["world"],
                "scene_file": str(config["scene_file"]) if config["scene_file"] else None,
                "build_target": config["build_target"],
                "mavlink_endpoint": config["mavlink_endpoint"],
                "headless": config["headless"],
                "launch_qgc": config["launch_qgc"],
                "flightgear_binary": str(config["flightgear_binary"]) if config["flightgear_binary"] else None,
            },
        )

        sitl_process = None
        viewer_processes = []
        connection = None
        adapter_handle = None
        adapter_collected = False
        result = None
        ulog_before = snapshot_px4_ulog_files(config)
        try:
            ensure_jsbsim_build(config, sink)
            sitl_process = launch_px4_jsbsim(config, sink, artifact_dir=sink.artifact_writer.artifact_dir)
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
            telemetry_summary = stream_jsbsim_telemetry(
                scenario=scenario,
                sink=sink,
                connection=connection,
                px4_process=sitl_process,
                start_wall=telemetry_start_wall,
            )
            adapter_report = collect_algorithm_adapter(
                adapter_handle,
                timeout_s=float((scenario.get("algorithm_adapter") or {}).get("join_timeout_s", 3.0)),
                request_stop=adapter_handle is not None,
            )
            adapter_collected = True
            telemetry_summary.update(adapter_report["metrics"])
            telemetry_summary["headless"] = config["headless"]
            telemetry_summary["launch_qgc"] = config["launch_qgc"]
            telemetry_summary["flightgear_viewer"] = not config["headless"]
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
            if adapter_handle is not None and not adapter_collected:
                collect_algorithm_adapter(
                    adapter_handle,
                    timeout_s=float((scenario.get("algorithm_adapter") or {}).get("join_timeout_s", 3.0)),
                    request_stop=True,
                )
            for process in reversed(viewer_processes):
                terminate_process(process, sink, "viewer")
            terminate_process(sitl_process, sink, "px4_jsbsim")
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
    jsbsim_root_dir = resolve_jsbsim_root(backend_options.get("jsbsim_root_dir"), toolchain_root)
    build_target = backend_options.get("build_target", "px4_sitl_default")
    build_dir = px4_dir / "build" / build_target if px4_dir else None
    model = backend_options.get("model") or MODEL_BY_VEHICLE.get(scenario.get("vehicle"), "quadrotor_x")
    world = backend_options.get("world", "LSZH")
    qgc_path = resolve_qgc_path(backend_options.get("qgc_path"))
    flightgear_binary = resolve_flightgear_binary(backend_options.get("flightgear_binary"))
    sitl_script = resolve_sitl_script(px4_dir)
    scene_file = resolve_scene_file(px4_dir, world)
    headless = backend_options.get("headless")
    if headless is None:
        headless = True
    connect_timeout_s = backend_options.get("connect_timeout_s")
    if connect_timeout_s is None:
        connect_timeout_s = default_connect_timeout(build_dir)
    build_jobs = backend_options.get("build_jobs")
    if build_jobs is None:
        build_jobs = min(max(os.cpu_count() or 1, 1), 4)
    return {
        "px4_dir": px4_dir,
        "toolchain_root": toolchain_root,
        "toolchain_bin_dirs": toolchain_bin_dirs,
        "jsbsim_root_dir": jsbsim_root_dir,
        "build_target": build_target,
        "build_dir": build_dir,
        "px4_binary": build_dir / "bin" / "px4" if build_dir else None,
        "jsbsim_bridge_binary": build_dir / "build_jsbsim_bridge" / "jsbsim_bridge" if build_dir else None,
        "sitl_script": sitl_script,
        "model": model,
        "world": world,
        "scene_file": scene_file,
        "mavlink_endpoint": backend_options.get("mavlink_endpoint", "udpin:127.0.0.1:14540"),
        "launch_qgc": bool(backend_options.get("launch_qgc", False)),
        "qgc_path": qgc_path,
        "flightgear_binary": flightgear_binary,
        "headless": bool(headless),
        "connect_timeout_s": float(connect_timeout_s),
        "process_start_grace_s": float(backend_options.get("process_start_grace_s", 2.0)),
        "sample_hz": float(scenario.get("update_hz", 5.0)),
        "speed_factor": float(backend_options.get("speed_factor", 1.0)),
        "shell_commands": list(backend_options.get("shell_commands", [])),
        "shell_command_delay_s": float(backend_options.get("shell_command_delay_s", 2.0)),
        "shell_command_interval_s": float(backend_options.get("shell_command_interval_s", 0.5)),
        "success_criteria": backend_options.get("success_criteria", "telemetry"),
        "build_jobs": int(build_jobs),
        "collect_ulog": bool(backend_options.get("collect_ulog", True)),
        "collect_ulog_max_files": int(backend_options.get("collect_ulog_max_files", 3)),
    }


def resolve_jsbsim_root(explicit_path=None, toolchain_root=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.environ.get("JSBSIM_ROOT_DIR")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    if toolchain_root:
        candidates.append(toolchain_root / "jsbsim")
    candidates.extend(JSBSIM_CANDIDATES)

    for candidate in candidates:
        if is_jsbsim_root(candidate):
            return candidate.resolve()
    return None


def is_jsbsim_root(path):
    candidate = Path(path)
    lib_dir = candidate / "lib"
    return (
        candidate.is_dir()
        and (candidate / "include" / "JSBSim" / "FGFDMExec.h").is_file()
        and (candidate / "bin" / "JSBSim").is_file()
        and any((lib_dir / name).is_file() for name in ("libJSBSim.so", "libJSBSim.a"))
    )


def resolve_sitl_script(px4_dir):
    if not px4_dir:
        return None
    candidate = px4_dir / "Tools" / "simulation" / "jsbsim" / "sitl_run.sh"
    return candidate if candidate.is_file() else None


def resolve_scene_file(px4_dir, world):
    if not px4_dir:
        return None
    candidate = px4_dir / "Tools" / "simulation" / "jsbsim" / "jsbsim_bridge" / "scene" / f"{world}.xml"
    return candidate if candidate.is_file() else None


def resolve_flightgear_binary(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.environ.get("FG_BINARY")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(FLIGHTGEAR_BINARY_CANDIDATES)

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def default_connect_timeout(build_dir):
    if build_dir is None:
        return 25.0
    px4_binary = build_dir / "bin" / "px4"
    jsbsim_bridge_binary = build_dir / "build_jsbsim_bridge" / "jsbsim_bridge"
    return 45.0 if px4_binary.is_file() and jsbsim_bridge_binary.is_file() else 240.0


def ensure_jsbsim_build(config, sink):
    if config["build_dir"] is None:
        raise BackendError("PX4 build directory could not be derived from the selected checkout.")

    if (
        not config["px4_binary"]
        or not config["px4_binary"].is_file()
        or not config["jsbsim_bridge_binary"]
        or not config["jsbsim_bridge_binary"].is_file()
        or cmake_cache_needs_jsbsim_reconfigure(config)
    ):
        configure_px4_jsbsim_build(config, sink)

    command = [
        "cmake",
        "--build",
        str(config["build_dir"]),
        "--target",
        "px4",
        "jsbsim_bridge",
        "-j{0}".format(config["build_jobs"]),
    ]
    run_jsbsim_build_command(
        command,
        cwd=config["px4_dir"],
        env=prepare_jsbsim_env(config),
        sink=sink,
        label="px4_jsbsim_build",
        failure_message="PX4 JSBSim build failed before launch.",
    )

    if not config["px4_binary"] or not config["px4_binary"].is_file():
        raise BackendError("PX4 binary was not produced at the expected path after the JSBSim build.")
    if not config["jsbsim_bridge_binary"] or not config["jsbsim_bridge_binary"].is_file():
        raise BackendError("jsbsim_bridge binary was not produced at the expected path after the JSBSim build.")


def configure_px4_jsbsim_build(config, sink):
    if not config["jsbsim_root_dir"]:
        raise BackendError("Local JSBSim toolchain not found; cannot configure PX4 JSBSim target.")
    command = [
        "cmake",
        "-S",
        str(config["px4_dir"]),
        "-B",
        str(config["build_dir"]),
        "-DCONFIG={0}".format(config["build_target"]),
        "-DJSBSIM_ROOT_DIR={0}".format(config["jsbsim_root_dir"]),
    ]
    run_jsbsim_build_command(
        command,
        cwd=config["px4_dir"],
        env=prepare_jsbsim_env(config),
        sink=sink,
        label="px4_jsbsim_configure",
        failure_message="PX4 JSBSim configure failed before launch.",
    )


def cmake_cache_needs_jsbsim_reconfigure(config):
    build_dir = config.get("build_dir")
    if not build_dir:
        return False
    cache_path = Path(build_dir) / "CMakeCache.txt"
    if not cache_path.is_file():
        return True
    try:
        cache_text = cache_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True
    return "JSBSIM_INCLUDE_DIR:PATH=JSBSIM_INCLUDE_DIR-NOTFOUND" in cache_text


def run_jsbsim_build_command(command, cwd, env, sink, label, failure_message):
    sink.emit_event(
        "info",
        label.replace("_", " "),
        {"command": " ".join(shlex.quote(part) for part in command), "cwd": str(cwd)},
    )
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_log_threads(process, sink, label)
    return_code = process.wait()
    if return_code != 0:
        raise BackendError(failure_message)


def prepare_jsbsim_env(config, artifact_dir=None):
    env = os.environ.copy()
    prepend_bin_dirs_to_path(env, config["toolchain_bin_dirs"])
    if config["flightgear_binary"]:
        flightgear_dir = str(config["flightgear_binary"].parent)
        current_path = env.get("PATH", "")
        env["PATH"] = flightgear_dir if not current_path else flightgear_dir + os.pathsep + current_path
        env["FG_BINARY"] = str(config["flightgear_binary"])
    if artifact_dir is not None and not config["headless"]:
        fg_home = Path(artifact_dir).resolve() / "flightgear_home"
        fg_home.mkdir(parents=True, exist_ok=True)
        env["FG_HOME"] = str(fg_home)
    env["PX4_SIM_SPEED_FACTOR"] = str(config["speed_factor"])
    env["JSBSIM_ROOT_DIR"] = str(config["jsbsim_root_dir"])
    lib_dir = config["jsbsim_root_dir"] / "lib"
    ld_library_path = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = str(lib_dir) if not ld_library_path else str(lib_dir) + os.pathsep + ld_library_path
    if config["headless"]:
        env["HEADLESS"] = "1"
    else:
        env.pop("HEADLESS", None)
    return env


def launch_px4_jsbsim(config, sink, artifact_dir=None):
    if not config["sitl_script"]:
        raise BackendError("PX4 JSBSim sitl_run.sh script was not found.")
    if not config["px4_binary"]:
        raise BackendError("PX4 binary path is missing from the JSBSim runtime config.")

    command = [
        str(config["sitl_script"]),
        str(config["px4_binary"]),
        config["model"],
        config["world"],
        str(config["px4_dir"]),
        str(config["build_dir"]),
    ]
    sink.emit_event(
        "info",
        "launching px4_jsbsim",
        {"command": " ".join(shlex.quote(part) for part in command), "cwd": str(config["px4_dir"])},
    )
    process = subprocess.Popen(
        command,
        cwd=str(config["px4_dir"]),
        env=prepare_jsbsim_env(config, artifact_dir=artifact_dir),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        preexec_fn=os.setsid,
    )
    start_px4_log_threads(process, sink, "px4_jsbsim")
    time.sleep(config["process_start_grace_s"])
    if process.poll() is not None:
        raise BackendError("PX4 JSBSim exited before the MAVLink connection phase completed.")
    return process


def stream_jsbsim_telemetry(scenario, sink, connection, px4_process, start_wall):
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
            raise BackendError("PX4 JSBSim exited before the configured run duration elapsed.")

        message = connection.recv_match(blocking=True, timeout=0.2)
        if message is not None:
            mavlink_count += 1
            update_jsbsim_state_from_message(state, message)
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


def update_jsbsim_state_from_message(state, message):
    msg_type = message.get_type()
    if msg_type == "BAD_DATA":
        return
    if msg_type == "HEARTBEAT":
        state["armed"] = bool(message.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        state["mode"] = mavutil.mode_string_v10(message)
        return
    if msg_type == "LOCAL_POSITION_NED":
        state["x_m"] = getattr(message, "x", state["x_m"])
        state["y_m"] = getattr(message, "y", state["y_m"])
        state["z_m"] = getattr(message, "z", state["z_m"])
        state["local_altitude_m"] = max(0.0, -float(state["z_m"]))
        vx = float(getattr(message, "vx", 0.0))
        vy = float(getattr(message, "vy", 0.0))
        vz = float(getattr(message, "vz", 0.0))
        state["speed_mps"] = math.sqrt(vx * vx + vy * vy + vz * vz)
        state["altitude_m"] = max(state.get("local_altitude_m", 0.0), state.get("global_relative_altitude_m", 0.0))
        return
    if msg_type == "GLOBAL_POSITION_INT":
        relative_alt = getattr(message, "relative_alt", None)
        if relative_alt is not None:
            state["global_relative_altitude_m"] = max(0.0, float(relative_alt) / 1000.0)
            state["altitude_m"] = max(state.get("local_altitude_m", 0.0), state["global_relative_altitude_m"])
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
        if hasattr(message, "heading"):
            state["heading_deg"] = float(message.heading)
        return
    if msg_type == "SYS_STATUS":
        battery_remaining = getattr(message, "battery_remaining", None)
        if battery_remaining is not None and battery_remaining >= 0:
            state["battery_pct"] = float(battery_remaining)


def build_notes(config, adapter_notes=None):
    notes = [
        "The px4_jsbsim backend runs PX4 SITL against the local JSBSim dynamics bridge via sitl_run.sh.",
    ]
    if config["headless"]:
        notes.append("This JSBSim path is validated in headless mode and in FlightGear visual mode; this run used the lighter headless path.")
    else:
        notes.append("FlightGear was requested as the 3D viewer for this JSBSim run.")
    if config["launch_qgc"]:
        notes.append("QGroundControl was requested as an auxiliary flight-state viewer.")
    notes.extend(adapter_notes or [])
    return notes


def build_algorithm_adapter_context(scenario, config):
    return {
        "backend": "px4_jsbsim",
        "vehicle": scenario.get("vehicle"),
        "scenario_name": scenario.get("name"),
        "telemetry_endpoint": config["mavlink_endpoint"],
        "preferred_telemetry_port": 14550,
        "system_address": "udp://127.0.0.1:14580",
        "target_altitude_m": float(scenario.get("target_altitude_m", 5.0)),
        "expected_duration_s": float(scenario.get("duration_s", 20.0)),
    }
