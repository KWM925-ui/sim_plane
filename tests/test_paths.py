import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.paths import (
    PlatformPathError,
    discover_platform_home,
    get_platform_paths,
    resolve_platform_path,
)


class PlatformPathsTests(unittest.TestCase):
    def tearDown(self):
        get_platform_paths.cache_clear()

    def test_discovers_current_checkout_from_package_location(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SIM_PLANE_HOME", None)
            root = discover_platform_home()
        self.assertTrue((root / "pyproject.toml").is_file())
        self.assertEqual(root / "configs", get_platform_paths().configs)

    def test_explicit_home_is_authoritative(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(PlatformPathError, "explicit"):
                discover_platform_home(tmp)

    def test_invalid_environment_home_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"SIM_PLANE_HOME": tmp}):
                with self.assertRaisesRegex(PlatformPathError, "SIM_PLANE_HOME"):
                    discover_platform_home()

    def test_relative_paths_resolve_against_platform_home(self):
        home = get_platform_paths().home
        self.assertEqual(home / "runs" / "example", resolve_platform_path("runs/example"))

    def test_absolute_paths_are_preserved(self):
        path = Path("/tmp/sim_plane_absolute")
        self.assertEqual(path, resolve_platform_path(path))


if __name__ == "__main__":
    unittest.main()
