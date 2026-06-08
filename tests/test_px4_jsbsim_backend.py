import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.backends.px4_jsbsim import (
    PX4JSBSimBackend,
    build_runtime_config,
    cmake_cache_needs_jsbsim_reconfigure,
    ensure_jsbsim_build,
    is_jsbsim_root,
    prepare_jsbsim_env,
    resolve_flightgear_binary,
    resolve_scene_file,
)


class PX4JSBSimBackendTest(unittest.TestCase):
    def test_jsbsim_root_detection_and_runtime_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text("", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "jsbsim").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "jsbsim" / "sitl_run.sh").write_text(
                "#!/usr/bin/env bash\n",
                encoding="utf-8",
            )
            (px4_root / "Tools" / "simulation" / "jsbsim" / "jsbsim_bridge" / "scene").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "jsbsim" / "jsbsim_bridge" / "scene" / "LSZH.xml").write_text(
                "<scene/>\n",
                encoding="utf-8",
            )
            (px4_root / "build" / "px4_sitl_default").mkdir(parents=True)

            jsbsim_root = px4_root.parent.parent / "toolchains" / "jsbsim"
            (jsbsim_root / "include" / "JSBSim").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "include" / "JSBSim" / "FGFDMExec.h").write_text("", encoding="utf-8")
            (jsbsim_root / "bin").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "bin" / "JSBSim").write_text("", encoding="utf-8")
            (jsbsim_root / "lib").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "lib" / "libJSBSim.a").write_text("", encoding="utf-8")

            self.assertTrue(is_jsbsim_root(jsbsim_root))

            scenario = {
                "vehicle": "quadrotor",
                "backend_options": {
                    "px4_dir": str(px4_root),
                    "jsbsim_root_dir": str(jsbsim_root),
                    "flightgear_binary": str(Path(tmpdir) / "fgfs"),
                },
            }
            Path(scenario["backend_options"]["flightgear_binary"]).write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            Path(scenario["backend_options"]["flightgear_binary"]).chmod(0o755)
            config = build_runtime_config(scenario)
            self.assertEqual(config["px4_dir"], px4_root.resolve())
            self.assertEqual(config["jsbsim_root_dir"], jsbsim_root.resolve())
            self.assertEqual(config["model"], "quadrotor_x")
            self.assertEqual(config["world"], "LSZH")
            self.assertTrue(str(config["sitl_script"]).endswith("sitl_run.sh"))
            self.assertTrue(str(config["scene_file"]).endswith("LSZH.xml"))
            self.assertTrue(str(config["flightgear_binary"]).endswith("fgfs"))
            self.assertEqual(config["build_dir"], px4_root.resolve() / "build" / "px4_sitl_default")
            self.assertTrue(config["collect_ulog"])
            self.assertEqual(config["collect_ulog_max_files"], 3)

    def test_validate_environment_reports_missing_jsbsim(self):
        backend = PX4JSBSimBackend()
        with mock.patch("sim_plane.backends.px4_jsbsim.JSBSIM_CANDIDATES", []):
            with mock.patch("sim_plane.backends.px4_jsbsim.resolve_px4_dir", return_value=Path("/tmp/PX4-Autopilot")):
                with mock.patch("sim_plane.backends.px4_jsbsim.resolve_toolchain_root", return_value=Path("/tmp/toolchains")):
                    issues = backend.validate_environment({"backend_options": {}, "vehicle": "quadrotor"})
        self.assertTrue(any("JSBSim" in issue for issue in issues))

    def test_validate_environment_reports_missing_build_directory(self):
        backend = PX4JSBSimBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text("", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "jsbsim").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "jsbsim" / "sitl_run.sh").write_text(
                "#!/usr/bin/env bash\n",
                encoding="utf-8",
            )
            (px4_root / "Tools" / "simulation" / "jsbsim" / "jsbsim_bridge" / "scene").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "jsbsim" / "jsbsim_bridge" / "scene" / "LSZH.xml").write_text(
                "<scene/>\n",
                encoding="utf-8",
            )
            jsbsim_root = Path(tmpdir) / "jsbsim"
            (jsbsim_root / "include" / "JSBSim").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "include" / "JSBSim" / "FGFDMExec.h").write_text("", encoding="utf-8")
            (jsbsim_root / "bin").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "bin" / "JSBSim").write_text("", encoding="utf-8")
            (jsbsim_root / "lib").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "lib" / "libJSBSim.a").write_text("", encoding="utf-8")

            issues = backend.validate_environment(
                {
                    "vehicle": "quadrotor",
                    "backend_options": {
                        "px4_dir": str(px4_root),
                        "jsbsim_root_dir": str(jsbsim_root),
                    },
                }
            )

        self.assertTrue(any("build directory" in issue for issue in issues))

    def test_validate_environment_reports_missing_build_products_and_stale_jsbsim_cache(self):
        backend = PX4JSBSimBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            self._write_px4_jsbsim_tree(px4_root)
            build_dir = px4_root / "build" / "px4_sitl_default"
            build_dir.mkdir(parents=True)
            (build_dir / "CMakeCache.txt").write_text(
                "JSBSIM_INCLUDE_DIR:PATH=JSBSIM_INCLUDE_DIR-NOTFOUND\n",
                encoding="utf-8",
            )
            jsbsim_root = self._write_jsbsim_root(Path(tmpdir) / "jsbsim")

            issues = backend.validate_environment(
                {
                    "vehicle": "quadrotor",
                    "backend_options": {
                        "px4_dir": str(px4_root),
                        "jsbsim_root_dir": str(jsbsim_root),
                    },
                }
            )

        self.assertTrue(any("PX4 JSBSim binary is missing" in issue for issue in issues))
        self.assertTrue(any("PX4 JSBSim bridge binary is missing" in issue for issue in issues))
        self.assertTrue(any("CMake cache did not discover JSBSim" in issue for issue in issues))

    def test_validate_environment_accepts_existing_jsbsim_build_products(self):
        backend = PX4JSBSimBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            self._write_px4_jsbsim_tree(px4_root)
            build_dir = px4_root / "build" / "px4_sitl_default"
            (build_dir / "bin").mkdir(parents=True)
            (build_dir / "bin" / "px4").write_text("", encoding="utf-8")
            (build_dir / "build_jsbsim_bridge").mkdir(parents=True)
            (build_dir / "build_jsbsim_bridge" / "jsbsim_bridge").write_text("", encoding="utf-8")
            jsbsim_root = self._write_jsbsim_root(Path(tmpdir) / "jsbsim")
            (build_dir / "CMakeCache.txt").write_text(
                "JSBSIM_INCLUDE_DIR:PATH={0}\n".format(jsbsim_root / "include" / "JSBSim"),
                encoding="utf-8",
            )

            issues = backend.validate_environment(
                {
                    "vehicle": "quadrotor",
                    "backend_options": {
                        "px4_dir": str(px4_root),
                        "jsbsim_root_dir": str(jsbsim_root),
                    },
                }
            )

        self.assertFalse(any("PX4 JSBSim binary is missing" in issue for issue in issues))
        self.assertFalse(any("PX4 JSBSim bridge binary is missing" in issue for issue in issues))
        self.assertFalse(any("CMake cache did not discover JSBSim" in issue for issue in issues))

    def test_validate_environment_reports_missing_flightgear_for_visual_mode(self):
        backend = PX4JSBSimBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text("", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "jsbsim").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "jsbsim" / "sitl_run.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "jsbsim" / "jsbsim_bridge" / "scene").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "jsbsim" / "jsbsim_bridge" / "scene" / "LSZH.xml").write_text(
                "<scene/>\n",
                encoding="utf-8",
            )
            jsbsim_root = Path(tmpdir) / "jsbsim"
            (jsbsim_root / "include" / "JSBSim").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "include" / "JSBSim" / "FGFDMExec.h").write_text("", encoding="utf-8")
            (jsbsim_root / "bin").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "bin" / "JSBSim").write_text("", encoding="utf-8")
            (jsbsim_root / "lib").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "lib" / "libJSBSim.a").write_text("", encoding="utf-8")
            with mock.patch("sim_plane.backends.px4_jsbsim.FLIGHTGEAR_BINARY_CANDIDATES", []), mock.patch.dict(
                "os.environ",
                {"FG_BINARY": ""},
                clear=False,
            ):
                issues = backend.validate_environment(
                    {
                        "vehicle": "quadrotor",
                        "backend_options": {
                            "px4_dir": str(px4_root),
                            "jsbsim_root_dir": str(jsbsim_root),
                            "headless": False,
                        },
                    }
                )
        self.assertTrue(any("fgfs" in issue for issue in issues))

    def test_validate_environment_reports_missing_scene_for_world(self):
        backend = PX4JSBSimBackend()
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
            (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text("", encoding="utf-8")
            (px4_root / "Tools" / "simulation" / "jsbsim").mkdir(parents=True)
            (px4_root / "Tools" / "simulation" / "jsbsim" / "sitl_run.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            jsbsim_root = Path(tmpdir) / "jsbsim"
            (jsbsim_root / "include" / "JSBSim").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "include" / "JSBSim" / "FGFDMExec.h").write_text("", encoding="utf-8")
            (jsbsim_root / "bin").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "bin" / "JSBSim").write_text("", encoding="utf-8")
            (jsbsim_root / "lib").mkdir(parents=True, exist_ok=True)
            (jsbsim_root / "lib" / "libJSBSim.a").write_text("", encoding="utf-8")
            issues = backend.validate_environment(
                {
                    "vehicle": "quadrotor",
                    "backend_options": {
                        "px4_dir": str(px4_root),
                        "jsbsim_root_dir": str(jsbsim_root),
                        "world": "KSFO",
                    },
                }
            )
        self.assertTrue(any("scene XML" in issue for issue in issues))

    def test_resolve_flightgear_binary_prefers_explicit_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fgfs = Path(tmpdir) / "fgfs"
            fgfs.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            fgfs.chmod(0o755)
            resolved = resolve_flightgear_binary(str(fgfs))
        self.assertEqual(resolved, fgfs.resolve())

    def test_resolve_scene_file_returns_matching_world_xml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            px4_root = Path(tmpdir) / "PX4-Autopilot"
            scene_dir = px4_root / "Tools" / "simulation" / "jsbsim" / "jsbsim_bridge" / "scene"
            scene_dir.mkdir(parents=True)
            (scene_dir / "LSZH.xml").write_text("<scene/>\n", encoding="utf-8")
            resolved = resolve_scene_file(px4_root, "LSZH")
        self.assertEqual(resolved, (scene_dir / "LSZH.xml"))

    def test_prepare_jsbsim_env_sets_flightgear_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fgfs = Path(tmpdir) / "bin" / "fgfs"
            fgfs.parent.mkdir(parents=True)
            fgfs.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            fgfs.chmod(0o755)
            artifact_dir = Path(tmpdir) / "artifact"
            config = {
                "toolchain_bin_dirs": [],
                "flightgear_binary": fgfs.resolve(),
                "headless": False,
                "speed_factor": 1.0,
                "jsbsim_root_dir": Path(tmpdir),
            }
            (Path(tmpdir) / "lib").mkdir(exist_ok=True)
            env = prepare_jsbsim_env(config, artifact_dir=artifact_dir)
        self.assertEqual(env["FG_BINARY"], str(fgfs.resolve()))
        self.assertEqual(env["FG_HOME"], str((artifact_dir / "flightgear_home").resolve()))
        self.assertTrue(env["PATH"].startswith(str(fgfs.parent.resolve())))

    def test_cmake_cache_needs_reconfigure_when_jsbsim_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_dir = Path(tmpdir) / "build"
            build_dir.mkdir()
            (build_dir / "CMakeCache.txt").write_text(
                "JSBSIM_INCLUDE_DIR:PATH=JSBSIM_INCLUDE_DIR-NOTFOUND\n",
                encoding="utf-8",
            )
            self.assertTrue(cmake_cache_needs_jsbsim_reconfigure({"build_dir": build_dir}))

    def test_ensure_jsbsim_build_reconfigures_then_builds_missing_bridge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            px4_root = root / "PX4-Autopilot"
            build_dir = px4_root / "build" / "px4_sitl_default"
            build_dir.mkdir(parents=True)
            jsbsim_root = self._write_jsbsim_root(root / "jsbsim")
            config = {
                "px4_dir": px4_root,
                "build_dir": build_dir,
                "build_target": "px4_sitl_default",
                "px4_binary": build_dir / "bin" / "px4",
                "jsbsim_bridge_binary": build_dir / "build_jsbsim_bridge" / "jsbsim_bridge",
                "jsbsim_root_dir": jsbsim_root,
                "toolchain_bin_dirs": [],
                "flightgear_binary": None,
                "headless": True,
                "speed_factor": 1.0,
                "build_jobs": 2,
            }
            sink = mock.Mock()

            def fake_build(command, cwd, env, sink, label, failure_message):
                if label == "px4_jsbsim_build":
                    config["px4_binary"].parent.mkdir(parents=True)
                    config["px4_binary"].write_text("", encoding="utf-8")
                    config["jsbsim_bridge_binary"].parent.mkdir(parents=True)
                    config["jsbsim_bridge_binary"].write_text("", encoding="utf-8")

            with mock.patch(
                "sim_plane.backends.px4_jsbsim.run_jsbsim_build_command",
                side_effect=fake_build,
            ) as run_mock:
                ensure_jsbsim_build(config, sink)

        labels = [call.kwargs["label"] for call in run_mock.call_args_list]
        self.assertEqual(labels, ["px4_jsbsim_configure", "px4_jsbsim_build"])
        configure_command = run_mock.call_args_list[0].args[0]
        build_command = run_mock.call_args_list[1].args[0]
        self.assertIn("-DJSBSIM_ROOT_DIR={0}".format(jsbsim_root), configure_command)
        self.assertIn("--target", build_command)
        target_index = build_command.index("--target")
        self.assertEqual(build_command[target_index + 1 : target_index + 3], ["px4", "jsbsim_bridge"])

    def test_run_requests_adapter_stop_when_collecting_report(self):
        backend = PX4JSBSimBackend()
        process = mock.Mock()
        process.poll.return_value = 0
        connection = mock.Mock()
        heartbeat = mock.Mock()
        heartbeat.get_srcSystem.return_value = 1
        heartbeat.get_srcComponent.return_value = 1
        scenario = {
            "name": "px4_jsbsim_adapter_stop",
            "vehicle": "quadrotor",
            "algorithm_adapter": {"type": "external_command", "join_timeout_s": 1.0},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_dir = root / "PX4-Autopilot" / "build" / "px4_sitl_default"
            build_dir.mkdir(parents=True)
            config = {
                "px4_dir": root / "PX4-Autopilot",
                "jsbsim_root_dir": root / "jsbsim",
                "sitl_script": root / "PX4-Autopilot" / "sitl_run.sh",
                "build_dir": build_dir,
                "scene_file": root / "PX4-Autopilot" / "scene" / "LSZH.xml",
                "model": "quadrotor_x",
                "world": "LSZH",
                "build_target": "px4_sitl_default",
                "mavlink_endpoint": "udpin:127.0.0.1:14540",
                "headless": True,
                "launch_qgc": False,
                "flightgear_binary": None,
                "connect_timeout_s": 1.0,
                "shell_commands": [],
                "success_criteria": "telemetry",
                "collect_ulog": False,
                "collect_ulog_max_files": 0,
            }
            sink = mock.Mock()
            sink.artifact_writer = mock.Mock(artifact_dir=root / "artifact")
            adapter_handle = object()

            with mock.patch("sim_plane.backends.px4_jsbsim.build_runtime_config", return_value=config), mock.patch(
                "sim_plane.backends.px4_jsbsim.snapshot_px4_ulog_files", return_value=[]
            ), mock.patch("sim_plane.backends.px4_jsbsim.ensure_jsbsim_build"), mock.patch(
                "sim_plane.backends.px4_jsbsim.launch_px4_jsbsim", return_value=process
            ), mock.patch(
                "sim_plane.backends.px4_jsbsim.mavutil.mavlink_connection", return_value=connection
            ), mock.patch(
                "sim_plane.backends.px4_jsbsim.wait_for_heartbeat", return_value=heartbeat
            ), mock.patch(
                "sim_plane.backends.px4_jsbsim.start_algorithm_adapter", return_value=adapter_handle
            ), mock.patch(
                "sim_plane.backends.px4_jsbsim.stream_jsbsim_telemetry", return_value={"telemetry_count": 1}
            ), mock.patch(
                "sim_plane.backends.px4_jsbsim.collect_algorithm_adapter",
                return_value={"metrics": {}, "notes": []},
            ) as collect_mock, mock.patch(
                "sim_plane.backends.px4_jsbsim.terminate_process"
            ), mock.patch(
                "sim_plane.backends.px4_jsbsim.collect_px4_ulog_artifacts_safely", return_value={}
            ), mock.patch(
                "sim_plane.backends.px4_jsbsim.px4_ulog_metrics", return_value={}
            ), mock.patch(
                "sim_plane.backends.px4_jsbsim.px4_ulog_note", return_value="ulog unavailable"
            ):
                result = backend.run(scenario, sink)

        self.assertEqual(result["status"], "passed")
        collect_mock.assert_called_once_with(adapter_handle, timeout_s=1.0, request_stop=True)

    def _write_px4_jsbsim_tree(self, px4_root):
        (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix").mkdir(parents=True)
        (px4_root / "ROMFS" / "px4fmu_common" / "init.d-posix" / "rcS").write_text("", encoding="utf-8")
        (px4_root / "Tools" / "simulation" / "jsbsim").mkdir(parents=True)
        (px4_root / "Tools" / "simulation" / "jsbsim" / "sitl_run.sh").write_text(
            "#!/usr/bin/env bash\n",
            encoding="utf-8",
        )
        scene_dir = px4_root / "Tools" / "simulation" / "jsbsim" / "jsbsim_bridge" / "scene"
        scene_dir.mkdir(parents=True)
        (scene_dir / "LSZH.xml").write_text("<scene/>\n", encoding="utf-8")

    def _write_jsbsim_root(self, jsbsim_root):
        (jsbsim_root / "include" / "JSBSim").mkdir(parents=True, exist_ok=True)
        (jsbsim_root / "include" / "JSBSim" / "FGFDMExec.h").write_text("", encoding="utf-8")
        (jsbsim_root / "bin").mkdir(parents=True, exist_ok=True)
        (jsbsim_root / "bin" / "JSBSim").write_text("", encoding="utf-8")
        (jsbsim_root / "lib").mkdir(parents=True, exist_ok=True)
        (jsbsim_root / "lib" / "libJSBSim.a").write_text("", encoding="utf-8")
        return jsbsim_root


if __name__ == "__main__":
    unittest.main()
