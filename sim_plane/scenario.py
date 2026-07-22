import copy
import json
from pathlib import Path

from sim_plane.paths import resolve_platform_path
from sim_plane.scenario_contract import (
    SCENARIO_SCHEMA_VERSION,
    ScenarioContractError,
    validate_scenario_contract,
)


DEFAULT_WAYPOINTS = [
    {"x": 0.0, "y": 0.0},
    {"x": 20.0, "y": 0.0},
    {"x": 20.0, "y": 20.0},
    {"x": 0.0, "y": 20.0},
    {"x": 0.0, "y": 0.0},
]


def load_scenario(path):
    scenario_path = resolve_platform_path(path).resolve()
    data = _load_scenario_data(scenario_path, stack=[])
    return normalize_scenario(data, scenario_path)


def normalize_scenario(data, source_path=None):
    if not isinstance(data, dict):
        raise ScenarioContractError("scenario must be a JSON object")
    scenario = copy.deepcopy(data)
    adapter = scenario.get("algorithm_adapter")
    if isinstance(adapter, str):
        scenario["algorithm_adapter"] = {"type": adapter}
    scenario.setdefault("schema_version", SCENARIO_SCHEMA_VERSION)
    scenario.setdefault("name", "unnamed_scenario")
    scenario.setdefault("description", "")
    scenario.setdefault("backend", "demo")
    scenario.setdefault("vehicle", "quadrotor")
    scenario.setdefault("duration_s", 18.0)
    scenario.setdefault("update_hz", 5.0)
    scenario.setdefault("target_altitude_m", 18.0)
    scenario.setdefault("realtime_factor", 4.0)
    scenario.setdefault("mission", {"type": "loop"})
    if "waypoints" not in scenario:
        mission = dict(scenario.get("mission") or {})
        scenario["waypoints"] = [] if mission.get("type") == "goal" else copy.deepcopy(DEFAULT_WAYPOINTS)
    scenario["waypoints"] = _canonicalize_waypoints(scenario["waypoints"])
    scenario.setdefault("algorithm_adapter", None)
    scenario.setdefault("backend_options", {})
    if source_path is not None:
        scenario["source_path"] = str(source_path)
    validate_scenario_contract(scenario)
    return scenario


def _canonicalize_waypoints(waypoints):
    if not isinstance(waypoints, list):
        return waypoints
    canonical = []
    for index, waypoint in enumerate(waypoints):
        if not isinstance(waypoint, dict):
            canonical.append(waypoint)
            continue
        item = dict(waypoint)
        for axis in ("x", "y", "z"):
            alias = "{0}_m".format(axis)
            if axis in item and alias in item and item[axis] != item[alias]:
                raise ScenarioContractError(
                    "scenario.waypoints[{0}] has conflicting {1} and {2}".format(
                        index, axis, alias
                    )
                )
            if axis not in item and alias in item:
                item[axis] = item[alias]
            item.pop(alias, None)
        canonical.append(item)
    return canonical


def validate_scenario(scenario):
    validate_scenario_contract(scenario)
    return scenario


def _load_scenario_data(scenario_path, stack):
    if scenario_path in stack:
        cycle = stack[stack.index(scenario_path):] + [scenario_path]
        raise ScenarioContractError(
            "scenario inheritance cycle: {0}".format(" -> ".join(str(path) for path in cycle))
        )
    if not scenario_path.is_file():
        raise ScenarioContractError("scenario file does not exist: {0}".format(scenario_path))
    try:
        data = json.loads(scenario_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioContractError(
            "scenario JSON is invalid at {0}:{1}:{2}: {3}".format(
                scenario_path,
                exc.lineno,
                exc.colno,
                exc.msg,
            )
        )
    if not isinstance(data, dict):
        raise ScenarioContractError("scenario must be a JSON object: {0}".format(scenario_path))

    declared_version = data.get("schema_version")
    if declared_version is not None and declared_version != SCENARIO_SCHEMA_VERSION:
        raise ScenarioContractError(
            "scenario.schema_version must be {0}: {1}".format(
                SCENARIO_SCHEMA_VERSION,
                scenario_path,
            )
        )

    extends = data.pop("extends", None)
    if extends is None:
        return data
    if not isinstance(extends, str) or not extends.strip():
        raise ScenarioContractError("scenario.extends must be a non-empty string: {0}".format(scenario_path))
    parent_path = Path(extends).expanduser()
    if not parent_path.is_absolute():
        parent_path = scenario_path.parent / parent_path
    parent_path = parent_path.resolve()
    parent = _load_scenario_data(parent_path, stack + [scenario_path])
    return deep_merge_scenario(parent, data)


def deep_merge_scenario(base, overrides):
    merged = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_scenario(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged
