"""Versioned features shared by offline extraction and the local live predictor.

Angles are degrees; distances and depth proxies are shoulder-width normalized.
Image x and z are corrected for aspect ratio. Depth is a MediaPipe proxy, not
a measurement of physical forward displacement. Left/right are anatomical.
"""
import math

LABELS = ("Correct", "Slouch", "Lean_Left", "Lean_Right")
VERSION = "posture-head-shoulders-v2"
QUALITY_VERSION = "head-shoulders-quality-v3"
FEATURES = (
    "f1", "f2", "face_asymmetry", "nose_shoulder_distance",
    "left_ear_shoulder_distance", "right_ear_shoulder_distance",
    "neck_angle", "head_tilt", "shoulder_angle", "shoulder_height_difference",
    "nose_left_shoulder_distance", "nose_right_shoulder_distance", "eye_mid_shoulder_distance",
    "ear_width_ratio", "eye_width_ratio", "nose_vertical_offset", "head_depth_proxy",
    "ear_depth_proxy", "nose_lateral_offset", "ear_vertical_offset", "face_shoulder_depth_asymmetry",
)
REQUIRED = (0, 2, 5, 7, 8, 11, 12)


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def midpoint(a, b):
    return tuple((x + y) / 2 for x, y in zip(a, b))


def incenter(a, b, c):
    weights = (distance(b, c), distance(a, c), distance(a, b))
    total = sum(weights)
    if total < 1e-8:
        raise ValueError("degenerate face triangle")
    return tuple(sum(w * p[i] for w, p in zip(weights, (a, b, c))) / total for i in (0, 1))


def vertical(top, bottom):
    return math.degrees(math.atan2(top[0] - bottom[0], bottom[1] - top[1]))


def extract_features(landmarks, width, height, visibility=0.65):
    if len(landmarks) != 33 or width <= 0 or height <= 0:
        raise ValueError("expected 33 landmarks and positive frame dimensions")
    for i in REQUIRED:
        p = landmarks[i]
        if not all(math.isfinite(float(p.get(k, float("nan")))) for k in ("x", "y", "z", "visibility")):
            raise ValueError("missing or nonfinite landmark")
        if not math.isfinite(float(p.get("presence", 1))) or p["visibility"] < visibility or p.get("presence", 1) < visibility:
            raise ValueError("low landmark confidence")
        if not (0 <= p["x"] <= 1 and 0 <= p["y"] <= 1):
            raise ValueError("required landmark outside frame")
    aspect = width / height
    # Never inspect inferred/out-of-frame hips or other unneeded landmarks.
    points = {i: (landmarks[i]["x"] * aspect, landmarks[i]["y"], landmarks[i]["z"] * aspect) for i in REQUIRED}
    n, le, re, ls, rs = [points[i] for i in (0, 7, 8, 11, 12)]
    sm, em = midpoint(ls, rs), midpoint(le, re)
    eyes = midpoint(points[2], points[5])
    sw = distance(ls, rs)
    if sw < 0.1 * aspect:
        raise ValueError("implausible upper-body geometry")
    # Slouch can bring the head close to/below shoulder height. These are
    # class signals, not detection failures; never filter for upright geometry.
    if distance(n, sm) / sw > 3:
        raise ValueError("implausible body proportions")
    # Retain the original monitor's exact two features for an honest baseline.
    raw = {i: (landmarks[i]["x"], landmarks[i]["y"]) for i in REQUIRED}
    dl = distance(incenter(raw[2], raw[7], raw[0]), raw[11])
    dr = distance(incenter(raw[5], raw[8], raw[0]), raw[12])
    raw_sw = distance(raw[11], raw[12])
    values = (
        abs(dl - dr) * 10 / raw_sw, (dl + dr) / raw_sw,
        (dl - dr) / raw_sw, distance(n, sm) / sw,
        distance(le, ls) / sw, distance(re, rs) / sw,
        vertical(em, sm), vertical(n, em),
        math.degrees(math.atan2(rs[1] - ls[1], ls[0] - rs[0])),
        (ls[1] - rs[1]) / sw, distance(n, ls) / sw, distance(n, rs) / sw, distance(eyes, sm) / sw,
        distance(le, re) / sw, distance(points[2], points[5]) / sw, (sm[1] - n[1]) / sw,
        (sm[2] - n[2]) / sw, (sm[2] - em[2]) / sw,
        (n[0] - sm[0]) / sw, (sm[1] - em[1]) / sw, ((le[2] - ls[2]) - (re[2] - rs[2])) / sw,
    )
    if not all(math.isfinite(v) for v in values):
        raise ValueError("nonfinite feature")
    return dict(zip(FEATURES, values))


def rule_predictions(rows):
    """Original fixed defaults; lateral sign extension is reported separately."""
    exact, directional = [], []
    for row in rows:
        if row["f2"] - 1.352 < -0.12:
            a = b = "Slouch"
        elif abs(row["f1"] - 0.031) > 0.55:
            a = "Lean"  # Original rule never distinguished left from right.
            b = "Lean_Left" if row["face_asymmetry"] < 0 else "Lean_Right"
        else:
            a = b = "Correct"
        exact.append(a)
        directional.append(b)
    return exact, directional
