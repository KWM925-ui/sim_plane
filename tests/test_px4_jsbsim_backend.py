import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.backends.px4_jsbsim import (
    PX4JSBSimBackend,
    build_runtime_config,
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

    def test_validate_environment_reports_missing_jsbsim(self):
        backend = PX4JSBSimBackend()
        with mock.patch("sim_plane.backends.px4_jsbsim.JSBSIM_CANDIDATES", []):
            with mock.patch("sim_plane.backends.px4_jsbsim.resolve_px4_dir", return_value=Path("/tmp/PX4-Autopilot")):
                with mock.patch("sim_plane.backends.px4_jsbsim.resolve_toolchain_root", return_value=Path("/tmp/toolchains")):
                    issues = backend.validate_environment({"backend_options": {}, "vehicle": "quadrotor"})
        self.assertTrue(any("JSBSim" in issue for issue in issues))

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


if __name__ == "__main__":
    unittest.main()
