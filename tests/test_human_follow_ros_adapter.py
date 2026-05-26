import unittest
from pathlib import Path

from sim_plane.adapters import available_adapters
from sim_plane.adapters.human_follow_ros import (
    DEFAULT_FOLLOWER_WORKSPACE_CANDIDATES,
    build_runtime_config,
    resolve_workspace_dir,
)
from sim_plane.backends.px4_sih import evaluate_run_status


class HumanFollowROSStage1AdapterTest(unittest.TestCase):
    def test_adapter_is_registered(self):
        self.assertIn("human_follow_ros_stage1", available_adapters())

    def test_runtime_config_defaults_to_sitl_udp_and_offboard(self):
        config = build_runtime_config({}, {})
        self.assertEqual(config["fcu_url"], "udp://:14540@127.0.0.1:14557")
        self.assertEqual(config["request_mode"], "OFFBOARD")
        self.assertFalse(config["request_arm"])
        self.assertTrue(config["publish_external_odom"])
        self.assertEqual(config["cleanup_mode"], "AUTO.LOITER")
        self.assertEqual(config["post_success_keepalive_s"], 10.0)
        self.assertFalse(config["expect_follow_launch_exit"])
        self.assertEqual(config["follow_launch_exit_timeout_s"], 10.0)

    def test_runtime_config_uses_explicit_launch_names(self):
        workspace_dir = resolve_workspace_dir("/tmp/follower_ws")
        config = build_runtime_config(
            {
                "ros_workspace_dir": "/tmp/follower_ws",
                "mavros_launch": "stage1_px4_mavros.launch",
                "follow_launch": "stage1_truth_fusion_controller_regression.launch",
            },
            {},
        )
        self.assertEqual(config["mavros_launch_name"], "stage1_px4_mavros.launch")
        self.assertEqual(config["follow_launch_name"], "stage1_truth_fusion_controller_regression.launch")
        self.assertEqual(
            config["mavros_launch"],
            workspace_dir / "src" / "human_follow_bringup" / "launch" / "stage1_px4_mavros.launch",
        )
        self.assertEqual(
            config["follow_launch"],
            workspace_dir
            / "src"
            / "human_follow_bringup"
            / "launch"
            / "stage1_truth_fusion_controller_regression.launch",
        )

    def test_default_candidate_prefers_managed_workspace_root(self):
        self.assertEqual(
            DEFAULT_FOLLOWER_WORKSPACE_CANDIDATES[0],
            Path("/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1"),
        )

    def test_evaluate_run_status_accepts_adapter_completed(self):
        status = evaluate_run_status(
            "adapter_completed",
            {"algorithm_adapter_completed_successfully": True},
        )
        self.assertEqual(status, "passed")


if __name__ == "__main__":
    unittest.main()
