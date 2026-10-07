"""Optional real-MediaPipe smoke test using a temporary blank video."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from research.dataset import MODEL_PATH, extract, read_csv, write_csv


@unittest.skipUnless(MODEL_PATH.is_file(), "download the Pose asset to test actual extraction")
class PoseSmokeTests(unittest.TestCase):
    def test_video_api_and_no_pose_quality_rejection(self):
        import cv2
        import numpy as np
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            video = root / "blank_fixture.mp4"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 10, (320, 240))
            self.assertTrue(writer.isOpened())
            for _ in range(20):
                writer.write(np.zeros((240, 320, 3), dtype=np.uint8))
            writer.release()
            manifest = root / "manifest.csv"
            write_csv(manifest, [dict(subject_id="S01", posture="Correct", video_path=video.name,
                                     start_seconds=.5, end_seconds=1.5)],
                      ["subject_id", "posture", "video_path", "start_seconds", "end_seconds"])
            output = root / "extracted"
            extract(SimpleNamespace(model=str(MODEL_PATH.resolve()), manifest=str(manifest),
                                    output=str(output), sample_fps=5, visibility=.65))
            self.assertEqual(read_csv(output / "features.csv"), [])
            rejected = read_csv(output / "rejected_frames.csv")
            self.assertEqual(len(rejected), 5)
            self.assertTrue(all(r["reason"] == "no pose" for r in rejected))
            self.assertTrue(all(500 <= int(r["timestamp_ms"]) < 1500 for r in rejected))
            config = json.loads((output / "extraction.json").read_text())
            self.assertEqual(config["videos"][0]["accepted_frames"], 0)


if __name__ == "__main__":
    unittest.main()
