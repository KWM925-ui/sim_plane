import errno
import fcntl
import json
import os
import socket
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import re

from sim_plane.io_utils import (
    append_jsonl,
    append_text_line,
    atomic_write_json,
    exclusive_file_lock,
)
from sim_plane.paths import get_platform_paths


RUNNING_MARKER = ".running"
COMPLETE_MARKER = ".complete"
LOCK_FILE = ".artifact.lock"
ROOT_LOCK_FILE = ".artifact-root.lock"
REQUIRED_ARTIFACT_FILES = ("manifest.json", "result.json", "events.jsonl")


def utc_timestamp():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def capture_git_state(repo_root=None):
    root = Path(repo_root) if repo_root is not None else get_platform_paths().home
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=str(root),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=str(root),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5.0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"kind": "git", "recorded": False, "commit": None, "dirty": None}
    commit = head.stdout.strip()
    if head.returncode != 0 or status.returncode != 0 or not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        return {"kind": "git", "recorded": False, "commit": None, "dirty": None}
    return {
        "kind": "git",
        "recorded": True,
        "commit": commit.lower(),
        "dirty": bool(status.stdout.strip()),
    }


def build_artifact_dir(root_dir, scenario_name):
    safe_name = safe_artifact_name(scenario_name)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    root = Path(root_dir)
    candidate = root / "{0}_{1}".format(safe_name, stamp)
    if not candidate.exists():
        return candidate
    for index in range(1, 1000):
        numbered = root / "{0}_{1}_{2:03d}".format(safe_name, stamp, index)
        if not numbered.exists():
            return numbered
    raise RuntimeError("could not allocate unique artifact directory for {0}".format(scenario_name))


def allocate_artifact_dir(root_dir, scenario_name):
    root = Path(root_dir)
    root.mkdir(parents=True, exist_ok=True)
    with artifact_root_lock(root):
        return _allocate_artifact_dir_locked(root, scenario_name)


def _allocate_artifact_dir_locked(root, scenario_name):
    safe_name = safe_artifact_name(scenario_name)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    for index in range(1000):
        suffix = "" if index == 0 else "_{0:03d}".format(index)
        candidate = root / "{0}_{1}{2}".format(safe_name, stamp, suffix)
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        atomic_write_json(
            candidate / RUNNING_MARKER,
            {
                "schema_version": 1,
                "state": "reserved",
                "reserved_at_utc": utc_timestamp(),
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
            },
        )
        return candidate
    raise RuntimeError("could not atomically allocate artifact directory for {0}".format(scenario_name))


def create_artifact_writer(root_dir, scenario, backend_name):
    root = Path(root_dir)
    root.mkdir(parents=True, exist_ok=True)
    with artifact_root_lock(root):
        artifact_dir = _allocate_artifact_dir_locked(root, scenario["name"])
        writer = ArtifactWriter(artifact_dir, scenario, backend_name)
        writer.initialize()
    return writer


def artifact_root_lock(root_dir):
    return exclusive_file_lock(Path(root_dir) / ROOT_LOCK_FILE)


def safe_artifact_name(value):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._")
    return safe or "artifact"


class ArtifactWriter:
    def __init__(self, artifact_dir, scenario, backend_name):
        self.artifact_dir = Path(artifact_dir)
        self.scenario = scenario
        self.backend_name = backend_name
        self.telemetry_path = self.artifact_dir / "telemetry.jsonl"
        self.events_path = self.artifact_dir / "events.jsonl"
        self.result_path = self.artifact_dir / "result.json"
        self.manifest_path = self.artifact_dir / "manifest.json"
        self.scenario_path = self.artifact_dir / "scenario.json"
        self.stdout_log_path = self.artifact_dir / "backend_stdout.log"
        self.stderr_log_path = self.artifact_dir / "backend_stderr.log"
        self.running_path = self.artifact_dir / RUNNING_MARKER
        self.complete_path = self.artifact_dir / COMPLETE_MARKER
        self.lock_path = self.artifact_dir / LOCK_FILE
        self._lock_handle = None
        self._started_at_utc = None
        self._write_lock = threading.RLock()
        self._accepting_writes = False

    def initialize(self):
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self._acquire_lock()
        try:
            self._initialize_locked()
        except Exception:
            self.close()
            raise

    def _initialize_locked(self):
        if self.manifest_path.exists() or self.result_path.exists() or self.complete_path.exists():
            raise RuntimeError("artifact directory is already initialized: {0}".format(self.artifact_dir))
        self._started_at_utc = utc_timestamp()
        atomic_write_json(
            self.running_path,
            {
                "schema_version": 1,
                "state": "running",
                "started_at_utc": self._started_at_utc,
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
            },
        )
        atomic_write_json(self.scenario_path, self.scenario)
        manifest = {
            "artifact_schema_version": 1,
            "created_at_utc": self._started_at_utc,
            "backend": self.backend_name,
            "scenario_name": self.scenario["name"],
            "vehicle": self.scenario["vehicle"],
            "artifact_dir": str(self.artifact_dir),
            "source_control": capture_git_state(),
            "lifecycle": {
                "state": "running",
                "started_at_utc": self._started_at_utc,
            },
            "files": {
                "scenario": "scenario.json",
                "telemetry": "telemetry.jsonl",
                "events": "events.jsonl",
                "result": "result.json",
                "backend_stdout": "backend_stdout.log",
                "backend_stderr": "backend_stderr.log",
            },
        }
        atomic_write_json(self.manifest_path, manifest)
        self.telemetry_path.touch()
        self.events_path.touch()
        self.stdout_log_path.touch()
        self.stderr_log_path.touch()
        self._accepting_writes = True

    def append_telemetry(self, sample):
        with self._write_lock:
            if not self._accepting_writes:
                return False
            append_jsonl(self.telemetry_path, sample)
            return True

    def append_event(self, event):
        with self._write_lock:
            if not self._accepting_writes:
                return False
            append_jsonl(self.events_path, event)
            return True

    def append_backend_log(self, stream_name, line):
        with self._write_lock:
            if not self._accepting_writes:
                return False
            if stream_name == "stdout":
                path = self.stdout_log_path
            else:
                path = self.stderr_log_path
            append_text_line(path, line)
            return True

    def write_result(self, result):
        with self._write_lock:
            if self._lock_handle is None:
                raise RuntimeError("artifact writer is not initialized or is already complete")
            self._accepting_writes = False
            try:
                payload = dict(result)
                payload["written_at_utc"] = utc_timestamp()
                atomic_write_json(self.result_path, payload)
                completed_at = utc_timestamp()
                manifest = read_json(self.manifest_path)
                manifest["lifecycle"] = {
                    "state": "complete",
                    "started_at_utc": self._started_at_utc,
                    "completed_at_utc": completed_at,
                    "result_status": payload.get("status"),
                }
                atomic_write_json(self.manifest_path, manifest)
                atomic_write_json(
                    self.complete_path,
                    {
                        "schema_version": 1,
                        "state": "complete",
                        "started_at_utc": self._started_at_utc,
                        "completed_at_utc": completed_at,
                        "result_status": payload.get("status"),
                        "pid": os.getpid(),
                    },
                )
                try:
                    self.running_path.unlink()
                except FileNotFoundError:
                    pass
            finally:
                self.close()

    def close(self):
        with self._write_lock:
            self._accepting_writes = False
            if self._lock_handle is None:
                return
            try:
                fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
            finally:
                self._lock_handle.close()
                self._lock_handle = None

    def _acquire_lock(self):
        if self._lock_handle is not None:
            raise RuntimeError("artifact writer is already initialized")
        handle = self.lock_path.open("a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                raise RuntimeError("artifact directory is active in another process: {0}".format(self.artifact_dir))
            raise
        self._lock_handle = handle

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def artifact_lifecycle_state(path):
    directory = Path(path)
    if not directory.is_dir():
        return "missing"
    required_present = all((directory / name).is_file() for name in REQUIRED_ARTIFACT_FILES)
    complete_marker = (directory / COMPLETE_MARKER).is_file()
    running_marker = (directory / RUNNING_MARKER).is_file()
    if complete_marker and required_present:
        return "complete"
    if running_marker:
        if artifact_lock_is_held(directory):
            return "active"
        return "stale_incomplete"
    if required_present:
        return "legacy_complete"
    return "incomplete"


def is_complete_artifact_dir(path):
    return artifact_lifecycle_state(path) in {"complete", "legacy_complete"}


def is_active_artifact_dir(path):
    return artifact_lifecycle_state(path) == "active"


def artifact_lock_is_held(path):
    return file_lock_is_held(Path(path) / LOCK_FILE)


def file_lock_is_held(lock_path):
    lock_path = Path(lock_path)
    if not lock_path.is_file():
        return False
    handle = lock_path.open("r")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                return True
            raise
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return False
    finally:
        handle.close()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    entries = []
    file_path = Path(path)
    if not file_path.exists():
        return entries
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
