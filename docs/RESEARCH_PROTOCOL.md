# Sitting-posture experiment

Research question: which of Random Forest, SVM-RBF, and XGBoost best classifies
Correct, Slouch, Lean_Left, and Lean_Right on previously unseen participants,
using the same MediaPipe geometric features?

The software is ready for data collection. No four-class participant videos or
experimental results have been supplied. The existing reference CSV cannot
answer this question: it has different labels/features and no required subject
and video provenance. Example scores in the pasted proposal are not results.

## 1. Define and record the dataset

Recruit at least 10 consenting participants, preferably 15-20. Assign anonymous
IDs S01, S02, etc.; keep identity/consent records separately from this repo.
Keep original videos in access-controlled storage and back them up. Videos and
derived participant data are excluded from Git by default.

Use a fixed, frontal, unmirrored camera at chest level, stable lighting, and the
same resolution and distance for all takes. Frame the head and both shoulders;
both ears should be visible. Hips and the lower body are not required. Record
60 seconds per posture, with 2-3 takes per class per person.
Rest between takes. Left and right mean the participant's anatomical left/right,
not the viewer's left/right. Do not mirror imported recordings.

| Label | Instruction |
|---|---|
| Correct | Sit comfortably upright, head centered, shoulders approximately level. |
| Slouch | Round your upper back and move your head/neck forward. |
| Lean_Left | Lean your torso toward your own left. |
| Lean_Right | Lean your torso toward your own right. |

Frontal head-and-shoulder views can make slouch subtle. This experiment measures
head position and shoulder geometry as proxies; it cannot directly verify spinal
or lower-torso posture outside the frame. Inspect videos and depth proxies carefully;
landmark z is an estimate, not a measured physical head-forward displacement.

From the repository root in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-research.txt
python -m research download-model
python -m research record --subject S01 --posture Correct --take 1
python -m research record --subject S01 --posture Slouch --take 1
python -m research record --subject S01 --posture Lean_Left --take 1
python -m research record --subject S01 --posture Lean_Right --take 1
```

Python 3.11 was used for verification. `requirements-research.lock.txt` captures
the verified environment; install that file instead of the version ranges to
reproduce those dependency versions. This workspace already has `.venv` and the
downloaded Pose asset, so recording can start with `.venv\Scripts\python.exe`.

Press SPACE after the participant holds the requested posture. ESC cancels;
partial recordings remain available but are not added to the manifest. No audio
is recorded. Repeat with `--take 2`, then new subject IDs.

To guide one participant through all four classes and two takes automatically:

```powershell
.venv\Scripts\python.exe -m research record-session --subject S01 --extract-after
```

Each clip waits for SPACE so the participant can assume the displayed posture.
ESC or closing the window stops the session. A session journal tracks saved clips;
completed sessions can automatically produce extraction and skeleton QC files.
Human review remains required. Public-data alternatives are assessed separately
in `DATASET_ASSESSMENT.md`; their published labels must be preserved.

The recorder writes videos and appends protocol labels to `dataset/manifest.csv`.
Its default stable interval excludes five seconds at each end. Open each video
and adjust `start_seconds`/`end_seconds` to exclude all transitions and movement.
The encoded FPS determines CSV timestamps; compare the saved video's duration
with the intended duration if the camera cannot sustain its reported FPS.
For existing videos, add one manifest row per video, with paths relative to the
manifest's folder. Do not invent labels from features or model predictions.

## 2. Extract, visually review, then clean

```powershell
python -m research extract
python -m research qc --per-class 50
```

Extraction samples at up to five frames/second inside stable intervals. It uses
MediaPipe Pose Tasks in VIDEO mode with a separate tracker for each recording,
saves all 33 landmarks for accepted frames, and calculates 21 numerical features.
Only the nose, eyes, ears and shoulders are used or required. Inferred lower-body
landmarks are ignored, and QC overlays show the head and shoulder joints only.
The feature contract is `posture-head-shoulders-v2`; older torso-based CSVs and
model artifacts must be re-extracted and retrained before using this version.
Distances/depth proxies use shoulder width; x/z are aspect-corrected. The legacy
f1/f2 retain their original definition for baseline evaluation. Subject IDs,
labels, video paths, and timestamps are never predictor inputs.

Low visibility/presence, missing/nonfinite landmarks, out-of-frame joints,
degenerate faces, and implausible proportions are rejected. See
`data/research/rejected_frames.csv` for reasons. Automated quality checks do not
verify ground truth; human review is mandatory.
The quality policy `head-shoulders-quality-v3` permits the head to approach or
drop below shoulder height during slouch. Upright-only geometric assumptions
must not remove the class being studied; confidence thresholds are unchanged.

Outputs in `data/research/`:

- `features.csv`: measurements with subject, video, frame index, and timestamp.
- `landmarks.jsonl`: corresponding 33 landmarks, dimensions, and provenance.
- `extraction.json`: model/video hashes, manifest, and settings.
- `qc/`: skeleton images, sampled per class and from every usable recording.
- `qc_review.csv` and `video_review.csv`: explicit human review decisions.

Watch every recording and inspect all QC images. Set each `decision` to `accept`
or `reject`; document errors in `notes`. A rejected QC sample quarantines its whole
recording so unsampled neighboring bad frames cannot silently remain. Correct the
stable interval or re-record, extract into a new directory, and repeat QC.
Extraction and QC refuse to overwrite existing reviews. For a new directory,
pass the same `--extraction` path to qc and clean.

```powershell
python -m research clean
```

This creates `features_clean.csv` and a review/hash receipt. Training refuses an
unreviewed file or a CSV modified after cleaning. Every participant must retain
all four classes; minimum three subjects is a software check, not a recommended
research sample size.

## 3. Compare models on the same held-out people

Default evaluation is nested leave-one-subject-out (LOSO): each person is held
out once; inner GroupKFold uses only remaining people for parameter selection.
All models share outer/inner splits and the exact same features. SVM scaling is
fitted inside each training fold. `--tune` evaluates two predeclared candidate
configurations per model; omit it for the proposal's defaults. Do not alter grids
after inspecting test results.

```powershell
python -m research train --mode loso --tune --output results/experiment_01
```

For a predeclared train/validation/test experiment, create `split.json`:

```json
{
  "train": ["S01", "S02", "S03", "S04", "S05", "S06", "S07"],
  "validation": ["S08", "S09"],
  "test": ["S10"]
}
```

```powershell
python -m research train --mode holdout --split split.json --tune --output results/holdout_01
```

Every subject must appear in exactly one partition. Hyperparameters and the
deployment model are selected using validation macro F1, weighted equally by
participant. Holdout models refit on train + validation before evaluation on test.
Test labels do not determine the deployment winner.

The experiment writes:

- `comparison.csv` and `comparison.png`: accuracy, macro precision/recall/F1,
  per-subject mean and sample SD, training and model-only prediction timing.
- `fold_metrics.csv`, `subject_metrics.csv`, and `predictions.csv`.
- Per-model classification reports and confusion matrices as CSV and PNG.
- `paired_comparison.csv`: subject-level F1 differences and consistency counts.
- `baseline_metrics.json` and baseline predictions/confusion matrices.
- `experiment.json`: partitions, configuration, hashes, dependency versions,
  selection scores, and methodological limitations.
- `best_model.joblib`: selected configuration and feature contract.

The original fixed-default rule merges both lean directions, so its report has
three states. `directional_extension_4class` is separately named as a new heuristic
using signed face asymmetry. Neither uses upright test samples for calibration.
The report also collapses each ML model to those same three states for direct
comparison with the original rule; rule prediction timings are included.
For personal calibration, predeclare a separate calibration recording and exclude
it from evaluation. Do not calibrate against labeled test frames.

Report per-person means and pooled frame scores; neighboring frames are correlated.
Mean +/- SD and paired differences are descriptive, not statistical significance.
A single holdout person has no meaningful subject SD. Prediction latency includes
scaler/classifier calls, with median single-frame and amortized batch timing; it
excludes MediaPipe, features, HTTP, and rendering. Measure end-to-end webcam latency
separately on the deployment PC.

LOSO estimates each model's nested selection procedure. For deployment, separate
group CV on all reviewed participants selects a configuration and refits on all
data. Its selection score is not independent performance of the winning deployed
model; fresh participants are needed for that final check.

## 4. Use the selected model in the webcam application

```powershell
python -m research serve --model results/experiment_01/best_model.joblib
```

The optional loopback server exposes `GET /api/model` and `POST /api/predict`
for direct Python inference using the shared feature extractor. It checks the
feature contract and exact Pose asset. Only load joblib files you created and trust.

The hosted webcam demonstration now runs all three frozen S01 classifiers directly
in JavaScript; it does not use this Python endpoint. Open the deployed website or
serve the project with `python -m http.server 8001 --bind 127.0.0.1`. Click Start
camera, allow access and select Random Forest, SVM or XGBoost. The original rules
remain a separate three-state option with upright calibration. ML calibration is
disabled. Invalid frames clear predictions rather than falling back to rules.

The bundled browser and Python MediaPipe runtimes are both version 0.10.35, with
the same Pose Lite asset. JavaScript features and all three classifiers match
Python on 1,930 recorded landmark rows (5,790 labels). This is implementation
parity, not an evaluation of fresh webcam accuracy or cross-runtime tracking.
See `docs/DEMO_GUIDE.md` and `docs/CODE_WALKTHROUGH.md`.

## Single-person pilot completed with S01

When additional participants are unavailable, `--mode pilot` supports S01 takes
02 and 03. Take 02 is development data; take 03 is a video-disjoint test.
Parameter and model selection use chronological 70/30 blocks of take 02 with a
two-second exclusion gap. Scalers fit only training blocks during selection.
Selected configurations refit on all take-02 frames before test evaluation.
The live winner is a separate all-data refit; those test scores do not evaluate it.
Ties use the deterministic model/candidate listing order.

Review provenance identifies assistant inspection of 207 QC images and 24 raw
overview frames. This is sampled pilot review, not exhaustive human verification.
Labels represent prompted head-and-shoulder gestures. The multi-person review
and subject-split protocol remains the target for the full study.
See [actual results](PILOT_RESULTS_S01.md).

```powershell
python -m research train --mode pilot --tune --data data/session_S01_20261006T191350Z_quality_v3/features_clean.csv --output results/pilot_S01_new
python -m research serve --model results/pilot_S01/best_model.joblib
```

## Verification

```powershell
python -m unittest discover -s tests -v
node --check script.js
node tests/test_browser.cjs
```

Tests use isolated synthetic fixtures to verify feature invariance, quality
rejection, review enforcement, matching folds/features, model fitting, and outputs.
Their scores are not participant results and no fixture model is deployed.

Implementation references: [MediaPipe Python Pose Tasks](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python),
[MediaPipe browser Pose Tasks](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/web_js),
[GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html),
and [scikit-learn pipelines](https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html).
