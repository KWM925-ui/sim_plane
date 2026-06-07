import unittest

from sim_plane.adapters import AlgorithmAdapterHandle


class AlgorithmAdapterHandleTest(unittest.TestCase):
    def test_non_dict_adapter_report_is_reported_as_adapter_failure(self):
        class BadAdapter:
            name = "bad_adapter"

            def run(self, spec, sink, context):
                return ({"metrics": {}},)

        class Sink:
            def __init__(self):
                self.events = []

            def emit_event(self, level, message, details=None):
                self.events.append((level, message, details or {}))

        sink = Sink()
        handle = AlgorithmAdapterHandle(BadAdapter(), {}, sink, {})
        handle.start()
        report = handle.collect(timeout_s=1.0)

        self.assertFalse(report["metrics"]["algorithm_adapter_completed_successfully"])
        self.assertIn("returned tuple, expected dict", report["notes"][0])
        self.assertTrue(
            any(
                event[0] == "error"
                and event[1] == "algorithm adapter failed"
                and "returned tuple, expected dict" in event[2].get("error", "")
                for event in sink.events
            )
        )


if __name__ == "__main__":
    unittest.main()
