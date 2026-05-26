import unittest

from sim_plane.doctor import collect_platform_doctor_report, format_platform_doctor_report


class DoctorReportTest(unittest.TestCase):
    def test_doctor_report_shape(self):
        report = collect_platform_doctor_report()

        self.assertIn("summary", report)
        self.assertIn("backends", report)
        self.assertIn("adapters", report)
        self.assertIn("recommendations", report)
        self.assertTrue(any(row["name"] == "demo" for row in report["backends"]))
        self.assertTrue(any(row["name"] == "external_command" for row in report["adapters"]))
        self.assertIn("platform_validation_path", report["recommendations"])
        self.assertIn("artifact_hygiene_path", report["recommendations"])

    def test_template_adapter_missing_command_is_note_not_blocker(self):
        report = collect_platform_doctor_report()
        adapters = {row["name"]: row for row in report["adapters"]}

        external = adapters["external_command"]
        ros_command = adapters["ros_command"]

        self.assertEqual("ready", external["status"])
        self.assertEqual([], external["blocking_issues"])
        self.assertTrue(any("template adapter ready" in note for note in external["notes"]))
        self.assertEqual("ready", ros_command["status"])
        self.assertEqual([], ros_command["blocking_issues"])
        self.assertTrue(any("template adapter ready" in note for note in ros_command["notes"]))

    def test_doctor_report_format_mentions_recommendations(self):
        report = collect_platform_doctor_report()
        rendered = format_platform_doctor_report(report)

        self.assertIn("sim_plane doctor", rendered)
        self.assertIn("recommendations:", rendered)
        self.assertIn("backends:", rendered)
        self.assertIn("adapters:", rendered)
        self.assertIn("platform_validation_path: latest platform acceptance", rendered)
        self.assertIn("artifact_hygiene_path: artifact hygiene", rendered)
        self.assertNotIn("first issue: The external_command adapter requires", rendered)
        self.assertIn("external_command: ready | note:", rendered)


if __name__ == "__main__":
    unittest.main()
