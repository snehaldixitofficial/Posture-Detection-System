"""Save a factual audit before choosing a public-data experiment."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def describe(path, subject_column, label_column):
    df = pd.read_csv(path)
    numeric = df.select_dtypes("number")
    summary = dict(file=str(path.relative_to(ROOT)), rows=len(df), columns=list(df),
                   sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   md5=hashlib.md5(path.read_bytes()).hexdigest(),
                   missing_values=int(df.isna().sum().sum()),
                   nonfinite_numeric_values=int((~np.isfinite(numeric)).sum().sum()),
                   duplicate_full_rows=int(df.duplicated().sum()),
                   label_counts={str(k): int(v) for k, v in df[label_column].value_counts().items()},
                   has_subject_ids=subject_column in df)
    if subject_column in df:
        summary["participants"] = int(df[subject_column].nunique())
        summary["subject_class_counts"] = pd.crosstab(df[subject_column], df[label_column]).to_dict(orient="index")
        coordinate_columns = [c for c in df if c.endswith(("_x", "_y", "_z"))]
        summary["coordinate_columns"] = len(coordinate_columns)
        summary["duplicate_coordinate_rows"] = int(df[coordinate_columns].duplicated().sum())
    return summary


if __name__ == "__main__":
    existing = describe(ROOT / "data/hf_posture_dataset.csv", "subject_id", "posture")
    public = describe(ROOT / "data/public/multiposture.csv", "subject", "upperbody_label")
    public["publisher_md5_matches"] = public["md5"] == "7efbc94d653acf32eefecec3ff26d6c6"
    public["source"] = "https://zenodo.org/records/14230872"
    public["limitations"] = [
        "Published labels contain lean-forward, not slouch.",
        "Raw images/videos and confidence scores are not included.",
        "Coordinates are hip-relative 3D, not the original browser's image-coordinate features.",
        "Subject 5 has no backward-lean frames; absent classes must be handled explicitly.",
        "Publisher description says 4800 frames/11 selected joints, while the downloaded CSV has 4794 rows/33 joints.",
        "Live webcam transfer requires the same coordinate definition and independent validation.",
    ]
    output = ROOT / "docs/verification/dataset_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(existing_reference=existing, multiposture=public), indent=2), encoding="utf-8")
    print(f"Saved {output}; MultiPosture: {public['rows']} rows, {public['participants']} participants.")
