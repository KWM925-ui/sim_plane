import json
from datetime import datetime
from pathlib import Path


def utc_timestamp():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def build_artifact_dir(root_dir, scenario_name):
    safe_name = scenario_name.replace(" ", "_")
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return Path(root_dir) / "{0}_{1}".format(safe_name, stamp)


class ArtifactWriter:
    def __init__(self, artifact_dir, scenario, backend_name):
        self.artifact_dir = Path(artifact_dir)
        self.scenario = scenario
        self.backend_name = backend_name
        self.telemetry_path = self.artifact_dir / "telemetry.jsonl"
        self.events_path = self.artifact_dir / "events.jsonl"
        self.result_path = self.artifact_dir / "result.json"
        self.manifest_path = self.artifact_dir / "manifest.json"
        self.scenario_path = self.artifact_dir / "scenario.json"
        self.stdout_log_path = self.artifact_dir / "backend_stdout.log"
        self.stderr_log_path = self.artifact_dir / "backend_stderr.log"

    def initialize(self):
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.scenario_path.write_text(
            json.dumps(self.scenario, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        manifest = {
            "created_at_utc": utc_timestamp(),
            "backend": self.backend_name,
            "scenario_name": self.scenario["name"],
            "vehicle": self.scenario["vehicle"],
            "artifact_dir": str(self.artifact_dir),
            "files": {
                "scenario": "scenario.json",
                "telemetry": "telemetry.jsonl",
                "events": "events.jsonl",
                "result": "result.json",
                "backend_stdout": "backend_stdout.log",
                "backend_stderr": "backend_stderr.log",
            },
        }
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self.stdout_log_path.touch()
        self.stderr_log_path.touch()

    def append_telemetry(self, sample):
        with self.telemetry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")

    def append_event(self, event):
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def append_backend_log(self, stream_name, line):
        if stream_name == "stdout":
            path = self.stdout_log_path
        else:
            path = self.stderr_log_path
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line.rstrip("\n") + "\n")

    def write_result(self, result):
        payload = dict(result)
        payload["written_at_utc"] = utc_timestamp()
        self.result_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def read_jsonl(path):
    entries = []
    file_path = Path(path)
    if not file_path.exists():
        return entries
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
