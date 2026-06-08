import math
import time


def update_goal_reach_state(
    *,
    goal_distance_m,
    speed_mps,
    tolerance_m,
    settle_speed_mps,
    settle_hold_s,
    settled_since,
    now=None,
):
    """Update planner goal-settle state for one telemetry sample."""
    try:
        goal_distance_m = float(goal_distance_m)
        speed_mps = float(speed_mps)
        tolerance_m = float(tolerance_m)
        settle_speed_mps = float(settle_speed_mps)
        settle_hold_s = float(settle_hold_s)
    except (TypeError, ValueError):
        return False, None

    if not all(
        math.isfinite(value)
        for value in (
            goal_distance_m,
            speed_mps,
            tolerance_m,
            settle_speed_mps,
            settle_hold_s,
        )
    ):
        return False, None

    if goal_distance_m > tolerance_m or speed_mps > settle_speed_mps:
        return False, None

    sample_time = time.time() if now is None else now
    if settle_hold_s <= 0.0:
        return True, sample_time

    if settled_since is None:
        return False, sample_time

    return sample_time - settled_since >= settle_hold_s, settled_since


def sample_time_seconds(sample, fallback=None):
    try:
        value = float((sample or {}).get("t"))
    except (TypeError, ValueError):
        return fallback
    return value if math.isfinite(value) else fallback


def make_goal_reach_diagnostics(*, tolerance_m, settle_speed_mps, settle_hold_s):
    return {
        "sample_count": 0,
        "tolerance_m": float(tolerance_m),
        "settle_speed_mps": float(settle_speed_mps),
        "settle_hold_s": float(settle_hold_s),
        "distance_within_tolerance_seen": False,
        "settle_condition_seen": False,
        "min_goal_distance_m": None,
        "min_goal_distance_speed_mps": None,
        "min_goal_distance_time_s": None,
        "min_low_speed_goal_distance_m": None,
        "min_low_speed_goal_speed_mps": None,
        "min_low_speed_goal_time_s": None,
        "longest_goal_settle_window_s": 0.0,
        "final_goal_distance_m": None,
        "final_goal_speed_mps": None,
        "final_goal_time_s": None,
    }


def update_goal_reach_diagnostics(
    diagnostics,
    *,
    goal_distance_m,
    speed_mps,
    settled_since,
    now,
):
    try:
        goal_distance_m = float(goal_distance_m)
        speed_mps = float(speed_mps)
    except (TypeError, ValueError):
        return diagnostics
    if not math.isfinite(goal_distance_m) or not math.isfinite(speed_mps):
        return diagnostics

    diagnostics["sample_count"] += 1
    diagnostics["final_goal_distance_m"] = goal_distance_m
    diagnostics["final_goal_speed_mps"] = speed_mps
    diagnostics["final_goal_time_s"] = now

    if (
        diagnostics["min_goal_distance_m"] is None
        or goal_distance_m < diagnostics["min_goal_distance_m"]
    ):
        diagnostics["min_goal_distance_m"] = goal_distance_m
        diagnostics["min_goal_distance_speed_mps"] = speed_mps
        diagnostics["min_goal_distance_time_s"] = now

    if goal_distance_m <= diagnostics["tolerance_m"]:
        diagnostics["distance_within_tolerance_seen"] = True
        if speed_mps <= diagnostics["settle_speed_mps"]:
            diagnostics["settle_condition_seen"] = True
            if (
                diagnostics["min_low_speed_goal_distance_m"] is None
                or goal_distance_m < diagnostics["min_low_speed_goal_distance_m"]
            ):
                diagnostics["min_low_speed_goal_distance_m"] = goal_distance_m
                diagnostics["min_low_speed_goal_speed_mps"] = speed_mps
                diagnostics["min_low_speed_goal_time_s"] = now
            if settled_since is not None and now is not None:
                diagnostics["longest_goal_settle_window_s"] = max(
                    diagnostics["longest_goal_settle_window_s"],
                    max(0.0, float(now) - float(settled_since)),
                )

    return diagnostics


def finalize_goal_reach_diagnostics(diagnostics, *, goal_reached):
    payload = {
        "goal_reach_tolerance_m": round(diagnostics["tolerance_m"], 3),
        "goal_reach_settle_speed_mps": round(diagnostics["settle_speed_mps"], 3),
        "goal_reach_settle_hold_s": round(diagnostics["settle_hold_s"], 3),
        "goal_reach_longest_settle_window_s": round(diagnostics["longest_goal_settle_window_s"], 3),
        "goal_reach_sample_count": diagnostics["sample_count"],
    }
    for source, target in (
        ("min_goal_distance_m", "goal_reach_min_distance_m"),
        ("min_goal_distance_speed_mps", "goal_reach_min_distance_speed_mps"),
        ("min_goal_distance_time_s", "goal_reach_min_distance_time_s"),
        ("min_low_speed_goal_distance_m", "goal_reach_min_low_speed_distance_m"),
        ("min_low_speed_goal_speed_mps", "goal_reach_min_low_speed_speed_mps"),
        ("min_low_speed_goal_time_s", "goal_reach_min_low_speed_time_s"),
        ("final_goal_distance_m", "goal_reach_final_distance_m"),
        ("final_goal_speed_mps", "goal_reach_final_speed_mps"),
        ("final_goal_time_s", "goal_reach_final_time_s"),
    ):
        value = diagnostics.get(source)
        if value is not None:
            payload[target] = round(float(value), 3)

    if diagnostics.get("min_goal_distance_m") is not None:
        payload["goal_reach_min_tolerance_margin_m"] = round(
            diagnostics["tolerance_m"] - diagnostics["min_goal_distance_m"],
            6,
        )
    if diagnostics.get("min_low_speed_goal_distance_m") is not None:
        payload["goal_reach_min_low_speed_tolerance_margin_m"] = round(
            diagnostics["tolerance_m"] - diagnostics["min_low_speed_goal_distance_m"],
            6,
        )
    if diagnostics.get("final_goal_distance_m") is not None:
        payload["goal_reach_final_tolerance_margin_m"] = round(
            diagnostics["tolerance_m"] - diagnostics["final_goal_distance_m"],
            6,
        )

    if goal_reached:
        payload["goal_reach_failure_reason"] = None
    elif diagnostics["sample_count"] <= 0:
        payload["goal_reach_failure_reason"] = "no_telemetry"
    elif not diagnostics["distance_within_tolerance_seen"]:
        payload["goal_reach_failure_reason"] = "distance_never_within_tolerance"
    elif not diagnostics["settle_condition_seen"]:
        payload["goal_reach_failure_reason"] = "within_tolerance_only_above_settle_speed"
    elif diagnostics["longest_goal_settle_window_s"] < diagnostics["settle_hold_s"]:
        payload["goal_reach_failure_reason"] = "settle_hold_not_met"
    else:
        payload["goal_reach_failure_reason"] = "not_reached"
    return payload
