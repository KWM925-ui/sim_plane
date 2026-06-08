import unittest

from sim_plane.evaluation import compute_kpis, enrich_result_with_kpis


class EvaluationTest(unittest.TestCase):
    def test_compute_kpis_reports_altitude_path_and_sensor_quality(self):
        scenario = {
            "target_altitude_m": 2.0,
            "duration_s": 3.0,
            "waypoints": [
                {"x": 0.0, "y": 0.0},
                {"x": 2.0, "y": 0.0},
            ],
        }
        telemetry = [
            {
                "t": 0.0,
                "position": {"x_m": 0.0, "y_m": 0.0, "z_m": 0.0},
                "truth_position": {"x_m": 0.0, "y_m": 0.0, "z_m": 0.0},
                "altitude_m": 0.0,
                "speed_mps": 0.0,
                "sensor_visible": True,
            },
            {
                "t": 1.0,
                "position": {"x_m": 1.0, "y_m": 0.3, "z_m": -2.1},
                "truth_position": {"x_m": 1.0, "y_m": 0.0, "z_m": -2.0},
                "altitude_m": 2.1,
                "speed_mps": 1.0,
                "phase": "mission",
                "sensor_visible": True,
            },
            {
                "t": 2.0,
                "position": None,
                "truth_position": {"x_m": 2.0, "y_m": 0.0, "z_m": -2.0},
                "altitude_m": 2.0,
                "speed_mps": 0.5,
                "sensor_visible": False,
            },
        ]

        kpis = compute_kpis(scenario, telemetry)

        self.assertEqual(kpis["kpi_sample_count"], 3)
        self.assertEqual(kpis["kpi_sensor_dropout_count"], 1)
        self.assertAlmostEqual(kpis["kpi_sensor_dropout_ratio"], 1.0 / 3.0, places=5)
        self.assertEqual(kpis["kpi_altitude_overshoot_m"], 0.1)
        self.assertEqual(kpis["kpi_target_reach_time_s"], 1.0)
        self.assertEqual(kpis["kpi_mission_altitude_mae_m"], 0.1)
        self.assertEqual(kpis["kpi_path_error_max_m"], 0.3)
        self.assertEqual(kpis["kpi_mission_path_error_max_m"], 0.3)
        self.assertEqual(kpis["kpi_measurement_horizontal_error_max_m"], 0.3)
        self.assertEqual(kpis["kpi_measurement_vertical_error_max_m"], 0.1)
        self.assertEqual(kpis["kpi_plugin_count"], 9)
        self.assertIn("dynamics", kpis["kpi_plugin_names"])

    def test_enrich_result_preserves_existing_metrics_and_adds_kpis(self):
        result = {
            "status": "passed",
            "metrics": {
                "target_altitude_reached": True,
                "max_speed_mps": 8.0,
            },
        }
        scenario = {"target_altitude_m": 1.0, "duration_s": 1.0}
        telemetry = [
            {
                "t": 0.0,
                "position": {"x_m": 0.0, "y_m": 0.0, "z_m": -1.0},
                "altitude_m": 1.0,
                "speed_mps": 0.2,
            }
        ]

        enriched = enrich_result_with_kpis(result, scenario, telemetry)

        self.assertTrue(enriched["metrics"]["target_altitude_reached"])
        self.assertEqual(enriched["metrics"]["max_speed_mps"], 8.0)
        self.assertEqual(enriched["metrics"]["kpi_sample_count"], 1)

    def test_compute_kpis_reports_dynamics_safety_and_recovery(self):
        scenario = {
            "target_altitude_m": 2.0,
            "duration_s": 4.0,
            "control_limits": {"max_speed_mps": 1.0},
            "safety": {
                "min_altitude_m": 0.5,
                "max_altitude_m": 2.5,
                "max_radius_m": 3.0,
            },
        }
        telemetry = [
            {
                "t": 0.0,
                "position": {"x_m": 0.0, "y_m": 0.0, "z_m": 0.0},
                "altitude_m": 0.0,
                "speed_mps": 0.0,
                "sensor_visible": True,
            },
            {
                "t": 1.0,
                "position": None,
                "altitude_m": 1.0,
                "speed_mps": 1.5,
                "sensor_visible": False,
            },
            {
                "t": 2.0,
                "position": {"x_m": 4.0, "y_m": 0.0, "z_m": -2.0},
                "altitude_m": 2.0,
                "speed_mps": 0.5,
                "sensor_visible": True,
            },
            {
                "t": 3.0,
                "position": {"x_m": 0.0, "y_m": 0.0, "z_m": -2.7},
                "altitude_m": 2.7,
                "speed_mps": 0.0,
                "sensor_visible": True,
            },
        ]

        kpis = compute_kpis(scenario, telemetry)

        self.assertEqual(kpis["kpi_target_lost_count"], 1)
        self.assertEqual(kpis["kpi_target_reacquire_count"], 1)
        self.assertEqual(kpis["kpi_sensor_recovery_time_s"], 1.0)
        self.assertEqual(kpis["kpi_max_acceleration_mps2"], 1.5)
        self.assertEqual(kpis["kpi_speed_limit_violation_count"], 1)
        self.assertEqual(kpis["kpi_min_altitude_violation_count"], 1)
        self.assertEqual(kpis["kpi_max_altitude_violation_count"], 1)
        self.assertEqual(kpis["kpi_geofence_violation_count"], 1)
        self.assertEqual(kpis["kpi_safety_violation_count"], 3)

    def test_altitude_timing_ignores_samples_without_altitude(self):
        scenario = {"target_altitude_m": 2.0, "duration_s": 4.0}
        telemetry = [
            {"t": 0.0, "position": {"x_m": 0.0, "y_m": 0.0, "z_m": 0.0}},
            {"t": 1.0, "position": {"x_m": 0.0, "y_m": 0.0}},
            {"t": 2.0, "altitude_m": 1.0, "speed_mps": 0.0},
            {"t": 3.0, "altitude_m": 2.0, "speed_mps": 0.0},
            {"t": 4.0, "altitude_m": 2.0, "speed_mps": 0.0},
        ]

        kpis = compute_kpis(scenario, telemetry)

        self.assertEqual(kpis["kpi_target_reach_time_s"], 3.0)
        self.assertEqual(kpis["kpi_altitude_settle_time_s"], 3.0)

    def test_goal_mission_final_distance_uses_mission_goal_not_default_waypoints(self):
        scenario = {
            "mission": {"type": "goal", "goal": {"x": 2.5, "y": 0.0, "z": 1.0}},
            "waypoints": [
                {"x": 0.0, "y": 0.0},
                {"x": 0.0, "y": 0.0},
            ],
        }
        telemetry = [
            {
                "t": 0.0,
                "phase": "mission",
                "position": {"x_m": 2.45, "y_m": -0.005, "z_m": -1.02},
                "altitude_m": 1.02,
                "speed_mps": 0.1,
            }
        ]

        kpis = compute_kpis(scenario, telemetry)

        self.assertEqual(kpis["kpi_final_goal_distance_m"], 0.054)
        self.assertEqual(kpis["kpi_final_goal_horizontal_distance_m"], 0.05)
        self.assertEqual(kpis["kpi_final_goal_altitude_error_m"], 0.02)


if __name__ == "__main__":
    unittest.main()
