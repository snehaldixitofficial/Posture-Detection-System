"""Loopback API integration using a temporary synthetic model, not research data."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from research.dataset import MODEL_PATH, digest
from research.features import FEATURES, LABELS, VERSION
from research import server
from test_research import fixture_landmarks


@unittest.skipUnless(MODEL_PATH.is_file(), "download the Pose asset for API integration")
class ServerTests(unittest.TestCase):
    def test_metadata_predictions_and_quality_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            model = RandomForestClassifier(n_estimators=2, random_state=42).fit(
                np.random.default_rng(42).normal(size=(8, len(FEATURES))), np.arange(8) % 4)
            path = Path(folder) / "fixture.joblib"
            joblib.dump(dict(model=model, name="fixture", features=FEATURES, labels=LABELS,
                             feature_version=VERSION, model_sha256=digest(MODEL_PATH)), path)
            real_server, ready, running = server.HTTPServer, threading.Event(), []
            def factory(address, handler):
                instance = real_server(address, handler)
                running.append(instance)
                ready.set()
                return instance
            with patch.object(server, "HTTPServer", factory):
                thread = threading.Thread(target=server.serve, args=(SimpleNamespace(model=str(path), port=0),), daemon=True)
                thread.start()
                self.assertTrue(ready.wait(5), "server failed to start")
                instance = running[0]
                base = f"http://127.0.0.1:{instance.server_address[1]}"
                try:
                    with urlopen(base + "/api/model", timeout=5) as response:
                        self.assertEqual(json.load(response)["feature_version"], VERSION)
                    with urlopen(base + "/", timeout=5) as response:
                        self.assertIn(b"classifier-mode", response.read())
                    body = dict(landmarks=fixture_landmarks(), width=800, height=600)
                    for i in range(13, 33):
                        body["landmarks"][i] = None
                    request = Request(base + "/api/predict", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
                    with urlopen(request, timeout=5) as response:
                        self.assertIn(json.load(response)["posture"], LABELS)
                    body["landmarks"][11]["visibility"] = .1
                    request.data = json.dumps(body).encode()
                    with self.assertRaises(HTTPError) as error:
                        urlopen(request, timeout=5)
                    self.assertEqual(error.exception.code, 422)
                    error.exception.close()
                    request.add_header("Origin", "https://example.com")
                    with self.assertRaises(HTTPError) as error:
                        urlopen(request, timeout=5)
                    self.assertEqual(error.exception.code, 403)
                    error.exception.close()
                finally:
                    instance.shutdown()
                    instance.server_close()
                    thread.join(5)


if __name__ == "__main__":
    unittest.main()
