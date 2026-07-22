import time
import threading

from sim_plane.artifacts import create_artifact_writer, utc_timestamp
from sim_plane.backends.base import BackendError
from sim_plane.evaluation import enrich_result_with_kpis
from sim_plane.paths import resolve_platform_path
from sim_plane.scenario import load_scenario, normalize_scenario
from sim_plane.web import ArtifactReplay, ArtifactRootBrowser, DashboardServer, LiveRunState, is_complete_artifact_dir


class RunSink:
    def __init__(self, artifact_writer, live_state):
        self.artifact_writer = artifact_writer
        self.live_state = live_state
        self.telemetry = []
        self._background_threads = []
        self._background_threads_lock = threading.Lock()

    def emit_telemetry(self, sample):
        if self.artifact_writer.append_telemetry(sample):
            self.telemetry.append(sample)
            if self.live_state is not None:
                self.live_state.append_telemetry(sample)

    def emit_event(self, level, message, details=None):
        event = {
            "ts_utc": utc_timestamp(),
            "level": level,
            "message": message,
            "details": details or {},
        }
        if self.artifact_writer.append_event(event) and self.live_state is not None:
            self.live_state.append_event(event)

    def emit_backend_log(self, stream_name, line):
        self.artifact_writer.append_backend_log(stream_name, line)

    def register_background_thread(self, thread):
        with self._background_threads_lock:
            self._background_threads.append(thread)

    def wait_for_background_threads(self, timeout_s=3.0):
        deadline = time.monotonic() + max(float(timeout_s), 0.0)
        with self._background_threads_lock:
            threads = list(self._background_threads)
        for thread in threads:
            if thread is threading.current_thread():
                continue
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(remaining)
        return [thread.name for thread in threads if thread.is_alive()]


def get_backend(name):
    from sim_plane.backends import available_backends

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
    writer = create_artifact_writer(resolve_platform_path(artifact_root), scenario, backend_name)
    artifact_dir = writer.artifact_dir

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

    pending_threads = sink.wait_for_background_threads()
    if pending_threads:
        sink.emit_event(
            "warning",
            "background output threads did not drain before artifact completion",
            {"threads": pending_threads},
        )
    result = enrich_result_with_kpis(result, scenario, sink.telemetry)
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
    artifact_dir = resolve_platform_path(artifact_dir)
    if is_complete_artifact_dir(artifact_dir):
        data_source = ArtifactReplay(artifact_dir)
    else:
        data_source = ArtifactRootBrowser(artifact_dir)
    server = DashboardServer(data_source, host=host, port=port)
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
    resolve_platform_path(path).mkdir(parents=True, exist_ok=True)


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
    return normalize_scenario(merged, source_path=merged.get("source_path"))
