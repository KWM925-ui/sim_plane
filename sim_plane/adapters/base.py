from abc import ABC, abstractmethod


class AdapterError(RuntimeError):
    """Raised when an algorithm adapter cannot run."""


class AlgorithmAdapter(ABC):
    name = "base"
    requires_dedicated_udp_port = False

    def validate_environment(self, spec=None, context=None):
        return []

    @abstractmethod
    def run(self, spec, sink, context):
        raise NotImplementedError
