"""Loopback-only live inference; only landmarks are sent, never video frames."""
import json
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import joblib
import numpy as np

from .dataset import MODEL_PATH, digest
from .features import FEATURES, LABELS, VERSION, extract_features


def serve(args):
    root = Path(__file__).resolve().parents[1]
    artifact = joblib.load(args.model)  # Only load your own trusted local artifact.
    if artifact["feature_version"] != VERSION or tuple(artifact["features"]) != FEATURES or tuple(artifact["labels"]) != LABELS:
        raise ValueError("model feature contract does not match this application")
    pose_model = root / MODEL_PATH
    if not pose_model.exists() or digest(pose_model) != artifact["model_sha256"]:
        raise ValueError("local Pose asset must match the extraction asset")
    class Handler(SimpleHTTPRequestHandler):
        def send_json(self, status, value):
            payload = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/api/model":
                self.send_json(200, {"name": artifact["name"], "labels": LABELS, "feature_version": VERSION,
                                     "evaluation_mode": artifact.get("evaluation_mode", "trained local model"),
                                     "pose_model_url": "/models/pose_landmarker_lite.task"})
            else:
                super().do_GET()

        def do_POST(self):
            if self.path != "/api/predict":
                return self.send_json(404, {"error": "unknown endpoint"})
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size < 32768:
                    raise ValueError("invalid payload size")
                # Drain the bounded request before replying, so Windows does not
                # reset a connection with unread bytes and discard the response.
                payload = self.rfile.read(size)
                origin = self.headers.get("Origin")
                if origin and origin not in (f"http://127.0.0.1:{args.port}", f"http://localhost:{args.port}"):
                    return self.send_json(403, {"error": "same-origin local requests only"})
                body = json.loads(payload)
                values = extract_features(body["landmarks"], body["width"], body["height"])
                row = np.array([[values[k] for k in FEATURES]])
                predicted = int(artifact["model"].predict(row)[0])
                self.send_json(200, {"posture": LABELS[predicted], "model": artifact["name"]})
            except (ValueError, KeyError, TypeError, OverflowError) as e:
                self.send_json(422, {"error": str(e)})

        def log_message(self, fmt, *values):
            if self.path != "/api/predict":
                super().log_message(fmt, *values)
    print(f"Open http://127.0.0.1:{args.port}; Python prediction API is available at /api/predict. CTRL+C stops the server.")
    HTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(root))).serve_forever()
