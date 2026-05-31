import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.backends.px4_gazebo_classic import (
    PX4GazeboClassicBackend,
    build_algorithm_adapter_context,
    build_runtime_config,
    prepare_gazebo_classic_env,
    parse_gazebo_classic_log_event,
    resolve_model_file,
    resolve_world_file,
    simulation_target_for_model,
)


class PX4GazeboClassicBackendTest(unittest.TestCase):
    def test_runtime_config_resolves_world_model_and_targets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text("", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "gazebo-classic").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_run.sh").write_text(
                "#!/usr/bin/env bash\n",
                encoding="utf-8",
            )
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "worlds").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "worlds" / "warehouse.world").write_text(
                "world\n",
                encoding="utf-8",
            )
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "models" / "iris").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "models" / "iris" / "iris.sdf").write_text(
                "model\n",
                encoding="utf-8",
            )
            (px4_root / "build" / "px4_sitl_default" / "bin").mkdir(parents=True)
            (px4_root / "build" / "px4_sitl_default" / "bin" / "px4").write_text("", encoding="utf-8")

            with mock.patch("sim_plane.backends.px4_gazebo_classic.resolve_executable", return_value=Path("/usr/bin/gazebo")):
                config = build_runtime_config(
                    {
                        "vehicle": "quadrotor",
                        "backend_options": {
                            "px4_dir": str(px4_root),
                            "world": "warehouse",
                            "launch_rviz": True,
                        },
                    }
                )
        self.assertEqual(config["model"], "iris")
        self.assertEqual(config["world"], "warehouse")
        self.assertTrue(config["launch_rviz"])
        self.assertEqual(config["simulation_target"], "gazebo-classic")
        self.assertTrue(config["gazebo_master_uri"].startswith("http://127.0.0.1:"))
        self.assertTrue(str(config["world_file"]).endswith("warehouse.world"))
        self.assertTrue(str(config["model_file"]).endswith("iris.sdf"))

    def test_validate_environment_reports_missing_world_or_model(self):
        backend = PX4GazeboClassicBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text("", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "gazebo-classic").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_run.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic").mkdir(parents=True)
            with mock.patch("sim_plane.backends.px4_gazebo_classic.resolve_executable", return_value=Path("/usr/bin/gazebo")):
                issues = backend.validate_environment(
                    {
                        "vehicle": "quadrotor",
                        "backend_options": {
                            "px4_dir": str(px4_root),
                            "world": "warehouse",
                            "model": "iris",
                        },
                    }
                )
        self.assertTrue(any("world file" in issue for issue in issues))
        self.assertTrue(any("model file" in issue for issue in issues))

    def test_validate_environment_reports_missing_gzclient_for_visual_mode(self):
        backend = PX4GazeboClassicBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text("", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "gazebo-classic").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_run.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "worlds").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "worlds" / "empty.world").write_text(
                "world\n",
                encoding="utf-8",
            )
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "models" / "iris").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "models" / "iris" / "iris.sdf").write_text(
                "model\n",
                encoding="utf-8",
            )

            def fake_resolve(name, extra_bin_dirs=None):
                if name == "gzclient":
                    return None
                return Path("/usr/bin") / name

            with mock.patch("sim_plane.backends.px4_gazebo_classic.resolve_executable", side_effect=fake_resolve):
                issues = backend.validate_environment(
                    {
                        "vehicle": "quadrotor",
                        "backend_options": {
                            "px4_dir": str(px4_root),
                            "headless": False,
                        },
                    }
                )
        self.assertTrue(any("gzclient" in issue for issue in issues))

    def test_resolve_helpers_and_target_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            world_dir = px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "worlds"
            model_dir = px4_root / "Tools" / "simulation" / "gazebo-classic" / "sitl_gazebo-classic" / "models" / "iris_depth_camera"
            world_dir.mkdir(parents=True)
            model_dir.mkdir(parents=True)
            (world_dir / "warehouse.world").write_text("world\n", encoding="utf-8")
            (model_dir / "iris_depth_camera.sdf.jinja").write_text("model\n", encoding="utf-8")
            world_file = resolve_world_file(px4_root, "warehouse")
            model_file = resolve_model_file(px4_root, "iris_depth_camera")
        self.assertEqual(world_file, world_dir / "warehouse.world")
        self.assertEqual(model_file, model_dir / "iris_depth_camera.sdf.jinja")
        self.assertEqual(simulation_target_for_model("iris"), "gazebo-classic")
        self.assertEqual(simulation_target_for_model("iris_depth_camera"), "gazebo-classic_iris_depth_camera")

    def test_parse_gazebo_classic_transient_preflight_warnings_are_demoted(self):
        ekf_event = parse_gazebo_classic_log_event(
            "px4_gazebo_classic_stdout",
            "stdout",
            "WARN  [health_and_arming_checks] Preflight Fail: ekf2 missing data",
        )
        power_event = parse_gazebo_classic_log_event(
            "px4_gazebo_classic_stdout",
            "stdout",
            "WARN  [health_and_arming_checks] Preflight Fail: system power unavailable",
        )
        self.assertEqual(ekf_event["level"], "info")
        self.assertEqual(power_event["level"], "info")

    def test_parse_gazebo_classic_harmless_stderr_noise_is_demoted(self):
        event = parse_gazebo_classic_log_event(
            "px4_gazebo_classic_stderr",
            "stderr",
            "libcurl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to fuel.gazebosim.org:443",
        )
        self.assertEqual(event["level"], "info")

    def test_prepare_gazebo_classic_env_isolates_master_uri_and_disables_model_db(self):
        config = {
            "toolchain_bin_dirs": [],
            "gazebo_master_uri": "http://127.0.0.1:45678",
            "speed_factor": 1.0,
            "headless": True,
            "home_lat": None,
            "home_lon": None,
            "home_alt": None,
        }
        env = prepare_gazebo_classic_env(config)
        self.assertEqual(env["GAZEBO_MASTER_URI"], "http://127.0.0.1:45678")
        self.assertEqual(env["GAZEBO_MODEL_DATABASE_URI"], "")

    def test_algorithm_adapter_context_passes_rviz_request(self):
        context = build_algorithm_adapter_context(
            {
                "vehicle": "quadrotor",
                "name": "gazebo_stage2_visual",
                "duration_s": 12.0,
                "target_altitude_m": 0.0,
            },
            {
                "launch_rviz": True,
                "mavlink_endpoint": "udpin:127.0.0.1:14550",
            },
        )
        self.assertTrue(context["launch_rviz"])
        self.assertEqual(context["backend"], "px4_gazebo_classic")


if __name__ == "__main__":
    unittest.main()
