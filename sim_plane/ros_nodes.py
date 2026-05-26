import subprocess
import time


def list_live_ros_nodes(env):
    try:
        listed = subprocess.check_output(
            ["rosnode", "list"],
            env=env,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None
    return set(line.strip() for line in listed.splitlines() if line.strip())


def cleanup_live_ros_nodes(
    nodes,
    sink,
    env,
    request_message,
    success_message=None,
    failure_message="ros node cleanup incomplete",
    sleep_s=1.0,
):
    if not nodes:
        return {"targets": [], "remaining": [], "returncode": None}

    live_nodes = list_live_ros_nodes(env)
    if live_nodes is None:
        return {"targets": [], "remaining": [], "returncode": None}

    targets = [node for node in nodes if node in live_nodes]
    if not targets:
        return {"targets": [], "remaining": [], "returncode": None}

    sink.emit_event("info", request_message, {"nodes": targets})
    result = subprocess.run(
        ["rosnode", "kill"] + targets,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(sleep_s)

    post_live_nodes = list_live_ros_nodes(env)
    remaining = [node for node in targets if post_live_nodes and node in post_live_nodes]
    if result.returncode != 0 or remaining:
        details = {"nodes": targets}
        if result.returncode != 0:
            details["returncode"] = result.returncode
            stderr = (result.stderr or "").strip()
            if stderr:
                details["stderr"] = stderr
        if remaining:
            details["remaining_nodes"] = remaining
        sink.emit_event("warning", failure_message, details)
    elif success_message:
        sink.emit_event("info", success_message, {"nodes": targets})

    return {
        "targets": targets,
        "remaining": remaining,
        "returncode": result.returncode,
    }
