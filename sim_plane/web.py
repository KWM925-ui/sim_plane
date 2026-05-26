import json
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sim_plane.artifacts import read_jsonl


STATIC_DIR = Path(__file__).resolve().parent / "static"


class LiveRunState:
    def __init__(self, scenario, artifact_dir):
        self.scenario = scenario
        self.artifact_dir = str(artifact_dir)
        self.started_at = time.time()
        self.telemetry = []
        self.events = []
        self.result = None
        self.status = "starting"
        self.lock = threading.Lock()

    def append_telemetry(self, sample):
        with self.lock:
            self.telemetry.append(sample)
            self.status = "running"

    def append_event(self, event):
        with self.lock:
            self.events.append(event)

    def finalize(self, result):
        with self.lock:
            self.result = result
            self.status = result.get("status", "finished")

    def meta(self):
        return {
            "mode": "live",
            "scenario": self.scenario,
            "artifact_dir": self.artifact_dir,
        }

    def state(self):
        with self.lock:
            telemetry_count = len(self.telemetry)
            events_count = len(self.events)
            latest = self.telemetry[-1] if self.telemetry else None
            return {
                "status": self.status,
                "telemetry_count": telemetry_count,
                "events_count": events_count,
                "latest": latest,
                "result": self.result,
                "uptime_wall_s": round(time.time() - self.started_at, 2),
            }

    def get_telemetry(self, after_index):
        with self.lock:
            items = self.telemetry[after_index:]
            return {"items": items, "next_index": len(self.telemetry)}

    def get_events(self, after_index):
        with self.lock:
            items = self.events[after_index:]
            return {"items": items, "next_index": len(self.events)}


class ArtifactReplay:
    def __init__(self, artifact_dir):
        self.artifact_dir = Path(artifact_dir)
        self.manifest = load_json(self.artifact_dir / "manifest.json")
        self.scenario = load_json(self.artifact_dir / "scenario.json")
        self.result = load_json(self.artifact_dir / "result.json")
        self.telemetry = read_jsonl(self.artifact_dir / "telemetry.jsonl")
        self.events = read_jsonl(self.artifact_dir / "events.jsonl")

    def meta(self):
        return {
            "mode": "replay",
            "scenario": self.scenario,
            "artifact_dir": str(self.artifact_dir),
            "manifest": self.manifest,
        }

    def state(self):
        latest = self.telemetry[-1] if self.telemetry else None
        return {
            "status": self.result.get("status", "finished"),
            "telemetry_count": len(self.telemetry),
            "events_count": len(self.events),
            "latest": latest,
            "result": self.result,
            "uptime_wall_s": None,
        }

    def get_telemetry(self, after_index):
        return {"items": self.telemetry[after_index:], "next_index": len(self.telemetry)}

    def get_events(self, after_index):
        return {"items": self.events[after_index:], "next_index": len(self.events)}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class DashboardServer:
    def __init__(self, data_source, host="127.0.0.1", port=8765):
        self.data_source = data_source
        self.host = host
        self.port = port
        self.httpd = ThreadingHTTPServer((host, port), self._make_handler())
        self.thread = None

    def _make_handler(self):
        data_source = self.data_source

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/":
                    self._serve_static("index.html", "text/html; charset=utf-8")
                    return
                if parsed.path == "/app.js":
                    self._serve_static("app.js", "application/javascript; charset=utf-8")
                    return
                if parsed.path == "/styles.css":
                    self._serve_static("styles.css", "text/css; charset=utf-8")
                    return
                if parsed.path == "/api/meta":
                    self._json(data_source.meta())
                    return
                if parsed.path == "/api/state":
                    self._json(data_source.state())
                    return
                if parsed.path == "/api/telemetry":
                    query = urllib.parse.parse_qs(parsed.query)
                    after = int(query.get("after", ["0"])[0])
                    self._json(data_source.get_telemetry(after))
                    return
                if parsed.path == "/api/events":
                    query = urllib.parse.parse_qs(parsed.query)
                    after = int(query.get("after", ["0"])[0])
                    self._json(data_source.get_events(after))
                    return

                self.send_error(404, "Not found")

            def log_message(self, fmt, *args):
                return

            def _serve_static(self, filename, content_type):
                path = STATIC_DIR / filename
                payload = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                try:
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    return

            def _json(self, payload):
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    return

        return Handler

    @property
    def url(self):
        return "http://{0}:{1}".format(self.host, self.port)

    def start(self, open_browser=False):
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        if open_browser:
            webbrowser.open(self.url)

    def shutdown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2.0)
