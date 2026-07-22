import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.paths import get_platform_paths
from sim_plane.scenario import load_scenario, normalize_scenario
from sim_plane.scenario_contract import (
    ADAPTER_OPTION_KEYS,
    BACKEND_OPTION_KEYS,
    ScenarioContractError,
)


class ScenarioNormalizationTest(unittest.TestCase):
    def test_goal_mission_without_explicit_waypoints_does_not_get_default_loop(self):
        scenario = normalize_scenario(
            {
                "name": "goal_probe",
                "mission": {"type": "goal", "goal": {"x": 2.5, "y": 0.0, "z": 1.0}},
            }
        )

        self.assertEqual(scenario["waypoints"], [])

    def test_loop_mission_still_gets_default_waypoints(self):
        scenario = normalize_scenario({"name": "loop_probe"})

        self.assertGreaterEqual(len(scenario["waypoints"]), 2)

    def test_legacy_scenario_defaults_to_schema_version_one(self):
        scenario = normalize_scenario({"name": "legacy_probe"})

        self.assertEqual(scenario["schema_version"], 1)

    def test_unknown_top_level_field_is_rejected(self):
        with self.assertRaisesRegex(ScenarioContractError, "unsupported field.*typo"):
            normalize_scenario({"name": "bad_probe", "typo": True})

    def test_unknown_backend_option_is_rejected_for_selected_backend(self):
        with self.assertRaisesRegex(ScenarioContractError, "launch_flightgear"):
            normalize_scenario(
                {
                    "name": "bad_jsbsim_probe",
                    "backend": "px4_jsbsim",
                    "backend_options": {"launch_flightgear": False},
                }
            )

    def test_backend_option_type_is_checked(self):
        with self.assertRaisesRegex(ScenarioContractError, "headless must be a boolean"):
            normalize_scenario(
                {
                    "name": "bad_type_probe",
                    "backend": "px4_jsbsim",
                    "backend_options": {"headless": "false"},
                }
            )

    def test_unknown_adapter_option_is_rejected(self):
        with self.assertRaisesRegex(ScenarioContractError, "mystery"):
            normalize_scenario(
                {
                    "name": "bad_adapter_probe",
                    "algorithm_adapter": {
                        "type": "external_command",
                        "command": ["true"],
                        "mystery": 1,
                    },
                }
            )

    def test_waypoint_meter_aliases_are_canonicalized(self):
        scenario = normalize_scenario(
            {
                "name": "alias_probe",
                "waypoints": [{"x_m": 1.0, "y_m": 2.0, "z_m": 3.0}],
            }
        )

        self.assertEqual(scenario["waypoints"], [{"x": 1.0, "y": 2.0, "z": 3.0}])

    def test_conflicting_waypoint_aliases_are_rejected(self):
        with self.assertRaisesRegex(ScenarioContractError, "conflicting x"):
            normalize_scenario(
                {
                    "name": "conflicting_alias_probe",
                    "waypoints": [{"x": 1.0, "x_m": 2.0, "y": 0.0}],
                }
            )

    def test_invalid_adapter_null_and_shell_list_are_rejected(self):
        with self.assertRaisesRegex(ScenarioContractError, "max_runtime_s"):
            normalize_scenario(
                {
                    "name": "null_adapter_probe",
                    "algorithm_adapter": {
                        "type": "external_command",
                        "command": ["true"],
                        "max_runtime_s": None,
                    },
                }
            )

    def test_invalid_mission_env_and_udp_contracts_are_rejected(self):
        with self.assertRaisesRegex(ScenarioContractError, "mission.type is not supported"):
            normalize_scenario(
                {"name": "bad_mission_probe", "mission": {"type": "teleport"}}
            )
        with self.assertRaisesRegex(ScenarioContractError, "mission.goal is required"):
            normalize_scenario(
                {"name": "missing_goal_probe", "mission": {"type": "goal"}}
            )
        with self.assertRaisesRegex(ScenarioContractError, "missing coordinate"):
            normalize_scenario(
                {
                    "name": "partial_goal_probe",
                    "mission": {"type": "manual_goal", "goal": {"x": 1.0}},
                }
            )
        with self.assertRaisesRegex(ScenarioContractError, "string keys and values"):
            normalize_scenario(
                {
                    "name": "numeric_env_probe",
                    "algorithm_adapter": {
                        "type": "external_command",
                        "command": ["true"],
                        "env": {"RATE": 10},
                    },
                }
            )
        with self.assertRaisesRegex(ScenarioContractError, "udp_port must be at most 65535"):
            normalize_scenario(
                {
                    "name": "invalid_udp_probe",
                    "algorithm_adapter": {
                        "type": "mavsdk_action_takeoff",
                        "udp_port": 70000,
                    },
                }
            )
        with self.assertRaisesRegex(ScenarioContractError, "shell=true"):
            normalize_scenario(
                {
                    "name": "shell_list_probe",
                    "algorithm_adapter": {
                        "type": "external_command",
                        "command": ["printf", "ok"],
                        "shell": True,
                    },
                }
            )

    def test_invalid_range_and_safety_bounds_are_rejected(self):
        with self.assertRaisesRegex(ScenarioContractError, "max_horizontal_range_m"):
            normalize_scenario(
                {
                    "name": "negative_range_probe",
                    "degradations": {"measurement_saturation": {"max_horizontal_range_m": -1.0}},
                }
            )
        with self.assertRaisesRegex(ScenarioContractError, "must not exceed"):
            normalize_scenario(
                {
                    "name": "inverted_safety_probe",
                    "safety": {"min_altitude_m": 3.0, "max_altitude_m": 2.0},
                }
            )

    def test_inheritance_deep_merges_objects_and_replaces_lists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            parent = root / "parent.json"
            child = root / "child.json"
            parent.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "name": "parent",
                        "backend": "px4_jsbsim",
                        "waypoints": [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 1.0}],
                        "backend_options": {
                            "model": "quadrotor_x",
                            "headless": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            child.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "extends": "parent.json",
                        "name": "child",
                        "waypoints": [{"x": 2.0, "y": 3.0}],
                        "backend_options": {"headless": False},
                    }
                ),
                encoding="utf-8",
            )

            scenario = load_scenario(child)

        self.assertEqual(scenario["name"], "child")
        self.assertEqual(scenario["waypoints"], [{"x": 2.0, "y": 3.0}])
        self.assertEqual(
            scenario["backend_options"],
            {"model": "quadrotor_x", "headless": False},
        )
        self.assertEqual(scenario["source_path"], str(child))

    def test_inheritance_cycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            left = root / "left.json"
            right = root / "right.json"
            left.write_text(json.dumps({"extends": "right.json"}), encoding="utf-8")
            right.write_text(json.dumps({"extends": "left.json"}), encoding="utf-8")

            with self.assertRaisesRegex(ScenarioContractError, "inheritance cycle"):
                load_scenario(left)

    def test_inheritance_rejects_unsupported_declared_parent_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            parent = root / "parent.json"
            child = root / "child.json"
            parent.write_text(
                json.dumps({"schema_version": 2, "name": "parent"}),
                encoding="utf-8",
            )
            child.write_text(
                json.dumps({"schema_version": 1, "extends": "parent.json", "name": "child"}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ScenarioContractError, "schema_version"):
                load_scenario(child)

    def test_all_checked_in_scenarios_satisfy_contract(self):
        scenario_root = get_platform_paths().scenarios
        paths = sorted(scenario_root.glob("*.json"))
        raw = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        loaded = [load_scenario(path) for path in paths]

        self.assertGreaterEqual(len(loaded), 30)
        self.assertTrue(all(item.get("schema_version") == 1 for item in raw))
        self.assertTrue(all(item["schema_version"] == 1 for item in loaded))

    def test_contract_registries_cover_runtime_registries(self):
        from sim_plane.adapters import available_adapters
        from sim_plane.backends import available_backends

        self.assertEqual(set(BACKEND_OPTION_KEYS), set(available_backends()))
        self.assertEqual(set(ADAPTER_OPTION_KEYS), set(available_adapters()))


if __name__ == "__main__":
    unittest.main()
