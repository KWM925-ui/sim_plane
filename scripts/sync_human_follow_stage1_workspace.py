#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_SOURCE_WS = Path("/home/coco/follwer_ws")
DEFAULT_MANAGED_WS = Path("/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1")
PACKAGES_TO_SYNC = [
    "human_follow_bringup",
    "human_follow_control",
    "human_follow_fusion",
    "human_follow_msgs",
    "human_follow_perception",
    "human_follow_px4_bridge",
    "quadrotor_msgs",
    "ego_planner_vendor/plan_env",
    "ego_planner_vendor/path_searching",
    "ego_planner_vendor/bspline_opt",
    "ego_planner_vendor/traj_utils",
    "ego_planner_vendor/ego_planner",
]
PROTECTED_RELATIVE_PATHS = {
    "src/CMakeLists.txt",
    "src/human_follow_bringup/config/mavros_px4_pluginlists_sitl.yaml",
    "src/human_follow_bringup/launch/stage1_px4_mavros.launch",
    "src/human_follow_bringup/launch/stage1_px4_mavros_sitl.launch",
}
BRINGUP_EXCLUDES = [
    "config/mavros_px4_pluginlists_sitl.yaml",
    "launch/stage1_px4_mavros.launch",
    "launch/stage1_px4_mavros_sitl.launch",
]


def run_command(command):
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "command failed: {0}\nstdout:\n{1}\nstderr:\n{2}".format(
                " ".join(command), completed.stdout, completed.stderr
            )
        )
    return completed


def remove_pycache(root_dir):
    removed = []
    for current_root, dirnames, filenames in os.walk(root_dir):
        for dirname in list(dirnames):
            if dirname == "__pycache__":
                full_path = Path(current_root) / dirname
                shutil.rmtree(full_path, ignore_errors=True)
                removed.append(str(full_path))
                dirnames.remove(dirname)
        for filename in filenames:
            if filename.endswith(".pyc"):
                full_path = Path(current_root) / filename
                full_path.unlink(missing_ok=True)
                removed.append(str(full_path))
    return removed


def ensure_workspace_shape(source_ws, managed_ws):
    if not (source_ws / "src").is_dir():
        raise RuntimeError("source workspace src missing: {0}".format(source_ws / "src"))
    if not (managed_ws / "src").is_dir():
        raise RuntimeError("managed workspace src missing: {0}".format(managed_ws / "src"))
    for relative_path in PROTECTED_RELATIVE_PATHS:
        protected_path = managed_ws / relative_path
        if not protected_path.exists():
            raise RuntimeError("protected managed path missing: {0}".format(protected_path))


def sync_package(source_ws, managed_ws, package_name, dry_run=False):
    source_dir = source_ws / "src" / package_name
    managed_dir = managed_ws / "src" / package_name
    if not source_dir.is_dir():
        raise RuntimeError("source package missing: {0}".format(source_dir))
    managed_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "rsync",
        "-a",
        "--delete",
        "--exclude=__pycache__/",
        "--exclude=*.pyc",
    ]
    if package_name == "human_follow_bringup":
        for exclude_pattern in BRINGUP_EXCLUDES:
            command.append("--exclude={0}".format(exclude_pattern))
    if dry_run:
        command.append("--dry-run")
    command.extend([str(source_dir) + "/", str(managed_dir) + "/"])
    return run_command(command)


def write_summary(source_ws, managed_ws, dry_run, package_results, pycache_removed):
    lines = []
    lines.append("human-follow stage1 managed workspace sync")
    lines.append("source_ws={0}".format(source_ws))
    lines.append("managed_ws={0}".format(managed_ws))
    lines.append("dry_run={0}".format("true" if dry_run else "false"))
    lines.append("protected_paths:")
    for relative_path in sorted(PROTECTED_RELATIVE_PATHS):
        lines.append("  - {0}".format(relative_path))
    lines.append("packages:")
    for package_name, result in package_results:
        stdout_lines = [line for line in result.stdout.splitlines() if line.strip()]
        lines.append("  - {0}: {1}".format(package_name, "changed" if stdout_lines else "clean"))
    lines.append("removed_pycache_entries={0}".format(len(pycache_removed)))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Sync the managed human-follow Stage1 workspace from the project workspace.")
    parser.add_argument("--source-ws", default=str(DEFAULT_SOURCE_WS))
    parser.add_argument("--managed-ws", default=str(DEFAULT_MANAGED_WS))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary-file", default="")
    args = parser.parse_args()

    source_ws = Path(args.source_ws).expanduser().resolve()
    managed_ws = Path(args.managed_ws).expanduser().resolve()
    ensure_workspace_shape(source_ws, managed_ws)

    pycache_removed = []
    if not args.dry_run:
        pycache_removed = remove_pycache(managed_ws / "src")
    package_results = []
    for package_name in PACKAGES_TO_SYNC:
        package_results.append((package_name, sync_package(source_ws, managed_ws, package_name, dry_run=args.dry_run)))

    summary = write_summary(source_ws, managed_ws, args.dry_run, package_results, pycache_removed)
    if args.summary_file:
        summary_path = Path(args.summary_file).expanduser()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary, encoding="utf-8")
    sys.stdout.write(summary)


if __name__ == "__main__":
    main()
