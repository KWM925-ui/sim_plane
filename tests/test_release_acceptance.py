import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.paths import get_platform_paths
from sim_plane.planner_acceptance import validate_acceptance_matrix
from sim_plane.platform_acceptance import validate_platform_matrix
from sim_plane.px4_failure_acceptance import validate_matrix as validate_px4_failure_matrix
from sim_plane.quadrotor_exam_acceptance import validate_matrix as validate_exam_matrix


class ReleaseAcceptanceContractTest(unittest.TestCase):
    def test_default_reference_acceptance_surfaces_are_complete(self):
        planner = validate_acceptance_matrix()
        platform = validate_platform_matrix()
        failure = validate_px4_failure_matrix()
        exam = validate_exam_matrix()

        self.assertEqual((planner["status"], len(planner["rows"])), ("passed", 4))
        self.assertEqual((platform["status"], len(platform["rows"])), ("passed", 21))
        self.assertEqual(platform["planner_acceptance"]["status"], "passed")
        self.assertEqual((failure["status"], len(failure["rows"])), ("passed", 1))
        self.assertEqual((exam["status"], len(exam["rows"])), ("passed", 8))

    def test_empty_row_matrices_fail_closed(self):
        root = get_platform_paths().home
        validators = (
            (validate_acceptance_matrix, root / "configs" / "planner_acceptance_matrix.json"),
            (validate_platform_matrix, root / "configs" / "platform_acceptance_matrix.json"),
            (validate_px4_failure_matrix, root / "configs" / "px4_failure_injection_acceptance_matrix.json"),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            for index, (validator, source) in enumerate(validators):
                payload = json.loads(source.read_text(encoding="utf-8"))
                payload["rows"] = []
                if validator is validate_platform_matrix:
                    payload["planner_acceptance_matrix"] = str(
                        root / "configs" / "planner_acceptance_matrix.json"
                    )
                matrix_path = Path(tmpdir) / "matrix_{0}.json".format(index)
                matrix_path.write_text(json.dumps(payload), encoding="utf-8")

                report = validator(path=matrix_path)

                self.assertEqual(report["status"], "failed")
                self.assertTrue(any("must not be empty" in issue for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
