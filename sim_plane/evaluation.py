import math


KPI_PLUGIN_NAMES = [
    "core",
    "sensor",
    "altitude",
    "mission",
    "path",
    "truth",
    "dynamics",
    "safety",
    "recovery",
]


def enrich_result_with_kpis(result, scenario, telemetry):
    payload = dict(result or {})
    metrics = dict(payload.get("metrics") or {})
    kpis = compute_kpis(scenario or {}, telemetry or [])
    metrics.update(kpis)
    payload["metrics"] = metrics
    return payload


def compute_kpis(scenario, telemetry):
    context = build_kpi_context(scenario, telemetry)
    kpis = {}
    for plugin in KPI_PLUGINS:
        kpis.update(plugin(context))
    kpis["kpi_plugin_count"] = len(KPI_PLUGINS)
    kpis["kpi_plugin_names"] = list(KPI_PLUGIN_NAMES)
    return {key: value for key, value in kpis.items() if value is not None}


def build_kpi_context(scenario, telemetry):
    samples = [sample for sample in telemetry if isinstance(sample, dict)]
    target_altitude_m = as_float(scenario.get("target_altitude_m"))
    duration_s = as_float(scenario.get("duration_s"))
    waypoints = normalize_waypoints(scenario.get("waypoints"))
    safety = dict(scenario.get("safety") or {})
    control = dict(scenario.get("control_limits") or {})

    numeric_times = [as_float(sample.get("t")) for sample in samples]
    numeric_times = [value for value in numeric_times if value is not None]
    mission_duration_s = (
        max(numeric_times) - min(numeric_times)
        if len(numeric_times) >= 2
        else duration_s
    )

    positions = [sample_position(sample) for sample in samples]
    valid_positions = [position for position in positions if position is not None]
    altitudes = [sample_altitude(sample) for sample in samples]
    altitudes = [altitude for altitude in altitudes if altitude is not None]
    altitude_samples = [
        {"sample": sample, "value": altitude}
        for sample in samples
        for altitude in [sample_altitude(sample)]
        if altitude is not None
    ]
    speeds = [as_float(sample.get("speed_mps")) for sample in samples]
    speeds = [speed for speed in speeds if speed is not None]
    accelerations = sample_accelerations(samples)
    visible_samples = [
        sample
        for sample in samples
        if sample.get("sensor_visible") is not False and sample_position(sample) is not None
    ]
    mission_samples = [sample for sample in samples if is_mission_sample(sample)]
    mission_positions = [sample_position(sample) for sample in mission_samples]
    mission_positions = [position for position in mission_positions if position is not None]
    mission_altitudes = [sample_altitude(sample) for sample in mission_samples]
    mission_altitudes = [altitude for altitude in mission_altitudes if altitude is not None]
    return {
        "scenario": scenario,
        "samples": samples,
        "target_altitude_m": target_altitude_m,
        "duration_s": duration_s,
        "waypoints": waypoints,
        "safety": safety,
        "control_limits": control,
        "numeric_times": numeric_times,
        "mission_duration_s": mission_duration_s,
        "positions": positions,
        "valid_positions": valid_positions,
        "altitudes": altitudes,
        "altitude_samples": altitude_samples,
        "speeds": speeds,
        "accelerations": accelerations,
        "visible_samples": visible_samples,
        "mission_samples": mission_samples,
        "mission_positions": mission_positions,
        "mission_altitudes": mission_altitudes,
    }


def kpi_core(context):
    samples = context["samples"]
    speeds = context["speeds"]
    valid_positions = context["valid_positions"]
    kpis = {
        "kpi_sample_count": len(samples),
        "kpi_duration_s": round(context["mission_duration_s"], 3) if context["mission_duration_s"] is not None else None,
        "kpi_distance_m": round(path_distance(valid_positions), 3),
        "kpi_max_speed_mps": round(max(speeds), 3) if speeds else None,
        "kpi_mean_speed_mps": round(sum(speeds) / len(speeds), 3) if speeds else None,
        "kpi_speed_roughness_mps": round(mean_abs_delta(speeds), 3) if len(speeds) >= 2 else 0.0,
    }
    return kpis


def kpi_sensor(context):
    samples = context["samples"]
    visible_samples = context["visible_samples"]
    kpis = {}
    if visible_samples or any("sensor_visible" in sample for sample in samples):
        kpis["kpi_sensor_visible_count"] = len(visible_samples)
        kpis["kpi_sensor_dropout_count"] = max(len(samples) - len(visible_samples), 0)
        kpis["kpi_sensor_dropout_ratio"] = (
            round(kpis["kpi_sensor_dropout_count"] / len(samples), 6) if samples else 0.0
        )
        kpis["kpi_target_lost_count"] = count_visibility_loss_events(samples)
        kpis["kpi_target_reacquire_count"] = count_visibility_reacquire_events(samples)
    return kpis


def kpi_altitude(context):
    samples = context["samples"]
    target_altitude_m = context["target_altitude_m"]
    altitudes = context["altitudes"]
    kpis = {}
    if target_altitude_m is not None and altitudes:
        altitude_errors = [abs(altitude - target_altitude_m) for altitude in altitudes]
        kpis.update(
            {
                "kpi_target_altitude_m": round(target_altitude_m, 3),
                "kpi_altitude_mae_m": round(sum(altitude_errors) / len(altitude_errors), 3),
                "kpi_altitude_rmse_m": round(root_mean_square(altitude_errors), 3),
                "kpi_altitude_max_error_m": round(max(altitude_errors), 3),
                "kpi_altitude_overshoot_m": round(max(0.0, max(altitudes) - target_altitude_m), 3),
            }
        )
        settle_time = first_settle_time(context["altitude_samples"], target_altitude_m)
        kpis["kpi_altitude_settle_time_s"] = round(settle_time, 3) if settle_time is not None else None
        reached_time = first_reach_time(context["altitude_samples"], target_altitude_m * 0.95)
        kpis["kpi_target_reach_time_s"] = round(reached_time, 3) if reached_time is not None else None
        kpis["kpi_altitude_stabilization_time_s"] = kpis["kpi_altitude_settle_time_s"]
    return kpis


def kpi_mission(context):
    target_altitude_m = context["target_altitude_m"]
    mission_samples = context["mission_samples"]
    mission_altitudes = context["mission_altitudes"]
    kpis = {}
    if mission_samples:
        kpis["kpi_mission_sample_count"] = len(mission_samples)
    if target_altitude_m is not None and mission_altitudes:
        mission_altitude_errors = [abs(altitude - target_altitude_m) for altitude in mission_altitudes]
        kpis.update(
            {
                "kpi_mission_altitude_mae_m": round(
                    sum(mission_altitude_errors) / len(mission_altitude_errors), 3
                ),
                "kpi_mission_altitude_max_error_m": round(max(mission_altitude_errors), 3),
            }
        )
    return kpis


def kpi_path(context):
    waypoints = context["waypoints"]
    valid_positions = context["valid_positions"]
    mission_positions = context["mission_positions"]
    kpis = {}
    if waypoints and valid_positions:
        horizontal_errors = [
            distance_to_polyline_2d(position["x_m"], position["y_m"], waypoints)
            for position in valid_positions
        ]
        kpis.update(
            {
                "kpi_path_error_mae_m": round(sum(horizontal_errors) / len(horizontal_errors), 3),
                "kpi_path_error_max_m": round(max(horizontal_errors), 3),
            }
        )
    if waypoints and mission_positions:
        mission_horizontal_errors = [
            distance_to_polyline_2d(position["x_m"], position["y_m"], waypoints)
            for position in mission_positions
        ]
        kpis.update(
            {
                "kpi_mission_path_error_mae_m": round(
                    sum(mission_horizontal_errors) / len(mission_horizontal_errors), 3
                ),
                "kpi_mission_path_error_max_m": round(max(mission_horizontal_errors), 3),
            }
        )
    if waypoints and valid_positions:
        final_goal_distance = distance_to_goal_2d(valid_positions[-1], waypoints[-1])
        kpis["kpi_final_goal_distance_m"] = round(final_goal_distance, 3)
    return kpis


def kpi_truth(context):
    truth_errors = truth_position_errors(context["samples"])
    kpis = {}
    if truth_errors:
        horizontal_truth_errors = [error["horizontal_m"] for error in truth_errors]
        vertical_truth_errors = [error["vertical_m"] for error in truth_errors]
        kpis.update(
            {
                "kpi_measurement_horizontal_error_mae_m": round(
                    sum(horizontal_truth_errors) / len(horizontal_truth_errors), 3
                ),
                "kpi_measurement_horizontal_error_max_m": round(max(horizontal_truth_errors), 3),
                "kpi_measurement_vertical_error_mae_m": round(
                    sum(vertical_truth_errors) / len(vertical_truth_errors), 3
                ),
                "kpi_measurement_vertical_error_max_m": round(max(vertical_truth_errors), 3),
            }
        )
    return kpis


def kpi_dynamics(context):
    speeds = context["speeds"]
    accelerations = context["accelerations"]
    kpis = {}
    if accelerations:
        accel_magnitudes = [abs(value) for value in accelerations]
        kpis["kpi_max_acceleration_mps2"] = round(max(accel_magnitudes), 3)
        kpis["kpi_mean_abs_acceleration_mps2"] = round(sum(accel_magnitudes) / len(accel_magnitudes), 3)
        kpis["kpi_acceleration_roughness_mps2"] = (
            round(mean_abs_delta(accelerations), 3) if len(accelerations) >= 2 else 0.0
        )
    if speeds:
        control_limits = context["control_limits"]
        max_speed_limit = as_float(control_limits.get("max_speed_mps"))
        if max_speed_limit is not None:
            violations = [speed for speed in speeds if speed > max_speed_limit]
            kpis["kpi_speed_limit_mps"] = round(max_speed_limit, 3)
            kpis["kpi_speed_limit_violation_count"] = len(violations)
            kpis["kpi_speed_limit_max_excess_mps"] = (
                round(max(speed - max_speed_limit for speed in violations), 3) if violations else 0.0
            )
    return kpis


def kpi_safety(context):
    safety = context["safety"]
    valid_positions = context["valid_positions"]
    altitudes = context["altitudes"]
    kpis = {}
    min_altitude = as_float(safety.get("min_altitude_m"))
    max_altitude = as_float(safety.get("max_altitude_m"))
    max_radius = as_float(safety.get("max_radius_m"))
    violations = 0
    if min_altitude is not None:
        count = sum(1 for altitude in altitudes if altitude < min_altitude)
        kpis["kpi_min_altitude_violation_count"] = count
        violations += count
    if max_altitude is not None:
        count = sum(1 for altitude in altitudes if altitude > max_altitude)
        kpis["kpi_max_altitude_violation_count"] = count
        violations += count
    if max_radius is not None:
        count = sum(
            1
            for position in valid_positions
            if math.hypot(position["x_m"], position["y_m"]) > max_radius
        )
        kpis["kpi_geofence_violation_count"] = count
        violations += count
    if safety:
        kpis["kpi_safety_violation_count"] = violations
    return kpis


def kpi_recovery(context):
    samples = context["samples"]
    target_altitude_m = context["target_altitude_m"]
    altitudes = context["altitudes"]
    kpis = {}
    recovery_time = dropout_recovery_time(samples)
    if recovery_time is not None:
        kpis["kpi_sensor_recovery_time_s"] = round(recovery_time, 3)
    if target_altitude_m is not None and altitudes:
        recovery_after_error = first_recovery_after_error_time(context["altitude_samples"], target_altitude_m)
        if recovery_after_error is not None:
            kpis["kpi_altitude_recovery_time_s"] = round(recovery_after_error, 3)
    return kpis


KPI_PLUGINS = [
    kpi_core,
    kpi_sensor,
    kpi_altitude,
    kpi_mission,
    kpi_path,
    kpi_truth,
    kpi_dynamics,
    kpi_safety,
    kpi_recovery,
]


def sample_position(sample):
    position = sample.get("position") or {}
    x_m = as_float(position.get("x_m"))
    y_m = as_float(position.get("y_m"))
    z_m = as_float(position.get("z_m"))
    if x_m is None or y_m is None:
        return None
    return {"x_m": x_m, "y_m": y_m, "z_m": z_m}


def is_mission_sample(sample):
    phase = str(sample.get("phase") or "").lower()
    mode = str(sample.get("mode") or "").lower()
    return phase in ("mission", "offboard", "track", "follow") or mode == "offboard"


def sample_altitude(sample):
    altitude = as_float(sample.get("altitude_m"))
    if altitude is not None:
        return altitude
    position = sample_position(sample)
    if position is None or position["z_m"] is None:
        return None
    return max(0.0, -position["z_m"])


def normalize_waypoints(raw_waypoints):
    waypoints = []
    for waypoint in raw_waypoints or []:
        if not isinstance(waypoint, dict):
            continue
        x_m = as_float(waypoint.get("x_m", waypoint.get("x")))
        y_m = as_float(waypoint.get("y_m", waypoint.get("y")))
        if x_m is None or y_m is None:
            continue
        waypoints.append({"x_m": x_m, "y_m": y_m})
    return waypoints


def sample_accelerations(samples):
    values = []
    previous_t = None
    previous_speed = None
    for sample in samples:
        current_t = as_float(sample.get("t"))
        current_speed = as_float(sample.get("speed_mps"))
        if current_t is None or current_speed is None:
            continue
        if previous_t is not None and previous_speed is not None:
            dt = current_t - previous_t
            if dt > 1e-9:
                values.append((current_speed - previous_speed) / dt)
        previous_t = current_t
        previous_speed = current_speed
    return values


def path_distance(positions):
    distance_m = 0.0
    previous = None
    for position in positions:
        current = (
            position["x_m"],
            position["y_m"],
            position["z_m"] if position["z_m"] is not None else 0.0,
        )
        if previous is not None:
            distance_m += euclidean_distance(previous, current)
        previous = current
    return distance_m


def distance_to_polyline_2d(x_m, y_m, waypoints):
    if not waypoints:
        return 0.0
    if len(waypoints) == 1:
        return math.hypot(x_m - waypoints[0]["x_m"], y_m - waypoints[0]["y_m"])
    distances = []
    for start, end in zip(waypoints, waypoints[1:]):
        distances.append(distance_to_segment_2d(x_m, y_m, start, end))
    return min(distances) if distances else 0.0


def distance_to_segment_2d(x_m, y_m, start, end):
    sx = start["x_m"]
    sy = start["y_m"]
    ex = end["x_m"]
    ey = end["y_m"]
    dx = ex - sx
    dy = ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return math.hypot(x_m - sx, y_m - sy)
    ratio = ((x_m - sx) * dx + (y_m - sy) * dy) / length_sq
    ratio = min(1.0, max(0.0, ratio))
    closest_x = sx + ratio * dx
    closest_y = sy + ratio * dy
    return math.hypot(x_m - closest_x, y_m - closest_y)


def distance_to_goal_2d(position, goal):
    return math.hypot(position["x_m"] - goal["x_m"], position["y_m"] - goal["y_m"])


def truth_position_errors(samples):
    errors = []
    for sample in samples:
        measured = sample_position(sample)
        truth = sample.get("truth_position") or {}
        truth_x = as_float(truth.get("x_m"))
        truth_y = as_float(truth.get("y_m"))
        truth_z = as_float(truth.get("z_m"))
        if measured is None or truth_x is None or truth_y is None:
            continue
        measured_z = measured["z_m"] if measured["z_m"] is not None else 0.0
        truth_z = truth_z if truth_z is not None else measured_z
        errors.append(
            {
                "horizontal_m": math.hypot(measured["x_m"] - truth_x, measured["y_m"] - truth_y),
                "vertical_m": abs(measured_z - truth_z),
            }
        )
    return errors


def first_reach_time(sample_values, threshold):
    for entry in sample_values:
        sample_t = as_float(entry["sample"].get("t"))
        value = entry["value"]
        if sample_t is not None and value >= threshold:
            return sample_t
    return None


def first_settle_time(sample_values, target, tolerance_ratio=0.05):
    tolerance = max(abs(target) * tolerance_ratio, 0.05)
    values = [entry["value"] for entry in sample_values]
    for index, value in enumerate(values):
        sample_t = as_float(sample_values[index]["sample"].get("t"))
        if sample_t is None:
            continue
        tail = values[index:]
        if tail and all(abs(tail_value - target) <= tolerance for tail_value in tail):
            return sample_t
    return None


def first_recovery_after_error_time(sample_values, target, tolerance_ratio=0.05):
    tolerance = max(abs(target) * tolerance_ratio, 0.05)
    out_of_band_seen = False
    for entry in sample_values:
        sample_t = as_float(entry["sample"].get("t"))
        value = entry["value"]
        if sample_t is None:
            continue
        if abs(value - target) > tolerance:
            out_of_band_seen = True
            continue
        if out_of_band_seen:
            return sample_t
    return None


def count_visibility_loss_events(samples):
    count = 0
    previous_visible = True
    for sample in samples:
        visible = sample.get("sensor_visible") is not False and sample_position(sample) is not None
        if previous_visible and not visible:
            count += 1
        previous_visible = visible
    return count


def count_visibility_reacquire_events(samples):
    count = 0
    previous_visible = True
    for sample in samples:
        visible = sample.get("sensor_visible") is not False and sample_position(sample) is not None
        if not previous_visible and visible:
            count += 1
        previous_visible = visible
    return count


def dropout_recovery_time(samples):
    lost_start = None
    recovery_times = []
    for sample in samples:
        sample_t = as_float(sample.get("t"))
        visible = sample.get("sensor_visible") is not False and sample_position(sample) is not None
        if sample_t is None:
            continue
        if not visible and lost_start is None:
            lost_start = sample_t
        elif visible and lost_start is not None:
            recovery_times.append(sample_t - lost_start)
            lost_start = None
    return max(recovery_times) if recovery_times else None


def root_mean_square(values):
    if not values:
        return 0.0
    return math.sqrt(sum(value * value for value in values) / len(values))


def mean_abs_delta(values):
    if len(values) < 2:
        return 0.0
    deltas = [abs(current - previous) for previous, current in zip(values, values[1:])]
    return sum(deltas) / len(deltas)


def euclidean_distance(left, right):
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(left, right)))


def as_float(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number
