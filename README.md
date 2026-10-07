# Stay Upright

Browser webcam demo with Random Forest, RBF SVM, XGBoost and the original rule
baseline. Only head and shoulders are required. Camera data stays on the device.

## Run

```powershell
.\.venv\Scripts\python.exe -m http.server 8001 --bind 127.0.0.1
```

Open http://127.0.0.1:8001/, click Start camera and allow access. All three live
cards compare the same frame. Calibration is only for the three-state rules.
Mirror/landmark controls and fullscreen support presentations. Pinned MediaPipe
0.10.35 JS/WASM and the pose asset are served with the website.

Read [Demo and viva guide](docs/DEMO_GUIDE.md) and
[Code walkthrough](docs/CODE_WALKTHROUGH.md).

## Research

The [S01 pilot](docs/PILOT_RESULTS_S01.md) is complete: one participant, eight
videos, 1,930 retained rows, four classes. Take 02 is development; take 03 is the
video-disjoint test. Website models are the frozen tested artifacts. The separate
all-data RF refit remains available for the optional Python research server.
Accuracy on new participants has not been established.

[Protocol](docs/RESEARCH_PROTOCOL.md) documents recording, QC and evaluation.
Public reference datasets were assessed and excluded from this experiment.
[Conference paper](docs/paper/STAY_UPRIGHT_IEEE.pdf) and
[LaTeX](docs/paper/STAY_UPRIGHT_IEEE.tex) retain the original measured results.
The PDF is an IEEE-style fallback; native IEEEtran compilation is unavailable.

## Main files

- `index.html`, `style.css`: structure and layout.
- `script.js`: camera lifecycle, MediaPipe and feedback.
- `posture-features.js`: 21-feature contract, matching Python.
- `model-runtime.js`: readable inference over learned JSON parameters.
- `research/`: Python recording, extraction, training and loopback server.
- `tools/export_browser_models.py`: model and paper exports.

## Verify

```powershell
.\.venv\Scripts\python.exe -m tools.export_browser_models
.\.venv\Scripts\python.exe -m tools.check_browser_parity
node tests/test_browser_models.cjs
node tests/test_browser.cjs
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Deploy

`tools/deploy_static.py` uploads an explicit public allowlist to the existing
Vercel project. Private recordings, landmark fixtures, joblib files and credentials
are excluded. HTTPS is required for a hosted camera demo.

This is a research prototype, not a clinical assessment. The timing display
measures one classifier call, not end-to-end latency. Counters record prediction
transitions and may increase when labels fluctuate. Exported-model parity verifies
implementation equivalence, not accuracy on new people.
