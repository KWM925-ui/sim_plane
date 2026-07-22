import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.backends.marsim import (
    MARSIMBackend,
    build_runtime_config,
    prepare_ros_runtime_env,
    stop_roslaunch,
)
from sim_plane.runner import apply_runtime_options


class MARSIMBackendTest(unittest.TestCase):
    def test_runtime_config_prefers_explicit_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "ros1_marsim"
            (workspace / "src").mkdir(parents=True)
            (workspace / "devel").mkdir(parents=True)
            (workspace / "devel" / "setup.bash").write_text("", encoding="utf-8")
            scenario = {
                "backend": "marsim",
                "vehicle": "quadrotor",
                "backend_options": {
                    "ros_workspace_dir": str(workspace),
                    "launch_rviz": False,
                    "use_gpu": True,
                },
            }
            config = build_runtime_config(scenario)
            self.assertEqual(config["workspace_dir"], workspace.resolve())
            self.assertFalse(config["launch_rviz"])
            self.assertTrue(config["use_gpu"])

    def test_runtime_options_merge_ros_overrides(self):
        scenario = {
            "backend": "marsim",
            "vehicle": "quadrotor",
            "backend_options": {},
        }
        merged = apply_runtime_options(
            scenario,
            {
                "launch_rviz": True,
                "ros_workspace_dir": "/tmp/ros1_marsim",
            },
        )
        self.assertTrue(merged["backend_options"]["launch_rviz"])
        self.assertEqual(merged["backend_options"]["ros_workspace_dir"], "/tmp/ros1_marsim")

    def test_validate_environment_reports_missing_workspace(self):
        backend = MARSIMBackend()
        with mock.patch("sim_plane.backends.marsim.DEFAULT_WORKSPACE_CANDIDATES", []):
            issues = backend.validate_environment({"backend_options": {}, "vehicle": "quadrotor"})
        self.assertTrue(any("workspace" in issue.lower() for issue in issues))

    def test_stop_roslaunch_prefers_parent_sigint(self):
        sink = mock.Mock()
        process = mock.Mock()
        process.pid = 2468
        process.poll.return_value = None
        with mock.patch("sim_plane.backends.marsim.os.killpg") as killpg, mock.patch(
            "sim_plane.backends.ros_runtime.process_group_exists", return_value=True
        ), mock.patch(
            "sim_plane.backends.ros_runtime.wait_for_process_group_exit", return_value=True
        ):
            stopped = stop_roslaunch(process, sink, "marsim", wait_timeout_s=4.0)
        self.assertTrue(stopped)
        killpg.assert_called_once()
        process.wait.assert_called_once()
        self.assertLessEqual(process.wait.call_args.kwargs["timeout"], 4.0)

    def test_prepare_ros_runtime_env_isolates_ros_logs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir) / "artifact"
            env = prepare_ros_runtime_env({"PATH": "/usr/bin"}, artifact_dir)
            self.assertEqual(env["PATH"], "/usr/bin")
            self.assertEqual(env["ROS_HOME"], str(artifact_dir / "ros_home"))
            self.assertEqual(env["ROS_LOG_DIR"], str(artifact_dir / "ros_logs"))
            self.assertEqual(env["ROS_HOSTNAME"], "127.0.0.1")
            self.assertEqual(env["ROS_IP"], "127.0.0.1")
            self.assertTrue((artifact_dir / "ros_home").is_dir())
            self.assertTrue((artifact_dir / "ros_logs").is_dir())

    def test_run_uses_longer_shutdown_timeout_for_gpu_visual(self):
        backend = MARSIMBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "ros1_marsim"
            (workspace / "src").mkdir(parents=True)
            (workspace / "devel").mkdir(parents=True)
            (workspace / "devel" / "setup.bash").write_text("", encoding="utf-8")
            artifact_dir = Path(tmpdir) / "artifact"
            sink = mock.Mock()
            sink.artifact_writer = mock.Mock(artifact_dir=str(artifact_dir))
            roslaunch_process = mock.Mock()
            telemetry_summary = {
                "telemetry_count": 1,
                "pointcloud_seen": True,
                "target_altitude_reached": True,
                "launch_rviz": True,
                "use_gpu": True,
            }
            scenario = {
                "name": "marsim_single_gpu_visual",
                "backend": "marsim",
                "vehicle": "quadrotor",
                "backend_options": {
                    "ros_workspace_dir": str(workspace),
                    "launch_rviz": True,
                    "use_gpu": True,
                },
            }
            with mock.patch.object(backend, "validate_environment", return_value=[]), mock.patch(
                "sim_plane.backends.marsim.load_sourced_environment",
                return_value={"PATH": "/usr/bin"},
            ), mock.patch(
                "sim_plane.backends.marsim.launch_roslaunch",
                return_value=roslaunch_process,
            ), mock.patch(
                "sim_plane.backends.marsim.launch_telemetry_probe",
                return_value=mock.Mock(),
            ), mock.patch(
                "sim_plane.backends.marsim.stream_telemetry",
                return_value=telemetry_summary,
            ), mock.patch(
                "sim_plane.backends.marsim.evaluate_run_status",
                return_value="passed",
            ), mock.patch(
                "sim_plane.backends.marsim.terminate_process",
            ), mock.patch(
                "sim_plane.backends.marsim.shutdown_specific_ros_nodes",
            ), mock.patch(
                "sim_plane.backends.marsim.stop_roslaunch",
                return_value=True,
            ) as stop_mock:
                result = backend.run(scenario, sink)
        self.assertEqual(result["status"], "passed")
        stop_mock.assert_called_once_with(roslaunch_process, sink, "marsim", wait_timeout_s=20.0)

    def test_run_keeps_default_shutdown_timeout_for_headless_cpu(self):
        backend = MARSIMBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "ros1_marsim"
            (workspace / "src").mkdir(parents=True)
            (workspace / "devel").mkdir(parents=True)
            (workspace / "devel" / "setup.bash").write_text("", encoding="utf-8")
            artifact_dir = Path(tmpdir) / "artifact"
            sink = mock.Mock()
            sink.artifact_writer = mock.Mock(artifact_dir=str(artifact_dir))
            roslaunch_process = mock.Mock()
            telemetry_summary = {
                "telemetry_count": 1,
                "pointcloud_seen": True,
                "target_altitude_reached": True,
                "launch_rviz": False,
                "use_gpu": False,
            }
            scenario = {
                "name": "marsim_single",
                "backend": "marsim",
                "vehicle": "quadrotor",
                "backend_options": {
                    "ros_workspace_dir": str(workspace),
                    "launch_rviz": False,
                    "use_gpu": False,
                },
            }
            with mock.patch.object(backend, "validate_environment", return_value=[]), mock.patch(
                "sim_plane.backends.marsim.load_sourced_environment",
                return_value={"PATH": "/usr/bin"},
            ), mock.patch(
                "sim_plane.backends.marsim.launch_roslaunch",
                return_value=roslaunch_process,
            ), mock.patch(
                "sim_plane.backends.marsim.launch_telemetry_probe",
                return_value=mock.Mock(),
            ), mock.patch(
                "sim_plane.backends.marsim.stream_telemetry",
                return_value=telemetry_summary,
            ), mock.patch(
                "sim_plane.backends.marsim.evaluate_run_status",
                return_value="passed",
            ), mock.patch(
                "sim_plane.backends.marsim.terminate_process",
            ), mock.patch(
                "sim_plane.backends.marsim.shutdown_specific_ros_nodes",
            ), mock.patch(
                "sim_plane.backends.marsim.stop_roslaunch",
                return_value=True,
            ) as stop_mock:
                result = backend.run(scenario, sink)
        self.assertEqual(result["status"], "passed")
        stop_mock.assert_called_once_with(roslaunch_process, sink, "marsim", wait_timeout_s=10.0)


if __name__ == "__main__":
    unittest.main()
