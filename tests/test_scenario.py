import unittest

from sim_plane.scenario import normalize_scenario


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


if __name__ == "__main__":
    unittest.main()
