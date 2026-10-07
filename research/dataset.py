"""Recording, extraction, provenance, visual QC, and explicit review gates."""
import csv
import hashlib
import json
import re
import time
from pathlib import Path

from .features import FEATURES, LABELS, VERSION, QUALITY_VERSION, REQUIRED, extract_features

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
MODEL_PATH = Path("models/pose_landmarker_lite.task")
META = ["row_id", "subject_id", "posture", "video_path", "frame_index", "timestamp_ms", "feature_version", "model_sha256"]
INSTRUCTIONS = {
    "Correct": "Sit comfortably upright; center head and level shoulders.",
    "Slouch": "Round upper back; move head and neck forward.",
    "Lean_Left": "Lean toward YOUR left side.",
    "Lean_Right": "Lean toward YOUR right side.",
}


def write_csv(path, rows, columns):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def record(args):
    import cv2
    if not re.fullmatch(r"S[0-9]{2,}", args.subject):
        raise ValueError("subject must be anonymous, e.g. S01")
    if args.seconds <= 2 * args.trim or args.trim < 0:
        raise ValueError("duration must exceed twice the nonnegative trim")
    root = Path(args.dataset).resolve()
    manifest_path = root / "manifest.csv"
    rows = read_csv(manifest_path) if manifest_path.exists() else []
    folder = root / args.subject / args.posture.lower()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{args.subject}_{args.posture.lower()}_{args.take:02d}.mp4"
    if path.exists():
        raise ValueError(f"recording already exists: {path}; choose another --take")
    cap = cv2.VideoCapture(args.camera)
    writer = None
    try:
        if not cap.isOpened():
            raise ValueError("cannot open camera")
        print("Press SPACE when holding the requested posture; ESC cancels. Audio is not recorded.")
        while True:
            ok, frame = cap.read()
            if not ok:
                raise ValueError("camera read failed")
            cv2.putText(frame, f"{args.subject} {args.posture} take {args.take}: SPACE to start", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 0), 2)
            cv2.putText(frame, INSTRUCTIONS[args.posture], (20, 65), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
            cv2.putText(frame, "Show your head, both ears and shoulders. ESC cancels.", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
            cv2.imshow("Research recording", frame)
            key = cv2.waitKey(1) & 255
            if key == 27:
                return False
            if cv2.getWindowProperty("Research recording", cv2.WND_PROP_VISIBLE) < 1:
                return False
            if key == 32:
                break
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not 1 <= fps <= 120:
            fps = 30.0
        height, width = frame.shape[:2]
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        if not writer.isOpened():
            raise ValueError("cannot create recording")
        start, count = time.perf_counter(), 0
        while time.perf_counter() - start < args.seconds:
            ok, frame = cap.read()
            if not ok:
                raise ValueError("camera read failed; incomplete video retained, no manifest entry")
            writer.write(frame)
            count += 1
            cv2.putText(frame, f"{args.posture} {time.perf_counter()-start:.1f}s", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 0), 2)
            cv2.imshow("Research recording", frame)
            if cv2.waitKey(1) & 255 == 27:
                print("Interrupted video retained for inspection; not added to manifest.")
                return False
            if cv2.getWindowProperty("Research recording", cv2.WND_PROP_VISIBLE) < 1:
                print("Recording window closed; partial video retained without manifest entry.")
                return False
        # OpenCV encodes at constant FPS; intervals use encoded video time.
        duration = count / fps
        if duration <= 2 * args.trim:
            raise ValueError("encoded video too short for trim; retained without manifest entry")
        rows.append(dict(subject_id=args.subject, posture=args.posture,
                         video_path=path.relative_to(root).as_posix(),
                         start_seconds=args.trim, end_seconds=duration-args.trim))
        write_csv(manifest_path, rows, ["subject_id", "posture", "video_path", "start_seconds", "end_seconds"])
        print(f"Saved {path}; review and adjust the stable interval before extraction.")
        return path
    finally:
        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()


def record_session(args):
    """Guide one actual participant through all four classes, preserving a journal."""
    from datetime import datetime, timezone
    from types import SimpleNamespace
    if not re.fullmatch(r"S[0-9]{2,}", args.subject):
        raise ValueError("subject must be anonymous, e.g. S01")
    if args.takes < 1 or args.start_take < 1:
        raise ValueError("take counts must be positive")
    if args.seconds <= 2 * args.trim or args.trim < 0:
        raise ValueError("duration must exceed twice the nonnegative trim")
    root = Path(args.dataset).resolve()
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    journal = root / f"session_{args.subject}_{timestamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    state = dict(subject_id=args.subject, started_utc=timestamp.isoformat(),
                 status="recording", feature_version=VERSION, framing="head_and_shoulders",
                 planned_clips=args.takes * len(LABELS), clips=[])
    def save():
        journal.write_text(json.dumps(state, indent=2), encoding="utf-8")
    save()
    try:
        for take in range(args.start_take, args.start_take + args.takes):
            for posture in LABELS:
                print(f"\n{args.subject} | {posture} | take {take}: {INSTRUCTIONS[posture]}", flush=True)
                path = record(SimpleNamespace(subject=args.subject, posture=posture, take=take,
                    seconds=args.seconds, trim=args.trim, camera=args.camera, dataset=args.dataset))
                if not path:
                    state["status"] = "cancelled"
                    save()
                    return
                state["clips"].append(dict(posture=posture, take=take, video_path=Path(path).relative_to(root).as_posix()))
                save()
        state["status"] = "recordings_complete_review_required"
        save()
        if args.extract_after:
            output = root.parent / "data" / journal.stem
            extract(SimpleNamespace(model=args.model, manifest=str(root / "manifest.csv"),
                output=str(output), sample_fps=5, visibility=.65))
            qc(SimpleNamespace(extraction=str(output), per_class=50, seed=42))
            state["extraction_path"] = str(output)
            save()
        print(f"Session recorded in {journal}. Human video/QC review is required before training.", flush=True)
    except Exception as error:
        state.update(status="failed", error=str(error))
        save()
        raise


def extract(args):
    model = Path(args.model)
    if not model.is_file():
        raise ValueError("Pose asset missing. Run: python -m research download-model")
    manifest = Path(args.manifest).resolve()
    root = manifest.parent
    videos = read_csv(manifest)
    if not videos:
        raise ValueError("Manifest is empty. Record participants or add reviewed video intervals first.")
    import cv2
    import mediapipe as mp
    if args.sample_fps <= 0 or not 0 <= args.visibility <= 1:
        raise ValueError("sample FPS must be positive and visibility between 0 and 1")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if any((output / name).exists() for name in ("features.csv", "landmarks.jsonl", "qc_review.csv", "video_review.csv")):
        raise ValueError("output already contains extraction or reviews; choose a new --output directory")
    sha = digest(model)
    rows, rejected, audits, seen = [], [], [], set()
    video_hashes = set()
    # One tracker per recording: no tracking state crosses videos or people.
    with (output / "landmarks.jsonl").open("w", encoding="utf-8") as landmark_file:
        for entry in videos:
            subject, label, relative = entry["subject_id"], entry["posture"], entry["video_path"]
            if not re.fullmatch(r"S[0-9]{2,}", subject) or label not in LABELS:
                raise ValueError("manifest has invalid anonymous subject or protocol label")
            video = (root / relative).resolve()
            if not video.is_relative_to(root) or not video.is_file() or relative in seen:
                raise ValueError(f"missing, duplicate, or out-of-root video: {relative}")
            seen.add(relative)
            video_sha = digest(video)
            if video_sha in video_hashes:
                raise ValueError(f"duplicate video content would risk leakage: {relative}")
            video_hashes.add(video_sha)
            start, end = float(entry["start_seconds"]), float(entry["end_seconds"])
            if not 0 <= start < end:
                raise ValueError(f"invalid stable interval: {relative}")
            cap = cv2.VideoCapture(str(video))
            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if not cap.isOpened() or fps <= 0 or total <= 0 or end > total / fps + 1 / fps:
                    raise ValueError(f"unreadable video or interval exceeds duration: {relative}")
                options = mp.tasks.vision.PoseLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                    running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=1,
                    min_pose_detection_confidence=.5, min_pose_presence_confidence=.5,
                    min_tracking_confidence=.5)
                count, accepted, next_sample, last_timestamp = 0, 0, start, -1
                with mp.tasks.vision.PoseLandmarker.create_from_options(options) as pose:
                    while True:
                        ok, frame = cap.read()
                        if not ok:
                            break
                        index = count
                        count += 1
                        seconds = index / fps
                        if seconds < next_sample or seconds >= end:
                            continue
                        next_sample = seconds + 1 / args.sample_fps
                        timestamp = max(last_timestamp + 1, round(seconds * 1000))
                        last_timestamp = timestamp
                        height, width = frame.shape[:2]
                        result = pose.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
                            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), timestamp)
                        row_id = hashlib.sha256(f"{subject}|{relative}|{index}".encode()).hexdigest()[:24]
                        meta = dict(zip(META, (row_id, subject, label, relative, index, timestamp, VERSION, sha)))
                        try:
                            if len(result.pose_landmarks) != 1:
                                raise ValueError("no pose")
                            landmarks = [dict(x=p.x, y=p.y, z=p.z, visibility=p.visibility, presence=p.presence) for p in result.pose_landmarks[0]]
                            features = extract_features(landmarks, width, height, args.visibility)
                        except ValueError as e:
                            rejected.append({**meta, "reason": str(e)})
                            continue
                        rows.append({**meta, **features})
                        landmark_file.write(json.dumps({**meta, "width": width, "height": height, "landmarks": landmarks}) + "\n")
                        accepted += 1
                audits.append({**entry, "video_sha256": video_sha, "accepted_frames": accepted,
                    "fps": fps, "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))})
                print(f"{relative}: {accepted} accepted")
            finally:
                cap.release()
    write_csv(output / "features.csv", rows, META + list(FEATURES))
    write_csv(output / "rejected_frames.csv", rejected, META + ["reason"])
    write_csv(output / "video_review.csv", [{"video_path": e["video_path"], "decision": "", "notes": ""} for e in videos], ["video_path", "decision", "notes"])
    (output / "extraction.json").write_text(json.dumps(dict(feature_version=VERSION, model_sha256=sha,
        quality_version=QUALITY_VERSION,
        mediapipe_version=mp.__version__, opencv_version=cv2.__version__,
        visibility=args.visibility, sample_fps=args.sample_fps, manifest=str(manifest),
        manifest_sha256=digest(manifest), videos=audits), indent=2), encoding="utf-8")
    print(f"{len(rows)} rows extracted; review videos and run qc before cleaning.")


def qc(args):
    import cv2
    import random
    root = Path(args.extraction)
    review = root / "qc_review.csv"
    if review.exists():
        raise ValueError("QC review already exists; do not overwrite review decisions")
    if args.per_class < 1:
        raise ValueError("--per-class must be positive")
    rows = read_csv(root / "features.csv")
    if {r["posture"] for r in rows} != set(LABELS):
        raise ValueError("accepted frames must contain all four classes before QC")
    meta = json.loads((root / "extraction.json").read_text())
    videos = Path(meta["manifest"]).parent
    for entry in meta["videos"]:
        if digest(videos / entry["video_path"]) != entry["video_sha256"]:
            raise ValueError("an original video changed after extraction; extract again")
    rng = random.Random(args.seed)
    selected = []
    # Sample every recording as well as each class, so no recording escapes QC.
    for path in sorted({r["video_path"] for r in rows}):
        selected.append(rng.choice([r for r in rows if r["video_path"] == path]))
    for label in LABELS:
        candidates = [r for r in rows if r["posture"] == label]
        selected.extend(rng.sample(candidates, min(args.per_class, len(candidates))))
    selected = {r["row_id"]: r for r in selected}
    landmarks = {}
    with (root / "landmarks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if record["row_id"] in selected:
                landmarks[record["row_id"]] = record
    folder = root / "qc"
    folder.mkdir(exist_ok=True)
    reviews = []
    for row_id, row in selected.items():
        cap = cv2.VideoCapture(str(videos / row["video_path"]))
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(row["frame_index"]))
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"cannot retrieve QC frame {row_id}")
        finally:
            cap.release()
        record = landmarks[row_id]
        width, height = record["width"], record["height"]
        points = [(round(p["x"]*width), round(p["y"]*height)) for p in record["landmarks"]]
        for a, b in ((0, 2), (2, 7), (0, 5), (5, 8), (7, 11), (8, 12), (11, 12)):
            cv2.line(frame, points[a], points[b], (0, 255, 0), 2)
        for i in REQUIRED:
            cv2.circle(frame, points[i], 3, (0, 255, 255), -1)
        cv2.putText(frame, f"{row['subject_id']} {row['posture']} frame {row['frame_index']}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 2)
        image = f"qc/{row_id}.jpg"
        if not cv2.imwrite(str(root / image), frame):
            raise ValueError("could not save QC image")
        reviews.append({"row_id": row_id, "image_path": image, "decision": "", "notes": ""})
    write_csv(review, reviews, ["row_id", "image_path", "decision", "notes"])
    (root / "qc_config.json").write_text(json.dumps({"seed": args.seed, "per_class": args.per_class}), encoding="utf-8")
    print(f"Inspect {len(reviews)} images; fill accept/reject in {review} and video_review.csv.")


def clean(args):
    root = Path(args.extraction)
    rows = read_csv(root / "features.csv")
    videos = read_csv(root / "video_review.csv")
    samples = read_csv(root / "qc_review.csv")
    if not rows or not samples or any(r["decision"] not in ("accept", "reject") for r in videos + samples):
        raise ValueError("every video and QC sample needs an explicit accept/reject decision")
    if len({r["video_path"] for r in videos}) != len(videos) or len({r["row_id"] for r in samples}) != len(samples):
        raise ValueError("duplicate review rows")
    audited = json.loads((root / "extraction.json").read_text())["videos"]
    if {r["video_path"] for r in videos} != {r["video_path"] for r in audited}:
        raise ValueError("video review coverage mismatch")
    by_id = {r["row_id"]: r for r in rows}
    if any(r["row_id"] not in by_id for r in samples):
        raise ValueError("QC references unknown rows")
    covered = {by_id[r["row_id"]]["video_path"] for r in samples}
    accepted_videos = {r["video_path"] for r in videos if r["decision"] == "accept"}
    if not accepted_videos <= covered:
        raise ValueError("every accepted recording must have QC samples")
    # Any rejected sample quarantines its entire recording: nearby unsampled
    # transition/bad frames must not silently remain in the training set.
    quarantine = {by_id[r["row_id"]]["video_path"] for r in samples if r["decision"] == "reject"}
    final = [r for r in rows if r["video_path"] in accepted_videos - quarantine]
    if {r["posture"] for r in final} != set(LABELS):
        raise ValueError("clean dataset must retain all four classes")
    write_csv(args.output, final, META + list(FEATURES))
    Path(str(args.output) + ".review.json").write_text(json.dumps({
        "source_sha256": digest(root / "features.csv"), "clean_sha256": digest(args.output),
        "video_review_sha256": digest(root / "video_review.csv"),
        "qc_review_sha256": digest(root / "qc_review.csv"), "quarantined_videos": sorted(quarantine),
        "rows_before": len(rows), "rows_after": len(final),
        "review_provenance": json.loads((root / "review_provenance.json").read_text()) if (root / "review_provenance.json").exists() else {"reviewer": "unspecified; see review CSV notes"}}, indent=2), encoding="utf-8")
    print(f"Saved {len(final)} reviewed rows to {args.output}; {len(quarantine)} videos quarantined.")
