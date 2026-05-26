from abc import ABC, abstractmethod


class BackendError(RuntimeError):
    """Raised when a backend cannot run."""


class Backend(ABC):
    name = "base"

    def validate_environment(self, scenario=None):
        return []

    @abstractmethod
    def run(self, scenario, sink):
        raise NotImplementedError
