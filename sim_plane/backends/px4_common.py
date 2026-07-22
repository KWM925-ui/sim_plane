import math
import os
import subprocess
import time
from pathlib import Path

from pymavlink import mavutil

from sim_plane.backends.base import BackendError
from sim_plane.processes import start_log_threads


QGC_CANDIDATES = [
    Path("/home/coco/桌面/QGroundControl.AppImage"),
    Path("/home/coco/Desktop/QGroundControl.AppImage"),
    Path("/home/coco/QGroundControl.AppImage"),
    Path("/home/nv/QGroundControl.AppImage"),
]

PX4_CANDIDATES = [
    Path("/home/coco/sim_plane_ws/src/core/PX4-Autopilot"),
]


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


def ensure_executable(path):
    mode = path.stat().st_mode
    if not mode & 0o111:
        path.chmod(mode | 0o111)


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


def wait_for_heartbeat(connection, timeout_s):
    heartbeat = connection.wait_heartbeat(timeout=timeout_s)
    if heartbeat is None:
        raise BackendError("Timed out waiting for a PX4 MAVLink heartbeat on the configured endpoint.")
    return heartbeat


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
    start_log_threads(process, sink, prefix, event_parser=parse_px4_log_event)


def parse_px4_log_event(label, stream_name, line):
    markers = ["ERROR", "WARN", "Ready", "Startup", "MAVLink", "ERROR ["]
    if not any(marker in line for marker in markers):
        return None
    transient_preflight_markers = (
        "Preflight Fail: heading estimate invalid",
        "Preflight Fail: height estimate not stable",
    )
    if any(marker in line for marker in transient_preflight_markers):
        return {
            "level": "info",
            "message": "{0} log".format(label),
            "details": {"line": line, "stream": stream_name},
        }
    level = "warning" if ("WARN" in line or "ERROR" in line or "[e]" in line.lower()) else "info"
    return {
        "level": level,
        "message": "{0} log".format(label),
        "details": {"line": line, "stream": stream_name},
    }
