# S01 head-and-shoulders pilot results

Trained Random Forest, RBF SVM and XGBoost on 962 take-02 frames; evaluated on 968 separate take-03 frames. The complete reviewed dataset contains 1930 frames from eight videos, one participant and four protocol classes.

Hyperparameters and the live model (Random_Forest) were chosen using 664 early training frames and 262 late validation frames from take 02. 36 frames in the two-second boundary gaps were excluded from tuning. No take-03 frames entered model selection.

| Model | Test accuracy | Macro precision | Macro recall | Macro F1 | Validation F1 | Training seconds | Median prediction ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Random_Forest | 0.9835 | 0.9845 | 0.9835 | 0.9835 | 0.9807 | 0.287 | 7.624 |
| SVM_RBF | 0.9514 | 0.9593 | 0.9514 | 0.9510 | 0.9807 | 0.004 | 0.217 |
| XGBoost | 0.9886 | 0.9891 | 0.9886 | 0.9886 | 0.9494 | 0.240 | 0.231 |

Original three-state rules: accuracy 0.9762, macro F1 0.9756. The separately named four-class directional extension: accuracy 0.9762, macro F1 0.9762. The JSON also reports each ML model collapsed to three states for a fair comparison with the original rule.

Saved outputs include all three frozen test models, a separately refitted live winner, per-class reports, confusion matrices, predictions, comparison chart, selected parameters, split row IDs and checksum provenance. The feature extractor uses only visible head/shoulder landmarks; hidden hips are ignored.

One person, one environment, two takes per class. Test videos are disjoint but from the same recording session. Tuning blocks share training videos; temporal dependence remains despite the gap. No between-person generalization, subject SD, significance test, or clinical slouch assessment is supported. Slouch is the recorded head/shoulder protocol gesture. Assistant sample review is not exhaustive human video review. Deployment refit includes test data, so test scores describe the frozen take-02 models only. Timings exclude pose extraction and transport.

Completed for this pilot: collection, landmark extraction, sample review, cleaning, model fitting/tuning, held-out-video evaluation, baseline comparisons, saved artifacts and local live integration. Multi-person collection and subject-independent evaluation remain future work.

Random Forest and SVM tied on validation macro F1; the deterministic model listing order selected Random Forest. XGBoost had the highest test score, but the test was not used to change the selected live model.

Verification: all 13 Python tests, browser contract checks and JavaScript syntax passed. The running deployment endpoint matched direct inference for recorded samples from all four classes. Fresh webcam performance has not been measured.
