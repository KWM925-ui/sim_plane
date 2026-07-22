import time
from queue import Empty

from sim_plane.backends.base import BackendError
from sim_plane.backends.planner_goal import (
    compute_goal_distance_m,
    finalize_goal_reach_diagnostics,
    make_goal_reach_diagnostics,
    sample_time_seconds,
    update_goal_reach_diagnostics,
    update_goal_reach_state,
)


def stream_scene_telemetry(config, sink, telemetry_queue, marsim_process, planner_process):
    return _stream_planner_telemetry(
        config=config,
        sink=sink,
        telemetry_queue=telemetry_queue,
        process_checks=(
            (
                marsim_process,
                "MARSIM roslaunch exited before the configured planner-on-scene run duration elapsed.",
            ),
            (
                planner_process,
                "The planner roslaunch exited before the configured planner-on-scene run duration elapsed.",
            ),
        ),
        first_sample_timeout="Timed out waiting for MARSIM odometry telemetry.",
        first_sample_event="planner-on-scene odometry received",
        pointcloud_event="scene pointcloud detected",
        summary_extra={
            "launch_rviz": config["launch_rviz"],
            "cloud_only": True,
        },
    )


def stream_estimator_telemetry(
    config,
    sink,
    telemetry_queue,
    marsim_process,
    fast_lio_process,
    planner_process,
):
    return _stream_planner_telemetry(
        config=config,
        sink=sink,
        telemetry_queue=telemetry_queue,
        process_checks=(
            (
                marsim_process,
                "MARSIM roslaunch exited before the configured planner-on-estimator run duration elapsed.",
            ),
            (
                fast_lio_process,
                "FAST_LIO roslaunch exited before the configured planner-on-estimator run duration elapsed.",
            ),
            (
                planner_process,
                "The planner roslaunch exited before the configured planner-on-estimator run duration elapsed.",
            ),
        ),
        first_sample_timeout="Timed out waiting for FAST_LIO odometry telemetry.",
        first_sample_event="planner-on-estimator odometry received",
        pointcloud_event="planner obstacle cloud detected",
        summary_extra={
            "launch_rviz": config["launch_rviz"],
            "marsim_launch_rviz": config["marsim_launch_rviz"],
            "fast_lio_launch_rviz": config["fast_lio_launch_rviz"],
            "cloud_only": True,
        },
    )


def _stream_planner_telemetry(
    *,
    config,
    sink,
    telemetry_queue,
    process_checks,
    first_sample_timeout,
    first_sample_event,
    pointcloud_event,
    summary_extra,
):
    start_wall = time.time()
    deadline = start_wall + config["duration_s"]
    telemetry_count = 0
    max_altitude_m = 0.0
    max_speed_mps = 0.0
    max_pointcloud_width = 0
    reached_target_altitude = False
    position_cmd_seen = False
    pointcloud_seen = False
    goal_reached = False
    min_goal_distance_m = None
    goal_settled_since = None
    goal_diagnostics = make_goal_reach_diagnostics(
        tolerance_m=config["goal_reach_tolerance_m"],
        settle_speed_mps=config["goal_settle_speed_mps"],
        settle_hold_s=config["goal_settle_hold_s"],
    )
    first_sample_seen = False
    first_sample_deadline = start_wall + config["startup_timeout_s"]

    while time.time() <= deadline:
        for process, exit_message in process_checks:
            if process.poll() is not None:
                raise BackendError(exit_message)

        timeout_s = (
            0.25
            if first_sample_seen
            else max(0.0, min(0.25, first_sample_deadline - time.time()))
        )
        if not first_sample_seen and timeout_s == 0.0:
            raise BackendError(first_sample_timeout)
        try:
            sample = telemetry_queue.get(timeout=max(timeout_s, 0.05))
        except Empty:
            continue

        if not first_sample_seen:
            first_sample_seen = True
            sink.emit_event(
                "info",
                first_sample_event,
                {
                    "odom_topic": config["odom_topic"],
                    "position": sample["position"],
                    "altitude_m": sample["altitude_m"],
                },
            )
        if sample.get("position_cmd_count", 0) > 0 and not position_cmd_seen:
            position_cmd_seen = True
            sink.emit_event(
                "info",
                "planner command stream detected",
                {
                    "command_topic": config["command_topic"],
                    "count": sample["position_cmd_count"],
                },
            )
        if sample.get("pointcloud_count", 0) > 0 and not pointcloud_seen:
            pointcloud_seen = True
            sink.emit_event(
                "info",
                pointcloud_event,
                {
                    "pointcloud_topic": config["pointcloud_topic"],
                    "width": sample.get("pointcloud_width", 0),
                },
            )

        sink.emit_telemetry(sample)
        telemetry_count += 1
        max_altitude_m = max(max_altitude_m, float(sample.get("altitude_m", 0.0)))
        max_speed_mps = max(max_speed_mps, float(sample.get("speed_mps", 0.0)))
        max_pointcloud_width = max(
            max_pointcloud_width,
            int(sample.get("pointcloud_width", 0) or 0),
        )
        goal_distance_m = compute_goal_distance_m(config["goal"], sample)
        min_goal_distance_m = (
            goal_distance_m
            if min_goal_distance_m is None
            else min(min_goal_distance_m, goal_distance_m)
        )
        sample_now = sample_time_seconds(sample, fallback=time.time() - start_wall)
        if float(sample.get("altitude_m", 0.0)) >= config["target_altitude_m"] * 0.95:
            reached_target_altitude = True
        sample_goal_reached, goal_settled_since = update_goal_reach_state(
            goal_distance_m=goal_distance_m,
            speed_mps=float(sample.get("speed_mps", 0.0)),
            tolerance_m=config["goal_reach_tolerance_m"],
            settle_speed_mps=config["goal_settle_speed_mps"],
            settle_hold_s=config["goal_settle_hold_s"],
            settled_since=goal_settled_since,
            now=sample_now,
        )
        update_goal_reach_diagnostics(
            goal_diagnostics,
            goal_distance_m=goal_distance_m,
            speed_mps=float(sample.get("speed_mps", 0.0)),
            settled_since=goal_settled_since,
            now=sample_now,
        )
        if sample_goal_reached:
            goal_reached = True
            sink.emit_event(
                "info",
                "goal reached",
                {
                    "goal": config["goal"],
                    "goal_distance_m": round(goal_distance_m, 3),
                    "speed_mps": sample.get("speed_mps", 0.0),
                },
            )
            break

    summary = {
        "telemetry_count": telemetry_count,
        "max_altitude_m": round(max_altitude_m, 3),
        "max_speed_mps": round(max_speed_mps, 3),
        "max_pointcloud_width": max_pointcloud_width,
        "pointcloud_seen": pointcloud_seen,
        "target_altitude_reached": reached_target_altitude,
        "position_cmd_seen": position_cmd_seen,
        "goal_reached": goal_reached,
        "min_goal_distance_m": (
            round(min_goal_distance_m, 3) if min_goal_distance_m is not None else None
        ),
        "duration_s": round(time.time() - start_wall, 3),
    }
    summary.update(summary_extra)
    summary.update(
        finalize_goal_reach_diagnostics(goal_diagnostics, goal_reached=goal_reached)
    )
    return summary
