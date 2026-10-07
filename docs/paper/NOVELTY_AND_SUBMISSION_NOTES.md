# Research contribution and submission notes

The paper is **Stay Upright: Auditable Head-and-Shoulder Posture Classification
with Video-Disjoint Evaluation**, by Snehal Dixit, VIT Bhopal University, SCAI.

## What you can defend as the contribution

The project connects a head-and-shoulder feature representation, an audited
quality policy, fair model/baseline evaluation, and verified browser deployment.
Its contribution is incremental engineering and experimental evidence, rather
than inventing RF, SVM, XGBoost or frontal posture recognition.

| Contribution | Implemented evidence | Practical reason |
|---|---|---|
| Explicit observation boundary | Seven required visible joints; 21 features; no hips or legs inspected | Webcam framing can exclude lower-body landmarks |
| Class-retention audit | Revised checks recover 421 Slouch rows while maintaining the 0.65 confidence threshold | A filter assuming upright geometry can erase the class being studied |
| Controlled comparison | Identical feature rows and test videos; two validation candidates per model family | Differences between classifiers are easier to interpret |
| Baseline compatibility | Original three-state rules compared to collapsed ML labels; directional extension reported separately | Three and four classes should not be treated as the same task |
| Deployment equivalence | 5,790 labels match Python on all 1,930 recorded rows | The browser demonstrates the actual evaluated classifiers |

The quality audit is the most concrete diagnostic finding. Signed and expanded
planar features also improved the exploratory comparisons, but the ablation
reuses the test recordings and is not an independent confirmatory experiment.
Depth proxies did not consistently improve performance; the paper retains this
negative finding.

## How to explain the novelty to your guide

“The classifiers are standard. My contribution is the controlled, auditable
pipeline for a webcam showing only the head and shoulders. I found that an
upright-assuming filter removed 421 slouch examples, corrected the policy without
lowering confidence requirements, compared the models on separate recordings,
and checked that the deployed browser reproduces the evaluated models.”

Do not claim a first-ever method, superiority across users, perfect natural-use
accuracy, statistical significance or clinical validity. Prior research already
uses frontal face/shoulder features and Random Forest. The manuscript cites this
and distinguishes the specific work completed here.

## What the manuscript covers

- Abstract and keywords, introduction and explicit research contributions.
- Related work and research position, with eleven numbered references.
- Feature definitions, normalization, quality checking and sampled review.
- Recording protocol, provenance, temporal validation gap and video test split.
- RF/SVM/XGBoost configurations and compatible rule baselines.
- Accuracy, macro precision/recall/F1, class errors and confusion matrices.
- Training/inference timings, quality audit and exploratory feature ablation.
- Browser model switching, local processing and Python/JavaScript parity.
- Limitations, reproducibility, future participant evaluation and conclusion.

## Before submission

Choose a conference so its page limit, anonymity policy and exact template can
be applied. The source uses IEEEtran conference mode. The supplied PDF is an
IEEE-style ReportLab export because the native compiler currently fails during
platform initialization; IEEEtran compilation and any required PDF eXpress check
remain unverified.

The study contains one participant and one session. The planned multi-person
experiment has not been completed. More participants, independent human review,
the applicable institutional research determination and cross-person testing
would materially strengthen a full research submission. The current evidence
supports a pilot/prototype paper; acceptance and venue suitability are unknown.

The requested acknowledgment removal is retained. Check the target venue's
content-disclosure requirements before submission. This note is not part of the
manuscript body.
