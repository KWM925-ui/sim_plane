import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.backends.px4_sih import (
    PX4SIHBackend,
    build_runtime_config,
    evaluate_run_status,
    is_px4_root,
    parse_px4_log_event,
    update_state_from_message,
)
from sim_plane.runner import apply_runtime_options


class PX4SIHBackendTest(unittest.TestCase):
    def test_px4_root_detection_and_runtime_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text("", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "jmavsim").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "jmavsim" / "jmavsim_run.sh").write_text(
                "#!/usr/bin/env bash\n",
                encoding="utf-8",
            )
            (px4_root / "build" / "px4_sitl_sih" / "bin").mkdir(parents=True)
            (px4_root / "build" / "px4_sitl_sih" / "bin" / "px4").write_text("", encoding="utf-8")

            self.assertTrue(is_px4_root(px4_root))

            scenario = {
                "vehicle": "quadrotor",
                "backend_options": {
                    "px4_dir": str(px4_root),
                    "launch_jmavsim": True,
                },
            }
            config = build_runtime_config(scenario)
            self.assertEqual(config["px4_dir"], px4_root.resolve())
            self.assertEqual(config["model"], "sihsim_quadx")
            self.assertTrue(str(config["jmavsim_script"]).endswith("jmavsim_run.sh"))
            self.assertEqual(config["connect_timeout_s"], 45.0)
            self.assertEqual(config["build_dir"], px4_root.resolve() / "build" / "px4_sitl_sih")
            self.assertTrue(config["collect_ulog"])
            self.assertEqual(config["collect_ulog_max_files"], 3)

    def test_runtime_options_merge_px4_overrides(self):
        scenario = {
            "backend": "px4_sih",
            "vehicle": "quadrotor",
            "backend_options": {},
        }
        merged = apply_runtime_options(
            scenario,
            {
                "px4_dir": "/tmp/PX4-Autopilot",
                "launch_qgc": True,
                "launch_jmavsim": True,
                "mavlink_endpoint": "udpin:127.0.0.1:14600",
                "model": "sihsim_airplane",
                "connect_timeout_s": 99.0,
            },
        )
        self.assertEqual(merged["backend_options"]["px4_dir"], "/tmp/PX4-Autopilot")
        self.assertTrue(merged["backend_options"]["launch_qgc"])
        self.assertTrue(merged["backend_options"]["launch_jmavsim"])
        self.assertEqual(merged["backend_options"]["mavlink_endpoint"], "udpin:127.0.0.1:14600")
        self.assertEqual(merged["backend_options"]["model"], "sihsim_airplane")
        self.assertEqual(merged["backend_options"]["connect_timeout_s"], 99.0)

    def test_validate_environment_reports_missing_px4(self):
        backend = PX4SIHBackend()
        with mock.patch("sim_plane.backends.px4_sih.PX4_CANDIDATES", []):
            with mock.patch.dict("os.environ", {}, clear=True):
                issues = backend.validate_environment({"backend_options": {}, "vehicle": "quadrotor"})
        self.assertTrue(any("PX4-Autopilot checkout not found" in issue for issue in issues))

    def test_parse_px4_heading_estimate_warning_is_demoted_to_info(self):
        event = parse_px4_log_event(
            "px4_stdout",
            "stdout",
            "WARN  [health_and_arming_checks] Preflight Fail: heading estimate invalid",
        )
        self.assertEqual(event["level"], "info")

    def test_parse_px4_other_warning_remains_warning(self):
        event = parse_px4_log_event(
            "px4_stdout",
            "stdout",
            "WARN  [foo] another warning",
        )
        self.assertEqual(event["level"], "warning")

    def test_evaluate_run_status_accepts_adapter_takeoff(self):
        status = evaluate_run_status(
            "adapter_takeoff",
            {
                "algorithm_adapter_completed_successfully": True,
                "target_altitude_reached": True,
            },
        )
        self.assertEqual(status, "passed")

    def test_runtime_config_defaults_early_stop_to_false(self):
        config = build_runtime_config({"backend_options": {}, "vehicle": "quadrotor"})
        self.assertFalse(config["allow_early_stop_on_adapter_success"])

    def test_runtime_config_reads_early_stop_flag(self):
        config = build_runtime_config(
            {
                "backend_options": {"allow_early_stop_on_adapter_success": True},
                "vehicle": "quadrotor",
            }
        )
        self.assertTrue(config["allow_early_stop_on_adapter_success"])

    def test_update_state_ignores_non_autopilot_heartbeat(self):
        class Heartbeat:
            base_mode = 0

            def get_type(self):
                return "HEARTBEAT"

            def get_srcComponent(self):
                return 190

        state = {
            "mode": "LOITER",
            "armed": True,
            "x_m": 0.0,
            "y_m": 0.0,
            "z_m": 0.0,
            "altitude_m": 0.0,
            "have_local_position": False,
            "speed_mps": 0.0,
            "battery_pct": None,
            "heading_deg": 0.0,
        }
        update_state_from_message(state, Heartbeat())
        self.assertEqual(state["mode"], "LOITER")
        self.assertTrue(state["armed"])


if __name__ == "__main__":
    unittest.main()
