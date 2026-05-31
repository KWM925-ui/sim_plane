import threading

from sim_plane.adapters.base import AdapterError


def available_adapters():
    from sim_plane.adapters.external_command import ExternalCommandAdapter
    from sim_plane.adapters.human_follow_ros import HumanFollowROSStage1Adapter
    from sim_plane.adapters.human_follow_ros_stage2 import HumanFollowROSStage2Adapter
    from sim_plane.adapters.mavsdk_action import MAVSDKActionAdapter
    from sim_plane.adapters.mavsdk_failure import MAVSDKFailureInjectionAdapter
    from sim_plane.adapters.ros_command import ROSCommandAdapter

    return {
        ExternalCommandAdapter.name: ExternalCommandAdapter,
        HumanFollowROSStage1Adapter.name: HumanFollowROSStage1Adapter,
        HumanFollowROSStage2Adapter.name: HumanFollowROSStage2Adapter,
        MAVSDKActionAdapter.name: MAVSDKActionAdapter,
        MAVSDKFailureInjectionAdapter.name: MAVSDKFailureInjectionAdapter,
        ROSCommandAdapter.name: ROSCommandAdapter,
    }


def normalize_algorithm_adapter_spec(spec):
    if spec is None:
        return None
    if isinstance(spec, str):
        return {"type": spec}
    if isinstance(spec, dict):
        if "type" not in spec:
            raise AdapterError("algorithm_adapter dictionaries must include a type field.")
        return dict(spec)
    raise AdapterError("algorithm_adapter must be null, a string, or a dictionary.")


def build_algorithm_adapter(spec):
    normalized = normalize_algorithm_adapter_spec(spec)
    if normalized is None:
        return None, None
    registry = available_adapters()
    adapter_type = normalized["type"]
    if adapter_type not in registry:
        raise AdapterError("Unknown algorithm adapter: {0}".format(adapter_type))
    return registry[adapter_type](), normalized


def validate_algorithm_adapter(spec, context=None):
    try:
        adapter, normalized = build_algorithm_adapter(spec)
    except AdapterError as exc:
        return [str(exc)]
    if adapter is None:
        return []

    issues = adapter.validate_environment(normalized, context=context)
    telemetry_port = extract_udp_port((context or {}).get("telemetry_endpoint"))
    system_address = resolve_adapter_system_address(adapter, normalized, context=context)
    adapter_port = extract_udp_port(system_address)
    if adapter.requires_dedicated_udp_port and telemetry_port is not None and adapter_port == telemetry_port:
        issues.append(
            "The algorithm adapter and telemetry collector both use UDP port {0}. "
            "Move backend_options.mavlink_endpoint to a separate PX4 telemetry port such as 14540 or 14550, "
            "and keep MAVSDK on PX4's onboard listener 14580.".format(
                adapter_port
            )
        )
    preferred_telemetry_port = (context or {}).get("preferred_telemetry_port")
    if (
        adapter.requires_dedicated_udp_port
        and telemetry_port is not None
        and preferred_telemetry_port is not None
        and telemetry_port != int(preferred_telemetry_port)
    ):
        issues.append(
            "The shared telemetry surface for {0} should use UDP port {1} when MAVSDK is active. "
            "Using port {2} can bind to PX4's onboard stream instead of the cleaner GCS stream.".format(
                (context or {}).get("backend", "this backend"),
                int(preferred_telemetry_port),
                telemetry_port,
            )
        )
    return issues


def extract_udp_port(address):
    from sim_plane.adapters.mavsdk_action import extract_udp_port as extract_action_udp_port

    return extract_action_udp_port(address)


def resolve_adapter_system_address(adapter, spec, context=None):
    if adapter.name == "mavsdk_failure_injection":
        from sim_plane.adapters.mavsdk_failure import resolve_mavsdk_system_address
    else:
        from sim_plane.adapters.mavsdk_action import resolve_mavsdk_system_address
    return resolve_mavsdk_system_address(spec, context=context)


def has_algorithm_adapter(spec):
    return spec is not None


class AlgorithmAdapterHandle:
    def __init__(self, adapter, spec, sink, context):
        self.adapter = adapter
        self.spec = spec
        self.sink = sink
        self.stop_event = threading.Event()
        self.context = dict(context or {})
        self.context["adapter_stop_event"] = self.stop_event
        self.report = None
        self.error = None
        self.thread = threading.Thread(
            target=self._run,
            name="sim-plane-algorithm-adapter",
            daemon=True,
        )

    def start(self):
        self.thread.start()

    def request_stop(self):
        self.stop_event.set()

    def _run(self):
        try:
            self.report = self.adapter.run(self.spec, self.sink, self.context) or {}
        except Exception as exc:
            self.error = str(exc)
            self.sink.emit_event(
                "error",
                "algorithm adapter failed",
                {"adapter": self.adapter.name, "error": self.error},
            )

    def collect(self, timeout_s, request_stop=False):
        if request_stop:
            self.request_stop()
        self.thread.join(timeout_s)
        base_metrics = {
            "algorithm_adapter_name": self.adapter.name,
            "algorithm_adapter_completed_successfully": False,
            "algorithm_adapter_stop_requested": self.stop_event.is_set(),
        }
        if self.thread.is_alive():
            return {
                "metrics": base_metrics,
                "notes": [
                    "The algorithm adapter did not finish before the backend shutdown window expired."
                    if not request_stop
                    else "The algorithm adapter did not stop before the backend shutdown window expired."
                ],
            }
        if self.error is not None:
            return {
                "metrics": base_metrics,
                "notes": [
                    "The algorithm adapter failed before completion: {0}".format(self.error)
                ],
            }
        metrics = dict(base_metrics)
        metrics.update((self.report or {}).get("metrics", {}))
        return {
            "metrics": metrics,
            "notes": list((self.report or {}).get("notes", [])),
        }


def start_algorithm_adapter(spec, sink, context=None):
    adapter, normalized = build_algorithm_adapter(spec)
    if adapter is None:
        return None
    handle = AlgorithmAdapterHandle(adapter, normalized, sink, context or {})
    handle.start()
    return handle


def collect_algorithm_adapter(handle, timeout_s, request_stop=False):
    if handle is None:
        return {"metrics": {}, "notes": []}
    return handle.collect(timeout_s, request_stop=request_stop)
