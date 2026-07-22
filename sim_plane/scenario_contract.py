import math


SCENARIO_SCHEMA_VERSION = 1
MISSION_TYPES = {"loop", "goal", "manual_goal"}


class ScenarioContractError(ValueError):
    pass


COMMON_SCENARIO_KEYS = {
    "schema_version",
    "name",
    "description",
    "backend",
    "vehicle",
    "duration_s",
    "update_hz",
    "target_altitude_m",
    "realtime_factor",
    "mission",
    "waypoints",
    "algorithm_adapter",
    "backend_options",
    "disturbances",
    "degradations",
    "control_limits",
    "safety",
    "source_path",
    "suite_variant",
}


ROS_BASE_OPTIONS = {
    "ros_setup",
    "ros_workspace_dir",
    "launch_rviz",
    "startup_timeout_s",
    "odom_topic",
    "pointcloud_topic",
    "command_topic",
    "shutdown_nodes",
    "success_criteria",
}

MARSIM_BASE_OPTIONS = ROS_BASE_OPTIONS | {
    "ros_package",
    "launch_file",
    "use_gpu",
    "map_topic",
}

PLANNER_GOAL_OPTIONS = {
    "goal_timeout_s",
    "goal_reach_tolerance_m",
    "goal_settle_speed_mps",
    "goal_settle_hold_s",
    "goal_topic",
    "goal_frame_id",
    "goal_x",
    "goal_y",
    "goal_z",
}

MARSIM_COMPOSITION_OPTIONS = {
    "marsim_workspace_dir",
    "marsim_ros_package",
    "marsim_launch_file",
    "marsim_launch_rviz",
    "use_gpu",
}

FAST_LIO_COMPOSITION_OPTIONS = {
    "fast_lio_workspace_dir",
    "fast_lio_launch_rviz",
    "source_odom_topic",
    "reference_odom_topic",
}

PX4_COMMON_OPTIONS = {
    "px4_dir",
    "model",
    "build_target",
    "qgc_path",
    "connect_timeout_s",
    "mavlink_endpoint",
    "launch_qgc",
    "process_start_grace_s",
    "speed_factor",
    "shell_commands",
    "shell_command_delay_s",
    "shell_command_interval_s",
    "success_criteria",
    "collect_ulog",
    "collect_ulog_max_files",
}


BACKEND_OPTION_KEYS = {
    "demo": set(),
    "ego_planner": ROS_BASE_OPTIONS
    | PLANNER_GOAL_OPTIONS
    | {"ros_package", "launch_file"},
    "ego_planner_swarm": ROS_BASE_OPTIONS | {"ros_package", "launch_file"},
    "marsim": MARSIM_BASE_OPTIONS,
    "fast_lio_marsim": ROS_BASE_OPTIONS
    | MARSIM_COMPOSITION_OPTIONS
    | FAST_LIO_COMPOSITION_OPTIONS
    | {"map_topic"},
    "ego_planner_marsim": ROS_BASE_OPTIONS
    | PLANNER_GOAL_OPTIONS
    | MARSIM_COMPOSITION_OPTIONS
    | {"ego_workspace_dir"},
    "ego_planner_fast_lio_marsim": ROS_BASE_OPTIONS
    | PLANNER_GOAL_OPTIONS
    | MARSIM_COMPOSITION_OPTIONS
    | FAST_LIO_COMPOSITION_OPTIONS
    | {"ego_workspace_dir"},
    "ego_planner_swarm_marsim": ROS_BASE_OPTIONS
    | PLANNER_GOAL_OPTIONS
    | MARSIM_COMPOSITION_OPTIONS
    | {"ego_workspace_dir", "ego_swarm_workspace_dir"},
    "ego_planner_swarm_fast_lio_marsim": ROS_BASE_OPTIONS
    | PLANNER_GOAL_OPTIONS
    | MARSIM_COMPOSITION_OPTIONS
    | FAST_LIO_COMPOSITION_OPTIONS
    | {"ego_workspace_dir", "ego_swarm_workspace_dir"},
    "px4_sih": PX4_COMMON_OPTIONS
    | {
        "launch_rviz",
        "launch_jmavsim",
        "jmavsim_port",
        "allow_early_stop_on_adapter_success",
    },
    "px4_jsbsim": PX4_COMMON_OPTIONS
    | {
        "jsbsim_root_dir",
        "world",
        "flightgear_binary",
        "headless",
        "build_jobs",
    },
    "px4_gazebo_classic": PX4_COMMON_OPTIONS
    | {
        "world",
        "world_file",
        "headless",
        "make_jobs",
        "simulation_target",
        "gazebo_master_uri",
        "launch_rviz",
        "stop_wait_timeout_s",
        "home_lat",
        "home_lon",
        "home_alt",
    },
}


PROCESS_ADAPTER_OPTIONS = {
    "type",
    "command",
    "shell",
    "workdir",
    "env",
    "result_json",
    "max_runtime_s",
    "join_timeout_s",
    "success_exit_codes",
    "allow_timeout_as_success",
    "treat_stop_request_as_success",
    "stop_signal",
    "stop_wait_timeout_s",
}

MAVSDK_CONNECTION_OPTIONS = {
    "type",
    "system_address",
    "udp_host",
    "udp_port",
    "join_timeout_s",
    "connect_timeout_s",
}

ADAPTER_OPTION_KEYS = {
    "external_command": PROCESS_ADAPTER_OPTIONS,
    "ros_command": PROCESS_ADAPTER_OPTIONS
    | {
        "ros_setup",
        "workspace_setup",
        "workspace_setups",
        "workspace_dirs",
        "required_published_topics",
        "required_subscribed_topics",
        "master_timeout_s",
        "ready_timeout_s",
        "post_launch_grace_s",
    },
    "mavsdk_action_takeoff": MAVSDK_CONNECTION_OPTIONS
    | {
        "armable_timeout_s",
        "takeoff_reach_timeout_s",
        "hold_after_takeoff_s",
        "land_timeout_s",
        "target_altitude_m",
        "land_at_end",
    },
    "mavsdk_failure_injection": MAVSDK_CONNECTION_OPTIONS
    | {
        "ready_timeout_s",
        "pre_injection_wait_s",
        "post_injection_observe_s",
        "reset_after_s",
        "instance",
        "failure_unit",
        "failure_type",
        "reset_failure_type",
        "reset_after_injection",
    },
}


BOOLEAN_OPTION_KEYS = {
    "launch_rviz",
    "use_gpu",
    "marsim_launch_rviz",
    "fast_lio_launch_rviz",
    "launch_qgc",
    "launch_jmavsim",
    "headless",
    "allow_early_stop_on_adapter_success",
    "collect_ulog",
}

INTEGER_OPTION_KEYS = {
    "jmavsim_port",
    "build_jobs",
    "make_jobs",
    "collect_ulog_max_files",
}

POSITIVE_NUMBER_OPTION_KEYS = {
    "startup_timeout_s",
    "goal_timeout_s",
    "connect_timeout_s",
    "speed_factor",
    "stop_wait_timeout_s",
}

NONNEGATIVE_NUMBER_OPTION_KEYS = {
    "goal_reach_tolerance_m",
    "goal_settle_speed_mps",
    "goal_settle_hold_s",
    "process_start_grace_s",
    "shell_command_delay_s",
    "shell_command_interval_s",
}

ARBITRARY_NUMBER_OPTION_KEYS = {
    "goal_x",
    "goal_y",
    "goal_z",
    "home_lat",
    "home_lon",
    "home_alt",
}

LIST_STRING_OPTION_KEYS = {"shell_commands", "shutdown_nodes"}


BOOLEAN_ADAPTER_KEYS = {
    "shell",
    "allow_timeout_as_success",
    "treat_stop_request_as_success",
    "land_at_end",
    "reset_after_injection",
}

NONNEGATIVE_ADAPTER_NUMBER_KEYS = {
    "max_runtime_s",
    "join_timeout_s",
    "stop_wait_timeout_s",
    "connect_timeout_s",
    "master_timeout_s",
    "ready_timeout_s",
    "post_launch_grace_s",
    "armable_timeout_s",
    "takeoff_reach_timeout_s",
    "hold_after_takeoff_s",
    "land_timeout_s",
    "target_altitude_m",
    "pre_injection_wait_s",
    "post_injection_observe_s",
    "reset_after_s",
}


def validate_scenario_contract(scenario):
    if not isinstance(scenario, dict):
        raise ScenarioContractError("scenario must be a JSON object")
    _reject_unknown(scenario, COMMON_SCENARIO_KEYS, "scenario")

    version = scenario.get("schema_version")
    if not _is_integer(version) or version != SCENARIO_SCHEMA_VERSION:
        raise ScenarioContractError(
            "scenario.schema_version must be {0}".format(SCENARIO_SCHEMA_VERSION)
        )

    _require_string(scenario.get("name"), "scenario.name", nonempty=True)
    _require_string(scenario.get("description"), "scenario.description")
    backend = scenario.get("backend")
    _require_string(backend, "scenario.backend", nonempty=True)
    if backend not in BACKEND_OPTION_KEYS:
        raise ScenarioContractError("scenario.backend is not supported: {0}".format(backend))
    _require_string(scenario.get("vehicle"), "scenario.vehicle", nonempty=True)
    _require_number(scenario.get("duration_s"), "scenario.duration_s", minimum=0.0, exclusive=True)
    _require_number(scenario.get("update_hz"), "scenario.update_hz", minimum=0.0, exclusive=True)
    _require_number(scenario.get("target_altitude_m"), "scenario.target_altitude_m")
    _require_number(scenario.get("realtime_factor"), "scenario.realtime_factor", minimum=0.0)

    _validate_mission(scenario.get("mission"))
    _validate_waypoints(scenario.get("waypoints"))
    _validate_backend_options(backend, scenario.get("backend_options"))
    _validate_adapter(scenario.get("algorithm_adapter"))
    _validate_disturbances(scenario.get("disturbances"))
    _validate_degradations(scenario.get("degradations"))
    _validate_control_limits(scenario.get("control_limits"))
    _validate_safety(scenario.get("safety"))

    if scenario.get("source_path") is not None:
        _require_string(scenario.get("source_path"), "scenario.source_path", nonempty=True)
    if scenario.get("suite_variant") is not None:
        _require_string(scenario.get("suite_variant"), "scenario.suite_variant", nonempty=True)


def _validate_backend_options(backend, options):
    if not isinstance(options, dict):
        raise ScenarioContractError("scenario.backend_options must be an object")
    _reject_unknown(options, BACKEND_OPTION_KEYS[backend], "scenario.backend_options for {0}".format(backend))
    for key, value in options.items():
        path = "scenario.backend_options.{0}".format(key)
        if key in BOOLEAN_OPTION_KEYS:
            _require_boolean(value, path)
        elif key in INTEGER_OPTION_KEYS:
            _require_integer(value, path, minimum=0)
        elif key in POSITIVE_NUMBER_OPTION_KEYS:
            if value is not None:
                _require_number(value, path, minimum=0.0, exclusive=True)
        elif key in NONNEGATIVE_NUMBER_OPTION_KEYS:
            _require_number(value, path, minimum=0.0)
        elif key in ARBITRARY_NUMBER_OPTION_KEYS:
            if value is not None:
                _require_number(value, path)
        elif key in LIST_STRING_OPTION_KEYS:
            _require_string_list(value, path)
        else:
            _require_string(value, path)


def _validate_adapter(adapter):
    if adapter is None:
        return
    if not isinstance(adapter, dict):
        raise ScenarioContractError("scenario.algorithm_adapter must be null or an object")
    adapter_type = adapter.get("type")
    _require_string(adapter_type, "scenario.algorithm_adapter.type", nonempty=True)
    if adapter_type not in ADAPTER_OPTION_KEYS:
        raise ScenarioContractError(
            "scenario.algorithm_adapter.type is not supported: {0}".format(adapter_type)
        )
    _reject_unknown(
        adapter,
        ADAPTER_OPTION_KEYS[adapter_type],
        "scenario.algorithm_adapter for {0}".format(adapter_type),
    )

    if adapter_type in {"external_command", "ros_command"}:
        _validate_command(adapter.get("command"), "scenario.algorithm_adapter.command")
    if adapter_type == "mavsdk_failure_injection":
        for key in ("failure_unit", "failure_type"):
            _require_string(adapter.get(key), "scenario.algorithm_adapter.{0}".format(key), nonempty=True)

    for key, value in adapter.items():
        path = "scenario.algorithm_adapter.{0}".format(key)
        if key == "type" or key == "command":
            continue
        if key in BOOLEAN_ADAPTER_KEYS:
            _require_boolean(value, path)
        elif key in NONNEGATIVE_ADAPTER_NUMBER_KEYS:
            if value is None and not (adapter_type == "ros_command" and key == "max_runtime_s"):
                raise ScenarioContractError("{0} must be a number".format(path))
            if value is not None:
                _require_number(value, path, minimum=0.0)
        elif key == "udp_port":
            _require_integer(value, path, minimum=1, maximum=65535)
        elif key == "instance":
            _require_integer(value, path, minimum=0)
        elif key == "success_exit_codes":
            if not isinstance(value, list) or not all(_is_integer(item) for item in value):
                raise ScenarioContractError("{0} must be a list of integers".format(path))
        elif key == "env":
            if not isinstance(value, dict) or not all(
                isinstance(key, str) and isinstance(item, str)
                for key, item in value.items()
            ):
                raise ScenarioContractError(
                    "{0} must be an object with string keys and values".format(path)
                )
        elif key in {
            "required_published_topics",
            "required_subscribed_topics",
            "workspace_setups",
            "workspace_dirs",
        }:
            _require_string_or_string_list(value, path)
        elif key == "stop_signal":
            if not isinstance(value, str) and not _is_integer(value):
                raise ScenarioContractError("{0} must be a string or integer".format(path))
        else:
            _require_string(value, path)

    if adapter_type in {"external_command", "ros_command"}:
        if adapter.get("shell", False) and isinstance(adapter.get("command"), list):
            raise ScenarioContractError(
                "{0}.command must be a string when shell=true".format(
                    "scenario.algorithm_adapter"
                )
            )


def _validate_mission(mission):
    if not isinstance(mission, dict):
        raise ScenarioContractError("scenario.mission must be an object")
    _reject_unknown(mission, {"type", "goal"}, "scenario.mission")
    mission_type = mission.get("type")
    _require_string(mission_type, "scenario.mission.type", nonempty=True)
    if mission_type not in MISSION_TYPES:
        raise ScenarioContractError(
            "scenario.mission.type is not supported: {0}".format(mission_type)
        )
    goal = mission.get("goal")
    if mission_type in {"goal", "manual_goal"} and goal is None:
        raise ScenarioContractError(
            "scenario.mission.goal is required for mission type {0}".format(mission_type)
        )
    if goal is None:
        return
    if not isinstance(goal, dict):
        raise ScenarioContractError("scenario.mission.goal must be an object")
    _reject_unknown(goal, {"x", "y", "z"}, "scenario.mission.goal")
    missing = sorted({"x", "y", "z"} - set(goal))
    if missing:
        raise ScenarioContractError(
            "scenario.mission.goal is missing coordinate(s): {0}".format(", ".join(missing))
        )
    for key, value in goal.items():
        _require_number(value, "scenario.mission.goal.{0}".format(key))


def _validate_waypoints(waypoints):
    if not isinstance(waypoints, list):
        raise ScenarioContractError("scenario.waypoints must be a list")
    allowed = {"x", "y", "z"}
    for index, waypoint in enumerate(waypoints):
        path = "scenario.waypoints[{0}]".format(index)
        if not isinstance(waypoint, dict):
            raise ScenarioContractError("{0} must be an object".format(path))
        _reject_unknown(waypoint, allowed, path)
        if "x" not in waypoint or "y" not in waypoint:
            raise ScenarioContractError("{0} must provide x and y".format(path))
        for key, value in waypoint.items():
            _require_number(value, "{0}.{1}".format(path, key))


def _validate_disturbances(config):
    if config is None:
        return
    if not isinstance(config, dict):
        raise ScenarioContractError("scenario.disturbances must be an object")
    _reject_unknown(config, {"seed", "wind", "measurement_noise", "initial_offset"}, "scenario.disturbances")
    if "seed" in config:
        _require_integer(config["seed"], "scenario.disturbances.seed")
    _validate_numeric_group(config, "wind", {"x_mps", "y_mps", "z_mps"})
    _validate_numeric_group(
        config,
        "measurement_noise",
        {"position_std_m", "altitude_std_m"},
        minimum=0.0,
    )
    _validate_numeric_group(config, "initial_offset", {"x_m", "y_m", "z_m"})


def _validate_degradations(config):
    if config is None:
        return
    if not isinstance(config, dict):
        raise ScenarioContractError("scenario.degradations must be an object")
    allowed = {
        "seed",
        "sensor_dropout",
        "target_loss",
        "sensor_noise",
        "measurement_bias",
        "measurement_bias_drift",
        "measurement_saturation",
        "sensor_latency",
        "communication_interruption",
        "control_saturation",
        "sensor_stream_faults",
    }
    _reject_unknown(config, allowed, "scenario.degradations")
    if "seed" in config:
        _require_integer(config["seed"], "scenario.degradations.seed")

    _validate_window_group(config, "sensor_dropout", allow_probability=True)
    _validate_window_group(config, "target_loss")
    _validate_numeric_group(config, "sensor_noise", {"position_std_m", "altitude_std_m"}, minimum=0.0)
    _validate_numeric_group(config, "measurement_bias", {"x_m", "y_m", "z_m"})
    _validate_numeric_group(config, "measurement_bias_drift", {"x_mps", "y_mps", "z_mps"})
    _validate_numeric_group(
        config,
        "measurement_saturation",
        {"max_horizontal_range_m", "min_altitude_m", "max_altitude_m"},
        nonnegative_keys={"max_horizontal_range_m"},
    )
    _validate_numeric_group(config, "sensor_latency", {"delay_s"}, minimum=0.0)
    _validate_window_group(config, "communication_interruption")
    _validate_numeric_group(config, "control_saturation", {"max_speed_mps"}, minimum=0.0)

    stream = config.get("sensor_stream_faults")
    if stream is not None:
        if not isinstance(stream, dict):
            raise ScenarioContractError("scenario.degradations.sensor_stream_faults must be an object")
        _reject_unknown(stream, {"gps_dropout", "vio_scale_drift", "imu_noise_burst"}, "scenario.degradations.sensor_stream_faults")
        _validate_window_group(stream, "gps_dropout", allow_probability=True, prefix="scenario.degradations.sensor_stream_faults")
        _validate_numeric_group(
            stream,
            "vio_scale_drift",
            {"start_s", "scale_rate_per_s", "max_scale_error"},
            nonnegative_keys={"start_s", "max_scale_error"},
            prefix="scenario.degradations.sensor_stream_faults",
        )
        _validate_window_numeric_group(
            stream,
            "imu_noise_burst",
            {"position_std_m", "altitude_std_m", "speed_std_mps"},
            prefix="scenario.degradations.sensor_stream_faults",
        )


def _validate_control_limits(config):
    if config is None:
        return
    if not isinstance(config, dict):
        raise ScenarioContractError("scenario.control_limits must be an object")
    _reject_unknown(config, {"max_speed_mps"}, "scenario.control_limits")
    if "max_speed_mps" in config:
        _require_number(config["max_speed_mps"], "scenario.control_limits.max_speed_mps", minimum=0.0)


def _validate_safety(config):
    if config is None:
        return
    if not isinstance(config, dict):
        raise ScenarioContractError("scenario.safety must be an object")
    _reject_unknown(config, {"min_altitude_m", "max_altitude_m", "max_radius_m"}, "scenario.safety")
    for key, value in config.items():
        minimum = 0.0 if key == "max_radius_m" else None
        _require_number(value, "scenario.safety.{0}".format(key), minimum=minimum)
    if "min_altitude_m" in config and "max_altitude_m" in config:
        if float(config["min_altitude_m"]) > float(config["max_altitude_m"]):
            raise ScenarioContractError("scenario.safety.min_altitude_m must not exceed max_altitude_m")


def _validate_numeric_group(container, key, allowed, minimum=None, nonnegative_keys=None, prefix="scenario.degradations"):
    group = container.get(key)
    if group is None:
        return
    path = "{0}.{1}".format(prefix, key)
    if not isinstance(group, dict):
        raise ScenarioContractError("{0} must be an object".format(path))
    _reject_unknown(group, allowed, path)
    for field, value in group.items():
        field_minimum = 0.0 if nonnegative_keys and field in nonnegative_keys else minimum
        _require_number(value, "{0}.{1}".format(path, field), minimum=field_minimum)
    if key == "measurement_saturation":
        minimum_altitude = group.get("min_altitude_m")
        maximum_altitude = group.get("max_altitude_m")
        if minimum_altitude is not None and maximum_altitude is not None:
            if float(minimum_altitude) > float(maximum_altitude):
                raise ScenarioContractError(
                    "{0}.min_altitude_m must not exceed max_altitude_m".format(path)
                )


def _validate_window_numeric_group(container, key, numeric_keys, prefix):
    group = container.get(key)
    if group is None:
        return
    path = "{0}.{1}".format(prefix, key)
    if not isinstance(group, dict):
        raise ScenarioContractError("{0} must be an object".format(path))
    _reject_unknown(group, set(numeric_keys) | {"windows"}, path)
    _validate_windows(group.get("windows"), "{0}.windows".format(path))
    for field in numeric_keys:
        if field in group:
            _require_number(group[field], "{0}.{1}".format(path, field), minimum=0.0)


def _validate_window_group(container, key, allow_probability=False, prefix="scenario.degradations"):
    group = container.get(key)
    if group is None:
        return
    path = "{0}.{1}".format(prefix, key)
    if not isinstance(group, dict):
        raise ScenarioContractError("{0} must be an object".format(path))
    allowed = {"windows"}
    if allow_probability:
        allowed.add("probability")
    _reject_unknown(group, allowed, path)
    _validate_windows(group.get("windows"), "{0}.windows".format(path))
    if "probability" in group:
        _require_number(group["probability"], "{0}.probability".format(path), minimum=0.0, maximum=1.0)


def _validate_windows(windows, path):
    if windows is None:
        return
    if not isinstance(windows, list):
        raise ScenarioContractError("{0} must be a list".format(path))
    for index, window in enumerate(windows):
        item_path = "{0}[{1}]".format(path, index)
        if not isinstance(window, dict):
            raise ScenarioContractError("{0} must be an object".format(item_path))
        _reject_unknown(window, {"start_s", "end_s"}, item_path)
        if "start_s" not in window or "end_s" not in window:
            raise ScenarioContractError("{0} must provide start_s and end_s".format(item_path))
        _require_number(window["start_s"], "{0}.start_s".format(item_path), minimum=0.0)
        _require_number(window["end_s"], "{0}.end_s".format(item_path), minimum=0.0)
        if float(window["end_s"]) < float(window["start_s"]):
            raise ScenarioContractError("{0}.end_s must be greater than or equal to start_s".format(item_path))


def _validate_command(value, path):
    if isinstance(value, str):
        if not value.strip():
            raise ScenarioContractError("{0} must not be empty".format(path))
        return
    if isinstance(value, list) and value and all(isinstance(item, str) and item for item in value):
        return
    raise ScenarioContractError("{0} must be a non-empty string or list of strings".format(path))


def _reject_unknown(mapping, allowed, path):
    unknown = sorted(set(mapping) - set(allowed))
    if unknown:
        raise ScenarioContractError(
            "{0} contains unsupported field(s): {1}".format(path, ", ".join(unknown))
        )


def _require_string(value, path, nonempty=False):
    if not isinstance(value, str):
        raise ScenarioContractError("{0} must be a string".format(path))
    if nonempty and not value.strip():
        raise ScenarioContractError("{0} must not be empty".format(path))


def _require_string_list(value, path):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ScenarioContractError("{0} must be a list of strings".format(path))


def _require_string_or_string_list(value, path):
    if isinstance(value, str):
        return
    _require_string_list(value, path)


def _require_boolean(value, path):
    if not isinstance(value, bool):
        raise ScenarioContractError("{0} must be a boolean".format(path))


def _require_integer(value, path, minimum=None, maximum=None):
    if not _is_integer(value):
        raise ScenarioContractError("{0} must be an integer".format(path))
    if minimum is not None and value < minimum:
        raise ScenarioContractError("{0} must be at least {1}".format(path, minimum))
    if maximum is not None and value > maximum:
        raise ScenarioContractError("{0} must be at most {1}".format(path, maximum))


def _require_number(value, path, minimum=None, maximum=None, exclusive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ScenarioContractError("{0} must be a finite number".format(path))
    numeric = float(value)
    if minimum is not None:
        invalid = numeric <= minimum if exclusive else numeric < minimum
        if invalid:
            relation = "greater than" if exclusive else "at least"
            raise ScenarioContractError("{0} must be {1} {2}".format(path, relation, minimum))
    if maximum is not None and numeric > maximum:
        raise ScenarioContractError("{0} must be at most {1}".format(path, maximum))


def _is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)
