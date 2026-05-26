import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path("/home/coco/sim_plane/scripts/sync_human_follow_stage1_workspace.py")
SPEC = importlib.util.spec_from_file_location("sync_human_follow_stage1_workspace", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SyncHumanFollowStage1WorkspaceTest(unittest.TestCase):
    def test_stage2_position_command_contract_package_is_synced(self):
        self.assertIn("quadrotor_msgs", MODULE.PACKAGES_TO_SYNC)

    def test_stage2_real_ego_vendor_packages_are_synced(self):
        for package_name in (
            "ego_planner_vendor/plan_env",
            "ego_planner_vendor/path_searching",
            "ego_planner_vendor/bspline_opt",
            "ego_planner_vendor/traj_utils",
            "ego_planner_vendor/ego_planner",
        ):
            self.assertIn(package_name, MODULE.PACKAGES_TO_SYNC)

    def test_bringup_excludes_lock_sim_specific_files(self):
        self.assertIn("config/mavros_px4_pluginlists_sitl.yaml", MODULE.BRINGUP_EXCLUDES)
        self.assertIn("launch/stage1_px4_mavros.launch", MODULE.BRINGUP_EXCLUDES)
        self.assertIn("launch/stage1_px4_mavros_sitl.launch", MODULE.BRINGUP_EXCLUDES)

    def test_protected_paths_match_bringup_excludes(self):
        protected_suffixes = {
            "src/human_follow_bringup/" + relative_path for relative_path in MODULE.BRINGUP_EXCLUDES
        }
        self.assertTrue(protected_suffixes.issubset(MODULE.PROTECTED_RELATIVE_PATHS))


if __name__ == "__main__":
    unittest.main()
