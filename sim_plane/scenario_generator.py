import shlex

from sim_plane.io_utils import atomic_write_json
from sim_plane.paths import get_platform_paths, resolve_platform_path
from sim_plane.scenario import normalize_scenario
from sim_plane.scenario_contract import SCENARIO_SCHEMA_VERSION


REPO_ROOT = get_platform_paths().home
DEFAULT_OUTPUT_DIR = REPO_ROOT / "scenarios"


EXTERNAL_BACKEND_DEFAULTS = {
    "px4_sih": {
        "name_prefix": "px4_sih_quadx",
        "duration_s": 40.0,
        "target_altitude_m": 4.0,
        "adapter_max_runtime_s": 36.0,
        "adapter_join_timeout_s": 6.0,
        "backend_options": {
            "model": "sihsim_quadx",
            "mavlink_endpoint": "udpin:127.0.0.1:14550",
            "launch_qgc": False,
            "launch_jmavsim": False,
            "success_criteria": "adapter_takeoff",
        },
    },
    "px4_jsbsim": {
        "name_prefix": "px4_jsbsim_quadx",
        "duration_s": 42.0,
        "target_altitude_m": 4.0,
        "adapter_max_runtime_s": 38.0,
        "adapter_join_timeout_s": 6.0,
        "backend_options": {
            "model": "quadrotor_x",
            "headless": True,
            "success_criteria": "adapter_takeoff",
        },
    },
    "px4_gazebo_classic": {
        "name_prefix": "px4_gazebo_classic_iris",
        "duration_s": 46.0,
        "target_altitude_m": 4.0,
        "adapter_max_runtime_s": 42.0,
        "adapter_join_timeout_s": 8.0,
        "backend_options": {
            "model": "iris",
            "world": "empty",
            "headless": True,
            "success_criteria": "adapter_takeoff",
        },
    },
}


ROS_BACKEND_DEFAULTS = {
    "marsim": {
        "name_prefix": "marsim",
        "duration_s": 18.0,
        "target_altitude_m": 1.0,
        "ready_timeout_s": 12.0,
        "join_timeout_s": 10.0,
        "required_subscribed_topics": [
            "/quad_0/lidar_slam/odom",
            "/quad0_pcl_render_node/cloud",
            "/map_generator/global_cloud",
        ],
        "required_published_topics": [
            "/quad_0/planning/pos_cmd",
        ],
        "backend_options": {
            "launch_rviz": False,
            "use_gpu": False,
            "command_topic": "/quad_0/planning/pos_cmd",
            "map_topic": "/map_generator/global_cloud",
            "success_criteria": "sensor_stack_with_commands",
        },
    },
    "fast_lio_marsim": {
        "name_prefix": "fast_lio_marsim",
        "duration_s": 20.0,
        "target_altitude_m": 1.0,
        "ready_timeout_s": 14.0,
        "join_timeout_s": 10.0,
        "required_subscribed_topics": [
            "/Odometry",
            "/quad0_pcl_render_node/sensor_cloud",
            "/map_generator/global_cloud",
        ],
        "required_published_topics": [
            "/quad_0/planning/pos_cmd",
        ],
        "backend_options": {
            "launch_rviz": False,
            "marsim_launch_rviz": False,
            "use_gpu": False,
            "command_topic": "/quad_0/planning/pos_cmd",
            "map_topic": "/map_generator/global_cloud",
            "success_criteria": "estimation_with_commands",
        },
    },
}


def build_custom_algorithm_scenario(
    adapter,
    command,
    name=None,
    output=None,
    backend=None,
    workdir=None,
    shell=False,
    duration_s=None,
    target_altitude_m=None,
    launch_rviz=None,
    use_gpu=None,
    required_subscribed_topics=None,
    required_published_topics=None,
):
    if adapter == "external_command":
        scenario = build_external_command_scenario(
            command=command,
            name=name,
            backend=backend or "px4_sih",
            workdir=workdir,
            shell=shell,
            duration_s=duration_s,
            target_altitude_m=target_altitude_m,
        )
    elif adapter == "ros_command":
        scenario = build_ros_command_scenario(
            command=command,
            name=name,
            backend=backend or "marsim",
            workdir=workdir,
            shell=shell,
            duration_s=duration_s,
            target_altitude_m=target_altitude_m,
            launch_rviz=launch_rviz,
            use_gpu=use_gpu,
            required_subscribed_topics=required_subscribed_topics,
            required_published_topics=required_published_topics,
        )
    else:
        raise ValueError("unsupported adapter for generator: {0}".format(adapter))

    scenario = normalize_scenario(scenario)
    output_path = resolve_output_path(output, scenario["name"])
    return scenario, output_path


def build_external_command_scenario(command, name, backend, workdir, shell, duration_s, target_altitude_m):
    if backend not in EXTERNAL_BACKEND_DEFAULTS:
        raise ValueError(
            "external_command generator supports backends: {0}".format(
                ", ".join(sorted(EXTERNAL_BACKEND_DEFAULTS))
            )
        )
    defaults = EXTERNAL_BACKEND_DEFAULTS[backend]
    scenario_name = name or "{0}_external_command_custom".format(defaults["name_prefix"])
    adapter = {
        "type": "external_command",
        "command": normalize_command(command, shell=shell),
        "max_runtime_s": float(duration_s or defaults["adapter_max_runtime_s"]),
        "join_timeout_s": float(defaults["adapter_join_timeout_s"]),
    }
    if workdir:
        adapter["workdir"] = str(resolve_platform_path(workdir))
    if shell:
        adapter["shell"] = True
    return {
        "schema_version": SCENARIO_SCHEMA_VERSION,
        "name": scenario_name,
        "description": "Generated custom control/decision algorithm scenario using external_command.",
        "backend": backend,
        "vehicle": "quadrotor",
        "duration_s": float(duration_s or defaults["duration_s"]),
        "update_hz": 5.0,
        "target_altitude_m": float(target_altitude_m or defaults["target_altitude_m"]),
        "algorithm_adapter": adapter,
        "backend_options": dict(defaults["backend_options"]),
    }


def build_ros_command_scenario(
    command,
    name,
    backend,
    workdir,
    shell,
    duration_s,
    target_altitude_m,
    launch_rviz,
    use_gpu,
    required_subscribed_topics,
    required_published_topics,
):
    if backend not in ROS_BACKEND_DEFAULTS:
        raise ValueError(
            "ros_command generator supports backends: {0}".format(
                ", ".join(sorted(ROS_BACKEND_DEFAULTS))
            )
        )
    defaults = ROS_BACKEND_DEFAULTS[backend]
    scenario_name = name or "{0}_ros_command_custom".format(defaults["name_prefix"])
    adapter = {
        "type": "ros_command",
        "command": normalize_command(command, shell=shell),
        "required_subscribed_topics": normalize_list(
            required_subscribed_topics,
            default=defaults["required_subscribed_topics"],
        ),
        "required_published_topics": normalize_list(
            required_published_topics,
            default=defaults["required_published_topics"],
        ),
        "ready_timeout_s": float(defaults["ready_timeout_s"]),
        "join_timeout_s": float(defaults["join_timeout_s"]),
    }
    if workdir:
        adapter["workdir"] = str(resolve_platform_path(workdir))
    if shell:
        adapter["shell"] = True
    backend_options = dict(defaults["backend_options"])
    if launch_rviz is not None:
        backend_options["launch_rviz"] = bool(launch_rviz)
        if backend == "fast_lio_marsim":
            backend_options["fast_lio_launch_rviz"] = bool(launch_rviz)
    if use_gpu is not None:
        backend_options["use_gpu"] = bool(use_gpu)
    return {
        "schema_version": SCENARIO_SCHEMA_VERSION,
        "name": scenario_name,
        "description": "Generated custom ROS planner/perception algorithm scenario using ros_command.",
        "backend": backend,
        "vehicle": "quadrotor",
        "duration_s": float(duration_s or defaults["duration_s"]),
        "update_hz": 5.0,
        "target_altitude_m": float(target_altitude_m or defaults["target_altitude_m"]),
        "algorithm_adapter": adapter,
        "backend_options": backend_options,
    }


def normalize_command(command, shell=False):
    if isinstance(command, list):
        if len(command) == 1:
            command_text = command[0]
        else:
            return [str(part) for part in command]
    else:
        command_text = str(command)
    if shell:
        return command_text
    return shlex.split(command_text)


def normalize_list(value, default):
    if value is None:
        return list(default)
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = value
    return [str(item).strip() for item in items if str(item).strip()]


def resolve_output_path(output, scenario_name):
    if output:
        return resolve_platform_path(output)
    return DEFAULT_OUTPUT_DIR / "{0}.json".format(scenario_name)


def write_scenario_file(scenario, output_path, force=False):
    path = resolve_platform_path(output_path)
    if path.exists() and not force:
        raise FileExistsError("scenario already exists, pass --force to overwrite: {0}".format(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_scenario(scenario)
    atomic_write_json(path, normalized)
    return path


def format_generated_scenario_help(scenario, output_path):
    return "\n".join(
        [
            "generated scenario: {0}".format(output_path),
            "adapter: {0}".format(scenario["algorithm_adapter"]["type"]),
            "backend: {0}".format(scenario["backend"]),
            "name: {0}".format(scenario["name"]),
            "",
            "run:",
            "python3 -m sim_plane run {0} --visualize --no-hold-open".format(output_path),
            "",
            "inspect:",
            "python3 -m sim_plane show-scenario {0}".format(output_path),
        ]
    )
