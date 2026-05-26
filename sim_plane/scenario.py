import json
from pathlib import Path


DEFAULT_WAYPOINTS = [
    {"x": 0.0, "y": 0.0},
    {"x": 20.0, "y": 0.0},
    {"x": 20.0, "y": 20.0},
    {"x": 0.0, "y": 20.0},
    {"x": 0.0, "y": 0.0},
]


def load_scenario(path):
    scenario_path = Path(path)
    data = json.loads(scenario_path.read_text(encoding="utf-8"))
    return normalize_scenario(data, scenario_path)


def normalize_scenario(data, source_path=None):
    scenario = dict(data)
    scenario.setdefault("name", "unnamed_scenario")
    scenario.setdefault("description", "")
    scenario.setdefault("backend", "demo")
    scenario.setdefault("vehicle", "quadrotor")
    scenario.setdefault("duration_s", 18.0)
    scenario.setdefault("update_hz", 5.0)
    scenario.setdefault("target_altitude_m", 18.0)
    scenario.setdefault("realtime_factor", 4.0)
    scenario.setdefault("waypoints", list(DEFAULT_WAYPOINTS))
    scenario.setdefault("mission", {"type": "loop"})
    scenario.setdefault("algorithm_adapter", None)
    scenario.setdefault("backend_options", {})
    if source_path is not None:
        scenario["source_path"] = str(source_path)
    return scenario
