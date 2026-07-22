import os
import signal
import threading
import time


def start_log_threads(process, sink, prefix, event_parser=None):
    stdout_thread = threading.Thread(
        target=stream_process_output,
        args=(process.stdout, sink, "{0}_stdout".format(prefix), "stdout", event_parser),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=stream_process_output,
        args=(process.stderr, sink, "{0}_stderr".format(prefix), "stderr", event_parser),
        daemon=True,
    )
    register_background_threads(sink, stdout_thread, stderr_thread)
    stdout_thread.start()
    stderr_thread.start()
    return stdout_thread, stderr_thread


def register_background_threads(sink, *threads):
    register = getattr(sink, "register_background_thread", None)
    if register is None:
        return
    for thread in threads:
        register(thread)


def stream_process_output(stream, sink, label, stream_name, event_parser=None):
    if stream is None:
        return
    for raw_line in iter(stream.readline, ""):
        line = raw_line.rstrip()
        if not line:
            continue
        sink.emit_backend_log(stream_name, "[{0}] {1}".format(label, line))
        if event_parser is None:
            continue
        event = event_parser(label, stream_name, line)
        if event:
            sink.emit_event(
                event.get("level", "info"),
                event.get("message", "{0} log".format(label)),
                event.get("details", {"line": line}),
            )
    stream.close()


def terminate_process(
    process,
    sink,
    label,
    stop_signal=signal.SIGTERM,
    wait_timeout_s=8.0,
    use_process_group=True,
    forced_kill_level="warning",
):
    if process is None:
        return
    parent_running = process.poll() is None
    group_id = process.pid if use_process_group else None
    if use_process_group:
        if not process_group_exists(group_id):
            return
    elif not parent_running:
        return
    sink.emit_event(
        "info",
        "stopping process",
        {"label": label, "pid": process.pid, "signal": signal_name(stop_signal)},
    )
    deadline = time.monotonic() + max(float(wait_timeout_s), 0.0)
    try:
        if use_process_group:
            os.killpg(group_id, stop_signal)
        else:
            process.send_signal(stop_signal)
        if parent_running:
            process.wait(timeout=max(0.0, deadline - time.monotonic()))
    except Exception:
        pass

    if use_process_group:
        if wait_for_process_group_exit(group_id, max(0.0, deadline - time.monotonic())):
            return
    elif process.poll() is not None:
        return

    sink.emit_event(forced_kill_level, "forcing process kill", {"label": label, "pid": process.pid})
    try:
        if use_process_group:
            os.killpg(group_id, signal.SIGKILL)
        else:
            process.kill()
    except Exception:
        return
    try:
        process.wait(timeout=max(wait_timeout_s, 0.1))
    except Exception:
        sink.emit_event(
            "warning",
            "process did not exit after forced kill",
            {"label": label, "pid": process.pid},
        )


def process_group_exists(group_id):
    if group_id is None:
        return False
    try:
        os.killpg(int(group_id), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_for_process_group_exit(group_id, timeout_s):
    deadline = time.monotonic() + max(float(timeout_s), 0.0)
    while process_group_exists(group_id):
        if time.monotonic() >= deadline:
            return False
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    return True


def signal_name(signum):
    for candidate in dir(signal):
        if not candidate.startswith("SIG") or candidate.startswith("SIG_"):
            continue
        if getattr(signal, candidate) == signum:
            return candidate
    return str(signum)
