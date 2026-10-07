"""Pilot split fixtures check software leakage prevention, not research results."""
import unittest
import numpy as np
import pandas as pd
from research.features import LABELS
from research.pilot import split_pilot

class PilotSplitTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame([{'subject_id': 'S01', 'posture': label,
                             'video_path': f'S01/{label}/S01_{label}_{take:02d}.mp4', 'timestamp_ms': t}
                            for take in (2, 3) for label in LABELS for t in range(5000, 55001, 200)])

    def test_test_videos_and_tuning_gap(self):
        df = self.frame()
        train, val, dev, test, gap = split_pilot(df)
        self.assertFalse(set(df.iloc[dev].video_path) & set(df.iloc[test].video_path))
        self.assertEqual(set(train) | set(val) | set(gap), set(dev))
        self.assertFalse(set(train) & set(val))
        self.assertEqual(len(test), len(dev))
        for video in df.iloc[dev].video_path.unique():
            ta = df.iloc[train].query('video_path == @video').timestamp_ms
            va = df.iloc[val].query('video_path == @video').timestamp_ms
            self.assertGreater(va.min() - ta.max(), 2000)
        changed = df.copy()
        changed.loc[test, 'timestamp_ms'] += 100000
        for original, new in zip((train, val, dev, test, gap), split_pilot(changed)):
            np.testing.assert_array_equal(original, new)

    def test_multiple_people_rejected(self):
        df = self.frame()
        df.loc[0, 'subject_id'] = 'S02'
        with self.assertRaises(ValueError):
            split_pilot(df)
