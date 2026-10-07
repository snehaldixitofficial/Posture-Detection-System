# Demo and viva guide

Open the deployed site, click **Start camera**, allow the camera, and keep your
head, ears and both shoulders visible. First start downloads the bundled
MediaPipe JavaScript and WebAssembly from the same site. No hips or full-body framing is required.

1. Sit upright. Point out the seven visible landmark dots and posture label.
2. Try slouching, then leaning left and right. Left/right are anatomical.
3. Switch Random Forest, SVM and XGBoost using the dropdown. The three cards
   show predictions for the same frame, even while rules are selected.
4. Toggle mirroring and landmarks. Mirroring changes the display only.
5. Select rules, sit upright and click **Set upright position**. The original rules
   report Correct/Slouch/Lean; the ML classifiers distinguish Lean_Left/Lean_Right.
6. Show Research, the paper, and the explanation. Stop the camera afterward.

## A one-minute explanation

“This system extracts head-and-shoulder landmarks using MediaPipe. I check seven
required joints, then calculate 21 geometry features. Distances are divided by
shoulder width to reduce scale dependence. Random Forest, RBF SVM and XGBoost
classify the same feature vector. The browser draws the landmarks and displays
the selected model's prediction. Camera data stays on the device.”

## Questions to expect

**Did you train MediaPipe?** No. It is a pretrained landmark detector. The three
posture classifiers were trained on features from the recorded posture clips.

**How much data?** One participant, eight completed videos, 1,930 retained rows.
Take 02 supplied 962 development rows; take 03 supplied 968 test rows. The initial
temporal validation split had a two-second exclusion gap. Final frozen classifiers
were fitted to take 02 after configuration selection. Adjacent frames are correlated.

**Which model won?** RF was selected on validation macro F1 (tie with SVM resolved
by documented order). XGBoost had the highest held-out test macro F1, 0.9886.
Do not choose a winner by reusing test labels.

**Why macro F1?** It gives each class equal weight and combines precision and recall.
Accuracy alone can hide weak performance on a minority class.

**Can it work on anyone?** The software can run on another person's webcam, but
accuracy on new participants is not established. Camera angle, lighting, body
proportions and domain differences can change predictions. Present this as a pilot.

**What is novel?** The auditable integration of visible head/shoulder geometry,
class-signal-preserving quality checks, separated recording evaluation and tested
browser deployment. These established classifiers are not new algorithms.

**Why no ML calibration?** Training and inference must use identical features.
Subtracting a new reference at inference would alter that contract.

**What does the speed display mean?** One classifier call only. It excludes
MediaPipe landmark detection, camera acquisition, rendering and the other models.

**Does it diagnose bad posture?** No. It classifies prompted geometric states in
this pilot. It does not establish medical or ergonomic risk.

## Troubleshooting

Use HTTPS or localhost, grant camera permission and close other apps using the
camera. If assets fail to load, check internet access and click Start again.
For invalid tracking, reposition so both shoulders, ears and face are visible.
Use even lighting and the same frontal head-and-shoulders framing as the study.

## Local demo

Run `.venv\Scripts\python.exe -m http.server 8001 --bind 127.0.0.1` from the project
root and open `http://127.0.0.1:8001/`. No Python prediction backend is needed for
this website. The separate research server is retained for Python inference.
