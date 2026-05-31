import math
import random
import time

from sim_plane.adapters import collect_algorithm_adapter, has_algorithm_adapter, start_algorithm_adapter, validate_algorithm_adapter
from sim_plane.backends.base import Backend


class DemoBackend(Backend):
    name = "demo"

    def validate_environment(self, scenario=None):
        if has_algorithm_adapter((scenario or {}).get("algorithm_adapter")):
            return validate_algorithm_adapter(
                (scenario or {}).get("algorithm_adapter"),
                context=build_algorithm_adapter_context(scenario or {}),
            )
        return []

    def run(self, scenario, sink):
        update_hz = float(scenario["update_hz"])
        dt = 1.0 / update_hz
        duration_s = float(scenario["duration_s"])
        target_altitude_m = float(scenario["target_altitude_m"])
        realtime_factor = max(float(scenario.get("realtime_factor", 4.0)), 0.0)
        waypoints = scenario.get("waypoints", [])
        disturbance_config = build_disturbance_config(scenario.get("disturbances", {}))
        degradation_config = build_degradation_config(scenario.get("degradations", {}))
        random_source = random.Random(disturbance_config["seed"])
        degradation_random_source = random.Random(degradation_config["seed"])
        latency_buffer = []

        sink.emit_event(
            "info",
            "demo backend booted",
            {
                "backend": self.name,
                "disturbances": disturbance_config["summary"],
                "degradations": degradation_config["summary"],
            },
        )
        adapter_handle = None
        adapter_report = {"metrics": {}, "notes": []}
        if has_algorithm_adapter(scenario.get("algorithm_adapter")):
            adapter_handle = start_algorithm_adapter(
                scenario.get("algorithm_adapter"),
                sink,
                context=build_algorithm_adapter_context(scenario),
            )

        telemetry_count = 0
        max_altitude_m = 0.0
        max_speed_mps = 0.0
        max_horizontal_error_m = 0.0
        max_altitude_error_m = 0.0
        reached_target_altitude = False
        mode = "INIT"
        phase = "boot"
        held_truth = None

        mission_start_t = 5.0
        mission_end_t = max(mission_start_t + 1.0, duration_s - 4.0)

        current_wp = 0
        prev_phase = None

        t = 0.0
        while t <= duration_s + 1e-9:
            if t < 2.0:
                phase = "boot"
                mode = "INIT"
                armed = False
                x = disturbance_config["initial_offset"]["x_m"]
                y = disturbance_config["initial_offset"]["y_m"]
                altitude = 0.0
            elif t < 3.0:
                phase = "arm"
                mode = "STANDBY"
                armed = True
                x = disturbance_config["initial_offset"]["x_m"]
                y = disturbance_config["initial_offset"]["y_m"]
                altitude = 0.0
            elif t < mission_start_t:
                phase = "takeoff"
                mode = "TAKEOFF"
                armed = True
                climb_progress = (t - 3.0) / max(mission_start_t - 3.0, 1e-6)
                altitude = target_altitude_m * min(max(climb_progress, 0.0), 1.0)
                x = disturbance_config["initial_offset"]["x_m"]
                y = disturbance_config["initial_offset"]["y_m"]
            elif t < mission_end_t:
                phase = "mission"
                mode = "OFFBOARD"
                armed = True
                altitude = target_altitude_m
                x, y, current_wp = interpolate_path(
                    t,
                    mission_start_t,
                    mission_end_t,
                    waypoints,
                    current_wp,
                )
            else:
                phase = "land"
                mode = "LAND"
                armed = True
                landing_progress = (t - mission_end_t) / max(duration_s - mission_end_t, 1e-6)
                altitude = target_altitude_m * max(0.0, 1.0 - landing_progress)
                x = disturbance_config["initial_offset"]["x_m"]
                y = disturbance_config["initial_offset"]["y_m"]

            truth = {
                "x_m": x,
                "y_m": y,
                "z_m": -altitude,
            }
            speed_mps = compute_speed(phase, target_altitude_m, duration_s)
            control_active = not is_in_dropout_window(
                t,
                degradation_config["communication_interruption"]["windows"],
            )
            if not control_active:
                degradation_config["communication_interruption_count"] += 1
                if held_truth is not None:
                    truth = dict(held_truth)
                    x = truth["x_m"]
                    y = truth["y_m"]
                    altitude = -truth["z_m"]
                speed_mps = 0.0
                mode = "HOLD"
            else:
                held_truth = dict(truth)

            control_saturated = False
            max_control_speed = degradation_config["control_saturation"]["max_speed_mps"]
            if max_control_speed is not None and speed_mps > max_control_speed:
                speed_mps = max_control_speed
                control_saturated = True
                degradation_config["control_saturation_count"] += 1

            heading_deg = (math.degrees(math.atan2(y + 1e-6, x + 1e-6)) + 360.0) % 360.0
            measured = apply_disturbances(
                truth=truth,
                t=t,
                disturbance_config=disturbance_config,
                random_source=random_source,
            )
            measured = apply_degradations(
                measured=measured,
                t=t,
                degradation_config=degradation_config,
                random_source=degradation_random_source,
                latency_buffer=latency_buffer,
                dt=dt,
            )
            speed_mps = apply_speed_degradations(
                speed_mps=speed_mps,
                t=t,
                degradation_config=degradation_config,
                random_source=degradation_random_source,
            )
            sample_visible = measured is not None
            if measured is None:
                horizontal_error_m = None
                altitude_error_m = None
            else:
                horizontal_error_m = math.hypot(measured["x_m"] - truth["x_m"], measured["y_m"] - truth["y_m"])
                altitude_error_m = abs((-measured["z_m"]) - altitude)
            battery_pct = max(18.0, 100.0 - (t / max(duration_s, 1e-6)) * 62.0)
            max_altitude_m = max(max_altitude_m, altitude)
            max_speed_mps = max(max_speed_mps, speed_mps)
            if horizontal_error_m is not None:
                max_horizontal_error_m = max(max_horizontal_error_m, horizontal_error_m)
            if altitude_error_m is not None:
                max_altitude_error_m = max(max_altitude_error_m, altitude_error_m)
            reached_target_altitude = reached_target_altitude or altitude >= target_altitude_m * 0.95

            if phase != prev_phase:
                sink.emit_event("info", "phase transition", {"phase": phase, "t": round(t, 2)})
                prev_phase = phase

            sample = {
                "t": round(t, 3),
                "phase": phase,
                "mode": mode,
                "armed": armed,
                "position": build_sample_position(measured),
                "truth_position": {
                    "x_m": round(truth["x_m"], 3),
                    "y_m": round(truth["y_m"], 3),
                    "z_m": round(truth["z_m"], 3),
                },
                "altitude_m": round(altitude, 3),
                "speed_mps": round(speed_mps, 3),
                "battery_pct": round(battery_pct, 2),
                "heading_deg": round(heading_deg, 2),
                "sensor_visible": sample_visible,
                "control_active": control_active,
                "control_saturated": control_saturated,
            }
            sink.emit_telemetry(sample)
            telemetry_count += 1

            if realtime_factor > 0.0:
                time.sleep(dt / realtime_factor)
            t += dt

        sink.emit_event("info", "demo backend finished", {"backend": self.name})
        if adapter_handle is not None:
            adapter_report = collect_algorithm_adapter(
                adapter_handle,
                timeout_s=float((scenario.get("algorithm_adapter") or {}).get("join_timeout_s", 3.0)),
                request_stop=True,
            )

        adapter_success = (
            adapter_handle is None
            or adapter_report.get("metrics", {}).get("algorithm_adapter_completed_successfully") is True
        )
        verdict = "passed" if reached_target_altitude and adapter_success else "failed"
        metrics = {
            "telemetry_count": telemetry_count,
            "max_altitude_m": round(max_altitude_m, 3),
            "max_speed_mps": round(max_speed_mps, 3),
            "max_horizontal_error_m": round(max_horizontal_error_m, 3),
            "max_altitude_error_m": round(max_altitude_error_m, 3),
            "target_altitude_reached": reached_target_altitude,
            "duration_s": duration_s,
            "disturbance_enabled": disturbance_config["enabled"],
            "degradation_enabled": degradation_config["enabled"],
            "sensor_dropout_count": degradation_config["dropout_count"],
            "target_loss_count": degradation_config["target_loss_count"],
            "sensor_latency_s": degradation_config["latency_s"],
            "sensor_noise_enabled": degradation_config["sensor_noise"]["position_std_m"] > 0.0
            or degradation_config["sensor_noise"]["altitude_std_m"] > 0.0,
            "communication_interruption_count": degradation_config["communication_interruption_count"],
            "control_saturation_count": degradation_config["control_saturation_count"],
            "sensor_stream_fault_enabled": degradation_config["sensor_stream_fault_enabled"],
            "gps_dropout_count": degradation_config["gps_dropout_count"],
            "vio_scale_drift_count": degradation_config["vio_scale_drift_count"],
            "vio_scale_drift_max_scale_error": round(degradation_config["vio_scale_drift_max_scale_error"], 6),
            "imu_noise_burst_count": degradation_config["imu_noise_burst_count"],
        }
        metrics.update(adapter_report.get("metrics", {}))
        notes = [
            "This is the built-in demo backend.",
            "It validates the platform loop, artifact flow, and visualization without requiring PX4 to be installed yet.",
        ]
        notes.extend(adapter_report.get("notes", []))
        return {
            "status": verdict,
            "backend": self.name,
            "vehicle": scenario["vehicle"],
            "scenario_name": scenario["name"],
            "metrics": metrics,
            "notes": notes,
        }


def build_algorithm_adapter_context(scenario):
    return {
        "backend": "demo",
        "vehicle": (scenario or {}).get("vehicle", "quadrotor"),
        "scenario_name": (scenario or {}).get("name", "demo"),
        "target_altitude_m": (scenario or {}).get("target_altitude_m"),
        "expected_duration_s": (scenario or {}).get("duration_s"),
    }


def compute_speed(phase, target_altitude_m, duration_s):
    if phase == "takeoff":
        return max(1.5, target_altitude_m / max(duration_s, 1.0) * 4.0)
    if phase == "mission":
        return 6.0
    if phase == "land":
        return 2.0
    return 0.4


def build_sample_position(measured):
    if measured is None:
        return None
    return {
        "x_m": round(measured["x_m"], 3),
        "y_m": round(measured["y_m"], 3),
        "z_m": round(measured["z_m"], 3),
    }


def interpolate_path(t, start_t, end_t, waypoints, current_wp):
    if len(waypoints) < 2:
        return 0.0, 0.0, 0

    normalized = (t - start_t) / max(end_t - start_t, 1e-6)
    normalized = min(max(normalized, 0.0), 0.999999)
    segment_count = len(waypoints) - 1
    scaled = normalized * segment_count
    index = min(int(scaled), segment_count - 1)
    local = scaled - index
    start = waypoints[index]
    end = waypoints[index + 1]
    x = start["x"] + (end["x"] - start["x"]) * local
    y = start["y"] + (end["y"] - start["y"]) * local
    return x, y, index


def build_disturbance_config(raw_config):
    config = dict(raw_config or {})
    wind = dict(config.get("wind") or {})
    noise = dict(config.get("measurement_noise") or {})
    initial_offset = dict(config.get("initial_offset") or {})
    seed = int(config.get("seed", 0))
    normalized = {
        "seed": seed,
        "wind": {
            "x_mps": float(wind.get("x_mps", 0.0)),
            "y_mps": float(wind.get("y_mps", 0.0)),
            "z_mps": float(wind.get("z_mps", 0.0)),
        },
        "measurement_noise": {
            "position_std_m": float(noise.get("position_std_m", 0.0)),
            "altitude_std_m": float(noise.get("altitude_std_m", 0.0)),
        },
        "initial_offset": {
            "x_m": float(initial_offset.get("x_m", 0.0)),
            "y_m": float(initial_offset.get("y_m", 0.0)),
            "z_m": float(initial_offset.get("z_m", 0.0)),
        },
    }
    normalized["enabled"] = any(
        abs(value) > 1e-12
        for group in ("wind", "measurement_noise", "initial_offset")
        for value in normalized[group].values()
    )
    normalized["summary"] = {
        "enabled": normalized["enabled"],
        "seed": seed,
        "wind": normalized["wind"],
        "measurement_noise": normalized["measurement_noise"],
        "initial_offset": normalized["initial_offset"],
    }
    return normalized


def build_degradation_config(raw_config):
    config = dict(raw_config or {})
    dropout = dict(config.get("sensor_dropout") or {})
    target_loss = dict(config.get("target_loss") or {})
    noise = dict(config.get("sensor_noise") or {})
    bias = dict(config.get("measurement_bias") or {})
    bias_drift = dict(config.get("measurement_bias_drift") or {})
    saturation = dict(config.get("measurement_saturation") or {})
    latency = dict(config.get("sensor_latency") or {})
    communication = dict(config.get("communication_interruption") or {})
    control_saturation = dict(config.get("control_saturation") or {})
    stream_faults = dict(config.get("sensor_stream_faults") or {})
    gps_dropout = dict(stream_faults.get("gps_dropout") or {})
    vio_scale_drift = dict(stream_faults.get("vio_scale_drift") or {})
    imu_noise_burst = dict(stream_faults.get("imu_noise_burst") or {})
    seed = int(config.get("seed", 0))
    dropout_windows = normalize_dropout_windows(dropout.get("windows", []))
    target_loss_windows = normalize_dropout_windows(target_loss.get("windows", []))
    communication_windows = normalize_dropout_windows(communication.get("windows", []))
    gps_dropout_windows = normalize_dropout_windows(gps_dropout.get("windows", []))
    imu_noise_burst_windows = normalize_dropout_windows(imu_noise_burst.get("windows", []))
    normalized = {
        "seed": seed,
        "sensor_dropout": {
            "probability": clamp(float(dropout.get("probability", 0.0)), 0.0, 1.0),
            "windows": dropout_windows,
        },
        "target_loss": {
            "windows": target_loss_windows,
        },
        "sensor_noise": {
            "position_std_m": float(noise.get("position_std_m", 0.0)),
            "altitude_std_m": float(noise.get("altitude_std_m", 0.0)),
        },
        "measurement_bias": {
            "x_m": float(bias.get("x_m", 0.0)),
            "y_m": float(bias.get("y_m", 0.0)),
            "z_m": float(bias.get("z_m", 0.0)),
        },
        "measurement_bias_drift": {
            "x_mps": float(bias_drift.get("x_mps", 0.0)),
            "y_mps": float(bias_drift.get("y_mps", 0.0)),
            "z_mps": float(bias_drift.get("z_mps", 0.0)),
        },
        "measurement_saturation": {
            "max_horizontal_range_m": optional_float(saturation.get("max_horizontal_range_m")),
            "min_altitude_m": optional_float(saturation.get("min_altitude_m")),
            "max_altitude_m": optional_float(saturation.get("max_altitude_m")),
        },
        "sensor_latency": {
            "delay_s": max(float(latency.get("delay_s", 0.0)), 0.0),
        },
        "communication_interruption": {
            "windows": communication_windows,
        },
        "control_saturation": {
            "max_speed_mps": optional_float(control_saturation.get("max_speed_mps")),
        },
        "sensor_stream_faults": {
            "gps_dropout": {
                "probability": clamp(float(gps_dropout.get("probability", 0.0)), 0.0, 1.0),
                "windows": gps_dropout_windows,
            },
            "vio_scale_drift": {
                "start_s": max(float(vio_scale_drift.get("start_s", 0.0)), 0.0),
                "scale_rate_per_s": float(vio_scale_drift.get("scale_rate_per_s", 0.0)),
                "max_scale_error": max(float(vio_scale_drift.get("max_scale_error", 0.0)), 0.0),
            },
            "imu_noise_burst": {
                "windows": imu_noise_burst_windows,
                "position_std_m": float(imu_noise_burst.get("position_std_m", 0.0)),
                "altitude_std_m": float(imu_noise_burst.get("altitude_std_m", 0.0)),
                "speed_std_mps": float(imu_noise_burst.get("speed_std_mps", 0.0)),
            },
        },
    }
    stream = normalized["sensor_stream_faults"]
    normalized["enabled"] = (
        normalized["sensor_dropout"]["probability"] > 0.0
        or bool(normalized["sensor_dropout"]["windows"])
        or bool(normalized["target_loss"]["windows"])
        or any(abs(value) > 1e-12 for value in normalized["sensor_noise"].values())
        or any(abs(value) > 1e-12 for value in normalized["measurement_bias"].values())
        or any(abs(value) > 1e-12 for value in normalized["measurement_bias_drift"].values())
        or normalized["sensor_latency"]["delay_s"] > 0.0
        or any(value is not None for value in normalized["measurement_saturation"].values())
        or bool(normalized["communication_interruption"]["windows"])
        or normalized["control_saturation"]["max_speed_mps"] is not None
        or stream["gps_dropout"]["probability"] > 0.0
        or bool(stream["gps_dropout"]["windows"])
        or abs(stream["vio_scale_drift"]["scale_rate_per_s"]) > 1e-12
        or stream["vio_scale_drift"]["max_scale_error"] > 0.0
        or bool(stream["imu_noise_burst"]["windows"])
    )
    normalized["dropout_count"] = 0
    normalized["target_loss_count"] = 0
    normalized["latency_s"] = normalized["sensor_latency"]["delay_s"]
    normalized["communication_interruption_count"] = 0
    normalized["control_saturation_count"] = 0
    normalized["gps_dropout_count"] = 0
    normalized["vio_scale_drift_count"] = 0
    normalized["vio_scale_drift_max_scale_error"] = 0.0
    normalized["imu_noise_burst_count"] = 0
    normalized["sensor_stream_fault_enabled"] = (
        stream["gps_dropout"]["probability"] > 0.0
        or bool(stream["gps_dropout"]["windows"])
        or abs(stream["vio_scale_drift"]["scale_rate_per_s"]) > 1e-12
        or stream["vio_scale_drift"]["max_scale_error"] > 0.0
        or bool(stream["imu_noise_burst"]["windows"])
    )
    normalized["summary"] = {
        "enabled": normalized["enabled"],
        "seed": seed,
        "sensor_dropout": normalized["sensor_dropout"],
        "target_loss": normalized["target_loss"],
        "sensor_noise": normalized["sensor_noise"],
        "measurement_bias": normalized["measurement_bias"],
        "measurement_bias_drift": normalized["measurement_bias_drift"],
        "measurement_saturation": normalized["measurement_saturation"],
        "sensor_latency": normalized["sensor_latency"],
        "communication_interruption": normalized["communication_interruption"],
        "control_saturation": normalized["control_saturation"],
        "sensor_stream_faults": normalized["sensor_stream_faults"],
    }
    return normalized


def normalize_dropout_windows(raw_windows):
    windows = []
    if not isinstance(raw_windows, list):
        return windows
    for window in raw_windows:
        if not isinstance(window, dict):
            continue
        start_s = optional_float(window.get("start_s"))
        end_s = optional_float(window.get("end_s"))
        if start_s is None or end_s is None or end_s < start_s:
            continue
        windows.append({"start_s": start_s, "end_s": end_s})
    return windows


def apply_disturbances(truth, t, disturbance_config, random_source):
    wind = disturbance_config["wind"]
    noise = disturbance_config["measurement_noise"]
    initial_z = disturbance_config["initial_offset"]["z_m"]
    measured = {
        "x_m": truth["x_m"] + wind["x_mps"] * t,
        "y_m": truth["y_m"] + wind["y_mps"] * t,
        "z_m": truth["z_m"] - initial_z - wind["z_mps"] * t,
    }
    position_std = noise["position_std_m"]
    altitude_std = noise["altitude_std_m"]
    if position_std > 0.0:
        measured["x_m"] += random_source.gauss(0.0, position_std)
        measured["y_m"] += random_source.gauss(0.0, position_std)
    if altitude_std > 0.0:
        measured["z_m"] += random_source.gauss(0.0, altitude_std)
    return measured


def apply_degradations(measured, t, degradation_config, random_source, latency_buffer, dt):
    degraded = dict(measured)
    dropout = degradation_config["sensor_dropout"]
    stream = degradation_config["sensor_stream_faults"]
    gps_dropout = stream["gps_dropout"]
    if is_in_dropout_window(t, degradation_config["target_loss"]["windows"]):
        degradation_config["target_loss_count"] += 1
        degradation_config["dropout_count"] += 1
        return None
    if is_in_dropout_window(t, dropout["windows"]) or random_source.random() < dropout["probability"]:
        degradation_config["dropout_count"] += 1
        return None
    if is_in_dropout_window(t, gps_dropout["windows"]) or random_source.random() < gps_dropout["probability"]:
        degradation_config["gps_dropout_count"] += 1
        degradation_config["dropout_count"] += 1
        return None

    bias = degradation_config["measurement_bias"]
    degraded["x_m"] += bias["x_m"]
    degraded["y_m"] += bias["y_m"]
    degraded["z_m"] += bias["z_m"]

    bias_drift = degradation_config["measurement_bias_drift"]
    degraded["x_m"] += bias_drift["x_mps"] * t
    degraded["y_m"] += bias_drift["y_mps"] * t
    degraded["z_m"] += bias_drift["z_mps"] * t

    noise = degradation_config["sensor_noise"]
    if noise["position_std_m"] > 0.0:
        degraded["x_m"] += random_source.gauss(0.0, noise["position_std_m"])
        degraded["y_m"] += random_source.gauss(0.0, noise["position_std_m"])
    if noise["altitude_std_m"] > 0.0:
        degraded["z_m"] += random_source.gauss(0.0, noise["altitude_std_m"])

    vio = stream["vio_scale_drift"]
    if t >= vio["start_s"] and (abs(vio["scale_rate_per_s"]) > 1e-12 or vio["max_scale_error"] > 0.0):
        raw_scale_error = max(t - vio["start_s"], 0.0) * vio["scale_rate_per_s"]
        max_scale_error = vio["max_scale_error"]
        if max_scale_error > 0.0:
            raw_scale_error = clamp(raw_scale_error, -max_scale_error, max_scale_error)
        scale = 1.0 + raw_scale_error
        degraded["x_m"] *= scale
        degraded["y_m"] *= scale
        degraded["z_m"] *= scale
        degradation_config["vio_scale_drift_count"] += 1
        degradation_config["vio_scale_drift_max_scale_error"] = max(
            degradation_config["vio_scale_drift_max_scale_error"],
            abs(raw_scale_error),
        )

    imu = stream["imu_noise_burst"]
    if is_in_dropout_window(t, imu["windows"]):
        degradation_config["imu_noise_burst_count"] += 1
        if imu["position_std_m"] > 0.0:
            degraded["x_m"] += random_source.gauss(0.0, imu["position_std_m"])
            degraded["y_m"] += random_source.gauss(0.0, imu["position_std_m"])
        if imu["altitude_std_m"] > 0.0:
            degraded["z_m"] += random_source.gauss(0.0, imu["altitude_std_m"])

    saturation = degradation_config["measurement_saturation"]
    max_horizontal = saturation["max_horizontal_range_m"]
    if max_horizontal is not None:
        horizontal = math.hypot(degraded["x_m"], degraded["y_m"])
        if horizontal > max_horizontal > 0.0:
            ratio = max_horizontal / horizontal
            degraded["x_m"] *= ratio
            degraded["y_m"] *= ratio
    altitude = -degraded["z_m"]
    min_altitude = saturation["min_altitude_m"]
    max_altitude = saturation["max_altitude_m"]
    if min_altitude is not None:
        altitude = max(altitude, min_altitude)
    if max_altitude is not None:
        altitude = min(altitude, max_altitude)
    degraded["z_m"] = -altitude

    delay_s = degradation_config["sensor_latency"]["delay_s"]
    if delay_s <= 0.0:
        return degraded
    latency_buffer.append({"t": t, "measured": dict(degraded)})
    cutoff_t = t - delay_s
    delayed = latency_buffer[0]["measured"]
    for entry in latency_buffer:
        if entry["t"] <= cutoff_t + dt * 0.5:
            delayed = entry["measured"]
        else:
            break
    while len(latency_buffer) > 2 and latency_buffer[1]["t"] <= cutoff_t:
        latency_buffer.pop(0)
    return dict(delayed)


def apply_speed_degradations(speed_mps, t, degradation_config, random_source):
    imu = degradation_config["sensor_stream_faults"]["imu_noise_burst"]
    if is_in_dropout_window(t, imu["windows"]) and imu["speed_std_mps"] > 0.0:
        return max(0.0, speed_mps + random_source.gauss(0.0, imu["speed_std_mps"]))
    return speed_mps


def is_in_dropout_window(t, windows):
    return any(window["start_s"] <= t <= window["end_s"] for window in windows)


def optional_float(value):
    if value is None:
        return None
    return float(value)


def clamp(value, minimum, maximum):
    return min(max(value, minimum), maximum)
