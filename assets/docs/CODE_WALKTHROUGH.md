# Code walkthrough

Read the project in this order. There is no frontend framework or bundler.

| File | Responsibility | Explain these parts |
|---|---|---|
| `index.html` | Page structure | Camera canvas, classifier dropdown, three prediction cards, results, downloads |
| `style.css` | Presentation | Colors, layout, responsive rules, mirrored canvas, fullscreen |
| `script.js` | Camera and UI controller | `state`, `startCamera`, `loadModels`, `processFrame`, `drawFrame`, `stopCamera` |
| `posture-features.js` | Geometry and validation | `required`, `extract`, `distance`, `midpoint`, `incenter`, `vertical` |
| `model-runtime.js` | Trained-model inference | `leaf`, `forest`, `svm`, `boosted`, `predict` |
| `assets/models/*.json` | Learned parameters | Tree nodes, SVM support vectors, scaler statistics and feature version |

## Follow one frame

`startCamera()` loads model files and MediaPipe, asks for video without audio,
then starts `processFrame()`. A guard prevents duplicate camera startup.
`processFrame()` skips repeated video timestamps. MediaPipe returns 33 joints;
`PostureFeatures.extract()` uses only indices 0, 2, 5, 7, 8, 11 and 12.
Low-confidence or out-of-frame required joints throw a readable error. Hips and
all unused lower-body coordinates are ignored.

Valid geometry produces 21 values, in exactly the Python training order. Each
classifier receives the same vector. The three cards show all predictions; the
dropdown chooses the large status and counters. Invalid tracking clears stale
feedback. `drawFrame()` draws video plus visible head/shoulder lines. CSS mirroring
does not change inputs. `stopCamera()` releases tracks and clears the video.

`showPrediction()` counts changes into slouch/lean states, not frames. Fluctuating
labels or temporary tracking loss can increase these demonstration counters.
`updateMode()` resets feedback when switching models. `rulePrediction()` preserves
the original three-state baseline and its two-feature calibration.

## Understand the features

The first two values preserve the original monitor: f1 is unsigned face-to-shoulder
asymmetry; f2 is combined face-to-shoulder distance divided by shoulder width.
Signed asymmetry adds direction. Remaining values measure normalized distances,
angles, vertical/lateral offsets, and three relative depth proxies. Depth is a
MediaPipe estimate, not a physical distance measurement. Image aspect ratio
corrects x and z for the added geometry. The first two legacy features deliberately
keep their original raw normalized coordinates for an honest baseline.

The feature contract is `posture-head-shoulders-v2`; the quality gate is
`head-shoulders-quality-v3`. Do not reorder or calibrate ML inputs. Retrain and
re-export if the feature representation changes.

## Understand each classifier

**Random Forest:** `leaf()` follows each tree's feature-threshold splits. At the
leaf, `forest()` adds normalized class probabilities. The class with the largest
sum wins. Inputs use float32 rounding to match sklearn tree traversal.

**SVM:** `svm()` applies the saved StandardScaler mean and scale, computes RBF
similarity to each support vector, evaluates all six class pairs, and counts votes.
The winning class gets the most pairwise votes. This demo does not invent SVM
probabilities or show uncalibrated confidence as a probability.

**XGBoost:** `boosted()` starts with the fitted class base margins, follows every
tree, and adds its leaf value to its class score. The largest margin selects the
class. Strict `<` split comparisons and float32 accumulation reproduce the booster.

## Python research pipeline

| File | Responsibility |
|---|---|
| `research/__main__.py` | Command-line entry points and arguments |
| `research/dataset.py` | Video recording, timestamped extraction, rejection logging, QC pages and cleaning receipts |
| `research/features.py` | Reference feature implementation and original/directional rules |
| `research/pilot.py` | Single-person video split, temporal validation with gap, candidate tuning, frozen test evaluation and separate winner refit |
| `research/train.py` | Multi-participant grouped evaluation for later data collection |
| `research/server.py` | Optional loopback Python predictor and model contract checks |
| `tools/export_browser_models.py` | Export actual frozen models, aggregate scores and paper for the website |
| `tools/check_browser_parity.py` | Generate private Python reference fixtures |
| `tests/test_browser_models.cjs` | Compare browser features and predictions to Python on every recorded row |
| `tools/paper_analysis.py` | Exploratory ablations and quality-gate audit; not primary model selection |
| `tools/export_conference_paper.py` | PDF fallback from LaTeX source when native compilation is unavailable |
| `tools/deploy_static.py` | Upload only explicit public assets to the existing Vercel project |

Raw data and fitted `.joblib` files remain local. Website model JSON is a readable
inference representation of the three frozen evaluated artifacts, not a new model
or the separately refitted all-data winner. Original numerical research scores
remain unchanged. Private landmarks used for parity are excluded from deployment.

## Reproduce the checks

```powershell
.\.venv\Scripts\python.exe -m tools.export_browser_models
.\.venv\Scripts\python.exe -m tools.check_browser_parity
node tests/test_browser_models.cjs
node tests/test_browser.cjs
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

For paper discussion, use the actual pilot report and the manuscript limitations.
Do not call adjacent video frames independent participants or claim fresh webcam
accuracy from exported-model parity. Parity verifies implementation equivalence.
