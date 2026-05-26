#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


def build_parser():
    parser = argparse.ArgumentParser(description="Clone or update structured upstream repos for sim_plane.")
    parser.add_argument(
        "--manifest",
        default="configs/upstreams.json",
        help="Path to the upstream manifest JSON file.",
    )
    parser.add_argument(
        "--workspace-root",
        help="Override the workspace root from the manifest.",
    )
    parser.add_argument(
        "--names",
        nargs="*",
        help="Only sync the named entries.",
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Do not clone or pull; only report current local status.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    workspace_root = Path(args.workspace_root or manifest["workspace_root"]).expanduser().resolve()
    entries = manifest["entries"]

    if args.names:
        wanted = set(args.names)
        entries = [entry for entry in entries if entry["name"] in wanted]

    workspace_root.mkdir(parents=True, exist_ok=True)
    print("workspace_root={0}".format(workspace_root))

    summary = []
    for entry in entries:
        repo_path = workspace_root / entry["path"]
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        if args.status_only:
            summary.append(report_status(entry, repo_path))
            continue
        if not repo_path.exists():
            clone_repo(entry, repo_path)
        else:
            update_repo(entry, repo_path)
        if entry.get("recursive"):
            update_submodules(entry, repo_path)
        summary.append(report_status(entry, repo_path))

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def clone_repo(entry, repo_path):
    command = ["git", "clone"]
    if entry.get("branch"):
        command.extend(["--branch", entry["branch"]])
    depth = entry.get("depth")
    if depth:
        command.extend(["--depth", str(depth)])
    if entry.get("recursive"):
        command.append("--recursive")
        if depth:
            command.extend(["--shallow-submodules"])
    command.extend([entry["url"], str(repo_path)])
    run(command, cwd=repo_path.parent)


def update_repo(entry, repo_path):
    run(["git", "fetch", "--all", "--tags", "--prune"], cwd=repo_path)
    branch = entry.get("branch")
    if branch:
        run(["git", "checkout", branch], cwd=repo_path)
        run(["git", "pull", "--ff-only", "origin", branch], cwd=repo_path)


def update_submodules(entry, repo_path):
    command = ["git", "submodule", "update", "--init", "--recursive"]
    depth = entry.get("depth")
    if depth:
        command.extend(["--depth", str(depth)])
    run(command, cwd=repo_path)


def report_status(entry, repo_path):
    exists = repo_path.exists()
    status = {
        "name": entry["name"],
        "path": str(repo_path),
        "exists": exists,
        "branch": entry.get("branch"),
        "url": entry["url"],
    }
    if not exists:
        return status

    status["head"] = capture(["git", "rev-parse", "HEAD"], cwd=repo_path).strip()
    status["head_short"] = capture(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path).strip()
    status["current_branch"] = capture(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path).strip()
    status["dirty"] = bool(capture(["git", "status", "--short"], cwd=repo_path).strip())
    return status


def run(command, cwd):
    print("$", " ".join(command))
    subprocess.run(command, cwd=str(cwd), check=True)


def capture(command, cwd):
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


if __name__ == "__main__":
    raise SystemExit(main())
