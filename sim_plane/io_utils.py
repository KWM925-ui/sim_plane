import fcntl
import json
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path


REPORT_LOCK_FILE = ".report.lock"


def atomic_write_json(path, payload):
    atomic_write_text(
        path,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )


def atomic_write_text(path, text):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = None
    try:
        existing_mode = stat.S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        pass
    fd, temporary_name = tempfile.mkstemp(
        prefix=".{0}.".format(target.name),
        suffix=".tmp",
        dir=str(target.parent),
    )
    temporary = Path(temporary_name)
    try:
        if existing_mode is not None:
            os.fchmod(fd, existing_mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            handle.write(str(text))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(target))
    except Exception:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


@contextmanager
def exclusive_file_lock(path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def report_write_lock(report_root):
    return exclusive_file_lock(Path(report_root) / REPORT_LOCK_FILE)


def append_jsonl(path, payload):
    append_text_line(path, json.dumps(payload, ensure_ascii=False))


def append_text_line(path, line):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(str(line).rstrip("\n") + "\n")
            handle.flush()
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def prune_directories(root, pattern, keep_last, protected_dirs=None):
    if keep_last is None or keep_last <= 0:
        return []

    protected = {Path(path).resolve() for path in (protected_dirs or [])}
    candidates = sorted(
        (path for path in Path(root).glob(pattern) if path.is_dir()),
        key=lambda path: path.name,
    )
    pruned = []
    for path in candidates[:-keep_last]:
        if path.resolve() in protected:
            continue
        shutil.rmtree(path)
        pruned.append(str(path))
    return pruned
