import json
import unittest
from pathlib import Path

from sim_plane.backends.planner_goal import (
    finalize_goal_reach_diagnostics,
    make_goal_reach_diagnostics,
    sample_time_seconds,
    update_goal_reach_diagnostics,
    update_goal_reach_state,
)


class PlannerGoalReachStateTest(unittest.TestCase):
    STRICT_PLANNER_SCENARIOS = [
        "ego_planner_marsim.json",
        "ego_planner_marsim_visual.json",
        "ego_planner_swarm_marsim.json",
        "ego_planner_swarm_marsim_visual.json",
        "ego_planner_fast_lio_marsim.json",
        "ego_planner_fast_lio_marsim_visual.json",
        "ego_planner_swarm_fast_lio_marsim.json",
        "ego_planner_swarm_fast_lio_marsim_visual.json",
    ]

    def test_zero_hold_reaches_on_first_in_tolerance_sample(self):
        reached, settled_since = update_goal_reach_state(
            goal_distance_m=0.013,
            speed_mps=0.0,
            tolerance_m=0.04,
            settle_speed_mps=0.25,
            settle_hold_s=0.0,
            settled_since=None,
            now=10.0,
        )

        self.assertTrue(reached)
        self.assertEqual(settled_since, 10.0)

    def test_distance_compare_uses_raw_metric_not_report_rounding(self):
        missed, _ = update_goal_reach_state(
            goal_distance_m=0.0400001,
            speed_mps=0.0,
            tolerance_m=0.04,
            settle_speed_mps=0.25,
            settle_hold_s=0.0,
            settled_since=None,
            now=10.0,
        )

        self.assertFalse(missed)

    def test_positive_hold_requires_elapsed_time(self):
        first_reached, settled_since = update_goal_reach_state(
            goal_distance_m=0.03,
            speed_mps=0.1,
            tolerance_m=0.04,
            settle_speed_mps=0.25,
            settle_hold_s=1.0,
            settled_since=None,
            now=10.0,
        )
        second_reached, settled_since = update_goal_reach_state(
            goal_distance_m=0.03,
            speed_mps=0.1,
            tolerance_m=0.04,
            settle_speed_mps=0.25,
            settle_hold_s=1.0,
            settled_since=settled_since,
            now=10.5,
        )
        third_reached, settled_since = update_goal_reach_state(
            goal_distance_m=0.03,
            speed_mps=0.1,
            tolerance_m=0.04,
            settle_speed_mps=0.25,
            settle_hold_s=1.0,
            settled_since=settled_since,
            now=11.0,
        )

        self.assertFalse(first_reached)
        self.assertFalse(second_reached)
        self.assertTrue(third_reached)
        self.assertEqual(settled_since, 10.0)

    def test_out_of_tolerance_resets_settle_state(self):
        reached, settled_since = update_goal_reach_state(
            goal_distance_m=0.2,
            speed_mps=0.0,
            tolerance_m=0.04,
            settle_speed_mps=0.25,
            settle_hold_s=1.0,
            settled_since=10.0,
            now=11.0,
        )

        self.assertFalse(reached)
        self.assertIsNone(settled_since)

    def test_non_finite_sample_never_reaches(self):
        for goal_distance_m, speed_mps in (
            (float("nan"), 0.0),
            (float("inf"), 0.0),
            (0.01, float("nan")),
            (0.01, float("inf")),
        ):
            reached, settled_since = update_goal_reach_state(
                goal_distance_m=goal_distance_m,
                speed_mps=speed_mps,
                tolerance_m=0.04,
                settle_speed_mps=0.25,
                settle_hold_s=0.0,
                settled_since=10.0,
                now=11.0,
            )

            self.assertFalse(reached)
            self.assertIsNone(settled_since)

    def test_sample_time_seconds_uses_sample_time_when_available(self):
        self.assertEqual(sample_time_seconds({"t": "2.5"}, fallback=10.0), 2.5)
        self.assertEqual(sample_time_seconds({"t": "nan"}, fallback=10.0), 10.0)
        self.assertEqual(sample_time_seconds({}, fallback=10.0), 10.0)

    def test_goal_diagnostics_explains_high_speed_nearest_point(self):
        diagnostics = make_goal_reach_diagnostics(
            tolerance_m=0.021,
            settle_speed_mps=0.25,
            settle_hold_s=0.2,
        )
        update_goal_reach_diagnostics(
            diagnostics,
            goal_distance_m=0.011,
            speed_mps=0.786,
            settled_since=None,
            now=2.355,
        )
        payload = finalize_goal_reach_diagnostics(diagnostics, goal_reached=False)

        self.assertEqual(payload["goal_reach_min_distance_m"], 0.011)
        self.assertEqual(payload["goal_reach_min_distance_speed_mps"], 0.786)
        self.assertEqual(payload["goal_reach_min_tolerance_margin_m"], 0.01)
        self.assertEqual(payload["goal_reach_failure_reason"], "within_tolerance_only_above_settle_speed")

    def test_goal_diagnostics_reports_insufficient_hold(self):
        diagnostics = make_goal_reach_diagnostics(
            tolerance_m=0.04,
            settle_speed_mps=0.25,
            settle_hold_s=0.2,
        )
        settled_since = 2.0
        update_goal_reach_diagnostics(
            diagnostics,
            goal_distance_m=0.03,
            speed_mps=0.1,
            settled_since=settled_since,
            now=2.1,
        )
        payload = finalize_goal_reach_diagnostics(diagnostics, goal_reached=False)

        self.assertEqual(payload["goal_reach_longest_settle_window_s"], 0.1)
        self.assertEqual(payload["goal_reach_failure_reason"], "settle_hold_not_met")

    def test_strict_planner_scenarios_require_nonzero_settle_hold(self):
        scenario_root = Path(__file__).resolve().parents[1] / "scenarios"
        for filename in self.STRICT_PLANNER_SCENARIOS:
            with self.subTest(filename=filename):
                scenario = json.loads((scenario_root / filename).read_text(encoding="utf-8"))
                hold_s = scenario["backend_options"]["goal_settle_hold_s"]
                self.assertGreater(hold_s, 0.0)


if __name__ == "__main__":
    unittest.main()
