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
from sim_plane.backends.px4_common import PX4_CANDIDATES, resolve_px4_dir
from sim_plane.runner import apply_runtime_options


class PX4SIHBackendTest(unittest.TestCase):
    def test_automatic_px4_discovery_only_uses_managed_workspace(self):
        self.assertEqual(
            PX4_CANDIDATES,
            [Path("/home/coco/sim_plane_ws/src/core/PX4-Autopilot")],
        )

    def test_explicit_and_environment_px4_paths_remain_supported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            explicit = root / "explicit"
            environment = root / "environment"
            for candidate in (explicit, environment):
                (candidate / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
                (candidate / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text(
                    "",
                    encoding="utf-8",
                )
                (candidate / "Tools").mkdir()

            with mock.patch("sim_plane.backends.px4_common.PX4_CANDIDATES", []), mock.patch.dict(
                "os.environ",
                {"PX4_AUTOPILOT_DIR": str(environment)},
                clear=True,
            ):
                self.assertEqual(resolve_px4_dir(explicit), explicit.resolve())
                self.assertEqual(resolve_px4_dir(), environment.resolve())

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
        with mock.patch("sim_plane.backends.px4_common.PX4_CANDIDATES", []):
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

    def test_parse_px4_height_estimate_warning_is_demoted_to_info(self):
        event = parse_px4_log_event(
            "px4_stdout",
            "stdout",
            "WARN  [health_and_arming_checks] Preflight Fail: height estimate not stable",
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
                "algorithm_adapter_target_altitude_reached": True,
                "target_altitude_reached": True,
            },
        )
        self.assertEqual(status, "passed")

    def test_evaluate_run_status_rejects_adapter_takeoff_without_adapter_altitude_confirmation(self):
        status = evaluate_run_status(
            "adapter_takeoff",
            {
                "algorithm_adapter_completed_successfully": True,
                "algorithm_adapter_target_altitude_reached": False,
                "target_altitude_reached": True,
            },
        )
        self.assertEqual(status, "failed")

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

    def test_run_requests_adapter_stop_when_collecting_report(self):
        backend = PX4SIHBackend()
        process = mock.Mock()
        process.poll.return_value = 0
        connection = mock.Mock()
        heartbeat = mock.Mock()
        heartbeat.get_srcSystem.return_value = 1
        heartbeat.get_srcComponent.return_value = 1
        scenario = {
            "name": "px4_sih_adapter_stop",
            "vehicle": "quadrotor",
            "algorithm_adapter": {"type": "external_command", "join_timeout_s": 1.0},
        }
        config = {
            "px4_dir": Path("/tmp/PX4-Autopilot"),
            "model": "sihsim_quadx",
            "mavlink_endpoint": "udpin:127.0.0.1:14540",
            "launch_qgc": False,
            "launch_jmavsim": False,
            "launch_rviz": False,
            "connect_timeout_s": 1.0,
            "shell_commands": [],
            "success_criteria": "telemetry",
            "collect_ulog": False,
            "collect_ulog_max_files": 0,
        }
        sink = mock.Mock()
        sink.artifact_writer = mock.Mock(artifact_dir=Path("/tmp/sim-plane-artifact"))
        adapter_handle = object()

        with mock.patch("sim_plane.backends.px4_sih.build_runtime_config", return_value=config), mock.patch(
            "sim_plane.backends.px4_sih.snapshot_px4_ulog_files", return_value=[]
        ), mock.patch("sim_plane.backends.px4_sih.launch_px4", return_value=process), mock.patch(
            "sim_plane.backends.px4_sih.mavutil.mavlink_connection", return_value=connection
        ), mock.patch(
            "sim_plane.backends.px4_sih.wait_for_heartbeat", return_value=heartbeat
        ), mock.patch(
            "sim_plane.backends.px4_sih.start_algorithm_adapter", return_value=adapter_handle
        ), mock.patch(
            "sim_plane.backends.px4_sih.stream_px4_telemetry", return_value={"telemetry_count": 1}
        ), mock.patch(
            "sim_plane.backends.px4_sih.collect_algorithm_adapter",
            return_value={"metrics": {}, "notes": []},
        ) as collect_mock, mock.patch(
            "sim_plane.backends.px4_sih.terminate_process"
        ), mock.patch(
            "sim_plane.backends.px4_sih.collect_px4_ulog_artifacts_safely", return_value={}
        ), mock.patch(
            "sim_plane.backends.px4_sih.px4_ulog_metrics", return_value={}
        ), mock.patch(
            "sim_plane.backends.px4_sih.px4_ulog_note", return_value="ulog unavailable"
        ):
            result = backend.run(scenario, sink)

        self.assertEqual(result["status"], "passed")
        collect_mock.assert_called_once_with(adapter_handle, timeout_s=1.0, request_stop=True)
        self.assertFalse(any(key.startswith("_sim_plane_internal") for key in scenario))


if __name__ == "__main__":
    unittest.main()
