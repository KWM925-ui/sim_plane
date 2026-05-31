import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sim_plane.adapters import available_adapters
from sim_plane.adapters.human_follow_ros_stage2 import build_adapter_notes, build_runtime_config


class HumanFollowROSStage2AdapterTest(unittest.TestCase):
    def test_adapter_is_registered(self):
        self.assertIn("human_follow_ros_stage2", available_adapters())

    def test_runtime_config_defaults(self):
        config = build_runtime_config({}, {})
        self.assertEqual(config["fcu_url"], "udp://:14540@127.0.0.1:14557")
        self.assertEqual(config["request_mode"], "OFFBOARD")
        self.assertTrue(config["request_arm"])
        self.assertTrue(config["require_estimator_valid"])
        self.assertEqual(config["cleanup_mode"], "AUTO.LOITER")
        self.assertEqual(config["ros_master_port"], 11371)
        self.assertEqual(config["min_goal_count"], 2)
        self.assertEqual(config["min_command_count"], 2)
        self.assertEqual(config["min_nonzero_setpoint_count"], 10)

    def test_runtime_config_uses_repo_local_stage2_launch_by_default(self):
        config = build_runtime_config({}, {})
        self.assertEqual(
            config["stage2_launch_path"],
            Path("/home/coco/sim_plane/sim_plane/ros/human_follow_stage2_real_ego_managed.launch"),
        )
        self.assertEqual(config["stage2_variant"], "real_ego")

    def test_non_real_ego_launch_is_classified_as_custom(self):
        with TemporaryDirectory() as temp_dir:
            custom_launch = Path(temp_dir) / "custom_stage2.launch"
            custom_launch.write_text("<launch />\n")
            config = build_runtime_config(
                {
                    "stage2_launch_path": str(custom_launch)
                },
                {},
            )
            self.assertEqual(config["stage2_variant"], "custom")

        default_config = build_runtime_config({}, {})
        self.assertEqual(default_config["stage2_variant"], "real_ego")

    def test_adapter_notes_name_selected_px4_backend(self):
        config = build_runtime_config({}, {"backend": "px4_gazebo_classic"})
        notes = build_adapter_notes(config)
        self.assertIn("PX4 Gazebo Classic + MAVROS", notes[0])


if __name__ == "__main__":
    unittest.main()
