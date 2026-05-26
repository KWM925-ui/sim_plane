import time
from pathlib import Path

from sim_plane.artifacts import ArtifactWriter, build_artifact_dir, utc_timestamp
from sim_plane.backends import available_backends
from sim_plane.backends.base import BackendError
from sim_plane.scenario import load_scenario
from sim_plane.web import ArtifactReplay, DashboardServer, LiveRunState


class RunSink:
    def __init__(self, artifact_writer, live_state):
        self.artifact_writer = artifact_writer
        self.live_state = live_state

    def emit_telemetry(self, sample):
        self.artifact_writer.append_telemetry(sample)
        if self.live_state is not None:
            self.live_state.append_telemetry(sample)

    def emit_event(self, level, message, details=None):
        event = {
            "ts_utc": utc_timestamp(),
            "level": level,
            "message": message,
            "details": details or {},
        }
        self.artifact_writer.append_event(event)
        if self.live_state is not None:
            self.live_state.append_event(event)

    def emit_backend_log(self, stream_name, line):
        self.artifact_writer.append_backend_log(stream_name, line)


def get_backend(name):
    registry = available_backends()
    if name not in registry:
        raise BackendError("Unknown backend: {0}".format(name))
    return registry[name]()


def run_scenario(
    scenario_path,
    backend_override=None,
    artifact_root="runs",
    visualize=False,
    host="127.0.0.1",
    port=8765,
    open_browser=False,
    hold_open=False,
    runtime_options=None,
):
    scenario = load_scenario(scenario_path)
    scenario = apply_runtime_options(scenario, runtime_options or {})
    backend_name = backend_override or scenario["backend"]
    backend = get_backend(backend_name)
    artifact_dir = build_artifact_dir(artifact_root, scenario["name"])
    writer = ArtifactWriter(artifact_dir, scenario, backend_name)
    writer.initialize()

    live_state = LiveRunState(scenario, artifact_dir) if visualize else None
    server = None
    if visualize:
        server = DashboardServer(live_state, host=host, port=port)
        server.start(open_browser=open_browser)

    sink = RunSink(writer, live_state)
    sink.emit_event("info", "run started", {"backend": backend_name, "scenario": scenario["name"]})
    issues = backend.validate_environment(scenario)
    for issue in issues:
        sink.emit_event("warning", "environment issue", {"message": issue})

    try:
        result = backend.run(scenario, sink)
    except Exception as exc:  # broad by design to preserve artifacts on failed runs
        result = {
            "status": "failed",
            "backend": backend_name,
            "vehicle": scenario["vehicle"],
            "scenario_name": scenario["name"],
            "error": str(exc),
        }
        sink.emit_event("error", "run failed", {"error": str(exc)})

    writer.write_result(result)
    if live_state is not None:
        live_state.finalize(result)

    if visualize and hold_open and server is not None:
        print("Dashboard is still available at {0}".format(server.url))
        print("Press Ctrl-C to stop the viewer.")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
    elif server is not None:
        server.shutdown()

    return {
        "artifact_dir": str(artifact_dir),
        "result": result,
        "dashboard_url": server.url if server is not None else None,
    }


def serve_artifact(artifact_dir, host="127.0.0.1", port=8765, open_browser=False):
    replay = ArtifactReplay(artifact_dir)
    server = DashboardServer(replay, host=host, port=port)
    server.start(open_browser=open_browser)
    print("Serving artifact dashboard at {0}".format(server.url))
    print("Press Ctrl-C to stop the viewer.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


def ensure_artifact_root(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def apply_runtime_options(scenario, runtime_options):
    if not runtime_options:
        return scenario

    merged = dict(scenario)
    backend_options = dict(merged.get("backend_options", {}))

    if runtime_options.get("px4_dir"):
        backend_options["px4_dir"] = runtime_options["px4_dir"]
    if runtime_options.get("launch_qgc"):
        backend_options["launch_qgc"] = True
    if runtime_options.get("disable_qgc"):
        backend_options["launch_qgc"] = False
    if runtime_options.get("launch_jmavsim"):
        backend_options["launch_jmavsim"] = True
    if runtime_options.get("disable_jmavsim"):
        backend_options["launch_jmavsim"] = False
    if runtime_options.get("launch_rviz"):
        backend_options["launch_rviz"] = True
    if runtime_options.get("disable_rviz"):
        backend_options["launch_rviz"] = False
    if runtime_options.get("ros_workspace_dir"):
        backend_options["ros_workspace_dir"] = runtime_options["ros_workspace_dir"]
    if runtime_options.get("mavlink_endpoint"):
        backend_options["mavlink_endpoint"] = runtime_options["mavlink_endpoint"]
    if runtime_options.get("model"):
        backend_options["model"] = runtime_options["model"]
    if runtime_options.get("connect_timeout_s") is not None:
        backend_options["connect_timeout_s"] = runtime_options["connect_timeout_s"]

    merged["backend_options"] = backend_options
    return merged
