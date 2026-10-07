"""Synthetic fixtures exercise software contracts; never research evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np
import pandas as pd

from research.dataset import META, clean, digest, write_csv
from research.features import FEATURES, LABELS, VERSION, extract_features, rule_predictions
from research.train import train


def fixture_landmarks():
    result = [dict(x=.5, y=.5, z=0., visibility=.99, presence=.99) for _ in range(33)]
    for i, x, y in ((0, .5, .2), (2, .54, .18), (5, .46, .18), (7, .6, .23), (8, .4, .23),
                    (11, .65, .4), (12, .35, .4), (23, .6, .8), (24, .4, .8)):
        result[i].update(x=x, y=y)
    return result


class FeatureTests(unittest.TestCase):
    def test_normalization_and_contract(self):
        original = fixture_landmarks()
        features = extract_features(original, 800, 600)
        moved = copy.deepcopy(original)
        for p in moved:
            p.update(x=(p['x']-.5)*.8+.52, y=(p['y']-.5)*.8+.48, z=p['z']*.8)
        transformed = extract_features(moved, 800, 600)
        self.assertEqual(tuple(features), FEATURES)
        np.testing.assert_allclose(list(features.values()), list(transformed.values()), atol=1e-10)

    def test_missing_and_bad_detection(self):
        for key, value in (("visibility", .2), ("x", 1.1), ("z", float("nan"))):
            pose = fixture_landmarks()
            pose[11][key] = value
            with self.assertRaises(ValueError):
                extract_features(pose, 800, 600)
        with self.assertRaises(ValueError):
            extract_features([], 800, 600)

    def test_unseen_lower_body_does_not_affect_head_shoulder_features(self):
        pose = fixture_landmarks()
        expected = extract_features(pose, 800, 600)
        for i in range(13, 33):
            pose[i] = None
        self.assertEqual(extract_features(pose, 800, 600), expected)
        self.assertTrue(all("hip" not in name and "torso" not in name for name in FEATURES))

    def test_original_baseline_is_not_relabelled(self):
        exact, extension = rule_predictions([dict(f1=1., f2=1.352, face_asymmetry=-.1)])
        self.assertEqual(exact, ["Lean"])
        self.assertEqual(extension, ["Lean_Left"])

    def test_slouch_geometry_is_not_removed_as_bad_detection(self):
        pose = fixture_landmarks()
        for i in (0, 2, 5, 7, 8):
            pose[i]["y"] += .23
        features = extract_features(pose, 800, 600)
        self.assertTrue(np.isfinite(list(features.values())).all())
        self.assertLess(features["nose_vertical_offset"], 0)


class ReviewTests(unittest.TestCase):
    def test_reviews_required_and_rejected_sample_quarantines_video(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows, videos, samples = [], [], []
            for i, label in enumerate(LABELS):
                for take in range(2):
                    video = f"{label}_{take}.mp4"
                    row = dict(zip(META, (f"{i}_{take}", "S01", label, video, 0, 0, VERSION, "fixture")))
                    rows.append({**row, **dict.fromkeys(FEATURES, 0.)})
                    videos.append(dict(video_path=video, decision="accept", notes=""))
                    samples.append(dict(row_id=row["row_id"], image_path="fixture.jpg", decision="accept", notes=""))
            write_csv(root / "features.csv", rows, META + list(FEATURES))
            write_csv(root / "video_review.csv", videos, ["video_path", "decision", "notes"])
            (root / "extraction.json").write_text(json.dumps({"videos": videos}))
            samples[0]["decision"] = ""
            write_csv(root / "qc_review.csv", samples, ["row_id", "image_path", "decision", "notes"])
            args = SimpleNamespace(extraction=str(root), output=str(root / "clean.csv"))
            with self.assertRaises(ValueError):
                clean(args)
            samples[0]["decision"] = "reject"
            write_csv(root / "qc_review.csv", samples, ["row_id", "image_path", "decision", "notes"])
            clean(args)
            self.assertEqual(len(pd.read_csv(root / "clean.csv")), 7)


class ExperimentTests(unittest.TestCase):
    def test_real_estimators_share_subject_folds_and_features(self):
        # Synthetic, deliberately small, temporary data: validates plumbing only.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = []
            rng = np.random.default_rng(42)
            for subject in ("S01", "S02", "S03"):
                for label_index, label in enumerate(LABELS):
                    for frame in range(3):
                        row = dict(zip(META, (f"{subject}_{label}_{frame}", subject, label, "fixture.mp4", frame, frame*200, VERSION, "fixture")))
                        row.update(dict(zip(FEATURES, rng.normal(label_index, .2, len(FEATURES)))))
                        rows.append(row)
            data = root / "features_clean.csv"
            write_csv(data, rows, META + list(FEATURES))
            Path(str(data) + ".review.json").write_text(json.dumps({"clean_sha256": digest(data)}))
            for mode in ("holdout", "loso"):
                split = root / "split.json"
                split.write_text(json.dumps(dict(train=["S01"], validation=["S02"], test=["S03"])))
                output = root / mode
                train(SimpleNamespace(data=str(data), output=str(output), mode=mode, split=str(split), tune=False, seed=42))
                provenance = json.loads((output / "experiment.json").read_text())
                for fold in provenance["folds"]:
                    self.assertFalse(set(fold["development_subjects"]) & set(fold["test_subjects"]))
                    for inner in fold["inner"]:
                        self.assertFalse(set(inner["train_subjects"]) & set(inner["validation_subjects"]))
                        self.assertFalse(set(inner["train_subjects"]) & set(fold["test_subjects"]))
                predictions = pd.read_csv(output / "predictions.csv")
                row_sets = [set(part.row_id) for _, part in predictions.groupby("model")]
                self.assertTrue(all(s == row_sets[0] for s in row_sets))
                artifact = joblib.load(output / "best_model.joblib")
                self.assertEqual(tuple(artifact["features"]), FEATURES)
                if mode == "holdout":
                    svm = joblib.load(output / "SVM_RBF.joblib")
                    self.assertEqual(svm[0].n_samples_seen_, 24)  # Train + validation, never test.
                self.assertTrue((output / "comparison.png").exists())
                self.assertTrue((output / "baseline_metrics.json").exists())
            # Edits invalidate the review gate rather than silently retraining.
            with data.open("a") as f:
                f.write("\n")
            with self.assertRaises(ValueError):
                train(SimpleNamespace(data=str(data)))


if __name__ == "__main__":
    unittest.main()
