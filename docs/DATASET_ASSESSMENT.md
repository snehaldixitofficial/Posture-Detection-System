# Public dataset assessment — 7 October 2026

A public dataset can support the RF/SVM/XGBoost comparison when participant
identities, posture labels, and measurement definitions are preserved. Participant
count alone is insufficient: random frame splits cannot establish performance on
previously unseen people.

## Existing reference CSV

Local audit: 5,949 rows, with Upright (3,521), Stiff (2,045), and Slouched (383).
It has no subject IDs, frame/video references, or left/right labels. It cannot
provide the requested subject-independent four-class experiment. Do not generate
subject IDs from row order or turn body-lean measurements into labels.

## Downloaded MultiPosture

Source: https://zenodo.org/records/14230872
DOI: 10.5281/zenodo.14230872
License: CC BY 4.0, confirmed from the saved publisher metadata.
Creators: David Carneros Prado, Luis Cabañero Gómez, Jesus Fontecha,
Ramon Hervas, Iván González Díaz, and Esperanza Johnson.

The downloaded CSV contains 4,794 rows, 13 subject IDs, 99 coordinate columns
(33 joints times three), and two posture-label columns. Its MD5 matches the
publisher's checksum. Local checks find no missing values, nonfinite numeric
values, duplicated full rows, or duplicated coordinate rows.

| Upper-body label | Meaning | Downloaded rows |
|---|---|---:|
| TUP | Upright | 1,615 |
| TLF | Lean forward | 1,897 |
| TLB | Lean backward | 442 |
| TLL | Lean left | 420 |
| TLR | Lean right | 420 |

Subject 5 has no backward-lean samples. A five-class evaluation must report class
support per participant and handle this absence without inventing observations.
The publisher's description gives different frame and selected-joint counts;
use the actual file schema and saved audit when reporting this experiment.

This supports a real subject-independent public-data comparison. It changes the
original experiment: lean-forward is not a verified slouch label, and only
skeletal coordinates are published. Original-image QC and re-extraction of the
publisher's videos are unavailable. Hip-relative 3D coordinates require a
separate feature contract from the browser's original image-coordinate pipeline.
Live webcam transfer must be checked independently; offline public-data scores
must not be presented as measured webcam accuracy.

The final project retained the original four-class head-and-shoulder recording
study. One volunteer completed the S01 pilot; its results are documented in
`PILOT_RESULTS_S01.md`. MultiPosture remains a reference dataset and was excluded
from the deployed models and reported pilot scores.

Machine-readable audit: `verification/dataset_audit.json`.
Downloaded data and publisher metadata: `data/public/` in the project root.
