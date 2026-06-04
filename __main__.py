"""Repo-level launcher for ``python3 -m sim_plane`` from the parent directory.

When the current directory is ``/home/coco``, Python sees ``/home/coco/sim_plane``
as an outer namespace package before it sees the real package under
``/home/coco/sim_plane/sim_plane``. This shim redirects imports to the inner
package so the CLI works from both the repo root and its parent directory.
"""

from pathlib import Path
import os
import sys


REPO_ROOT = Path(__file__).resolve().parent
PACKAGE_DIR = REPO_ROOT / "sim_plane"

parent_package = sys.modules.get("sim_plane")
if parent_package is not None and hasattr(parent_package, "__path__"):
    parent_package.__path__ = [str(PACKAGE_DIR)]
    if getattr(parent_package, "__spec__", None) is not None:
        parent_package.__spec__.submodule_search_locations = [str(PACKAGE_DIR)]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.chdir(REPO_ROOT)

from sim_plane.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
