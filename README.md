# Perception (UMIC SeDriCa 2026-27) - README

Attempted:
- **Question 1 - The road disappears** (`Q1/`): code, results, figures, written report (`Q1_REPORT.md`) and appendix (`APPENDIX_Q1.md`).
- **Question 2 - Crossing with conflicting evidence** (`Q2/`): code, results, figures, written report (`Q2_REPORT.md`, parts (a)-(e)), appendix (`APPENDIX_Q2.md`) and the stage-by-stage working notes (`STAGE1_NOTES.md` ... `STAGE5_NOTES.md`). 
## Setup (both questions)
Tested with Python 3.12.3, CPU only, no GPU, no network. Packages: `Q1/requirements.txt` (numpy, pandas, matplotlib, tabulate, OpenCV); Q2 uses the same ones. Every script reads `SeDriCa_perception_starter_data.zip` directly from the folder it is run in (copy the zip into `Q1/` and into `Q2/`; do not unzip).

---

# Question 1

## Run instructions (Q1)
Q1 has no random seed in the main pipeline (the detector is deterministic; the stress tests use fixed NumPy seeds 0 and 1).

```bash
cd Perception/Q1
pip install -r requirements.txt
# copy SeDriCa_perception_starter_data.zip into this folder (scripts read it directly; do not unzip)
python lane_baseline.py        # baseline on 72 frames  -> baseline_results.csv
python run_repair.py           # revision on 72 frames  -> repair_results.csv (+ before/after table in the terminal)
python make_figures.py         # report figures + error table -> figures/*.png, error_table.csv, error_table.md
python annotate_frames.py      # annotated frames      -> figures/annotated_frames.png
# optional checks
python edge_case_tests.py      # synthetic edge cases vs the BASELINE (documents its known failures)
python repair_edge_cases.py    # the same cases vs the REVISION
python repair_stress_tests.py  # perturbed real frames (erased paint, noise, exposure, boosted seam, width drift)
```
Order matters: `run_repair.py` needs `baseline_results.csv`; `make_figures.py` needs both CSVs.

## Files (Q1)
| file | purpose |
|---|---|
| `Q1_REPORT.md` | answers (a)-(e), confidence rule, tables, failure frames |
| `APPENDIX_Q1.md` | references, decision log, failure log, AI usage note for Q1 |
| `lane_baseline.py` | baseline detector (frozen; thresholds and assumptions in its docstring) |
| `lane_repair.py` | revised detector with confidence; `calibrate_width()` fits the width model from the CLEAR images only |
| `run_repair.py`, `make_figures.py`, `annotate_frames.py` | evaluation and figures |
| `edge_case_tests.py`, `repair_edge_cases.py`, `repair_stress_tests.py` | tests |
| `notes/` | stage-by-stage working notes, including the audit that corrected earlier errors |

## Key parameters (Q1)
Baseline: gray > 190; rows v=260 and v=170; left/right split at u=240; fixed width 250 px. Revision: rows 95-319; paint = gray >= max(100, 0.75 x 99.9th percentile); run width 2-10 px; vote tolerance 2.5 px; slope limit 0.10; centre range u=170-310; unknown if confidence < 0.25 or < 15 supporting rows.

## Evaluation hygiene (Q1)
Neither detector class reads `lane_reference.csv`. The scripts load it only to score or draw results, and `lane_baseline.py` and `run_repair.py` do so after every prediction has been produced. The width model is calibrated from images only (`calibrate_width()` reads the CLEAR frames, not the CSV).

---

# Question 2

## Run instructions (Q2)
The rules are deterministic. The only randomness is the perturbation trials of part (e), seeded with **2026** (trial *i* of level *L* uses `SeedSequence([2026, ord(L), i])`, so a trial is reproducible regardless of run order). Whole pipeline: about 30 s on a sandbox CPU.

```bash
cd Perception/Q2
pip install -r ../Q1/requirements.txt          # same packages as Q1
# copy SeDriCa_perception_starter_data.zip into this folder (do not unzip)
python q2_stage1.py          # (a) annotated frames + signal-flow diagram -> figures/q2_annotated_frames.png, figures/q2_signal_flow.png
python q2_stage2.py          # (b) baseline rule     -> baseline_decisions.csv, baseline_decisions_with_reference.csv, figures/q2_baseline_timeline.png
python q2_stage3.py          # (c) revised vs baseline -> revised_decisions.csv, revised_decisions_with_reference.csv, stage3_summary.csv, figures/q2_revised_timeline.png
python q2_stage4.py          # (d) stopping-distance check -> stopping_distance_check.csv, figures/q2_stopping_margin.png
python q2_stage5.py          # (e) 200 trials x 2 levels, seed 2026 -> trials_all.csv, aggregate_level_A.csv, aggregate_level_B.csv
python q2_stage5_causes.py   # (e) why unnecessary STOPs happen -> unnecessary_stop_causes.csv
python q2_stage5_report.py   # (e) 20-trial table + figures -> trial_table_20.csv/.md, figures/q2_trials_summary.png, figures/q2_false_alarm_dangerous_delay.png
# optional checks (each tests-file ends with "failures: 0")
python q2_edge_tests.py              # baseline rule, 18 cases
python q2_edge_tests_revised.py      # revised rule, 34 cases
python q2_edge_tests_timeliness.py   # stopping-distance check, 16 cases
python q2_ablation.py                # what each revised mechanism contributes (+ deterministic V2X blackouts)
python q2_sensitivity.py             # sensitivity of the new thresholds
```
Order matters only for `q2_stage5_report.py`, which needs `trials_all.csv` from `q2_stage5.py`. Stages 1-5 otherwise recompute what they need and can be run independently. `q2_ablation.py` and `q2_sensitivity.py` print the ablation table when imported or run; that is expected.

## Files (Q2)
| file | purpose |
|---|---|
| `q2_rules.py` | `baseline()` (stateless) and `RevisedRule` (stateful, one instance per episode); all thresholds are constants at the top of each section |
| `q2_timeliness.py` | part (d): `check()` computes d_stop, margin, decision budget and required deceleration; `first_stop()` |
| `q2_stage1.py` ... `q2_stage5_report.py` | the stages above (a) to (e) |
| `q2_edge_tests*.py` | tests for baseline, revised rule and timeliness check |
| `q2_ablation.py`, `q2_sensitivity.py` | ablation and parameter sensitivity |
| `Q2_REPORT.md`, `APPENDIX_Q2.md` | written answers (a)-(e) with tables and figures; references, decision log, failure log, AI usage note |
| `STAGE1_NOTES.md` ... `STAGE5_NOTES.md` | analysis for parts (a) to (e), in order: what the car knows; baseline; stale V2X + disagreement + person memory; stopping distance; uncertainty trials |
| `*.csv`, `figures/*.png` | generated results; `*_with_reference.csv` files contain the reference columns and are for evaluation only |

## Key parameters (Q2)
- **Shared:** tau = 0.15 s, a = 0.8 m/s^2 (assignment values); d_stop = v*tau + v^2/(2a) = 0.52 m at the logged 0.8 m/s.
- **Baseline** (message age ignored): camera red at `red_score >= 0.5`; person probable at `person_score >= 0.5`, almost certain at `>= 0.9`. STOP if V2X red and camera red agree, or person >= 0.9; SLOW if exactly one source says red, person >= 0.5, or a camera score is missing; otherwise GO.
- **Revised:** keep the V2X message with the newest sample time (older repeats ignored); fresh if effective age <= 0.3 s; fresh V2X red -> STOP unless the camera is clearly not red (< 0.2); camera alone may STOP at >= 0.9 only when V2X is old or missing; a person score >= 0.9 is held for 0.3 s; unresolved evidence is SLOW but becomes STOP when `distance - d_stop < 0.5 m`.
- **Perturbation levels (identical for every rule):** A = noise sigma 0.15, camera frame lost 10 %, V2X message dropped 15 %, 6-frame outage burst with probability 0.5; B = sigma 0.30, 20 %, 30 %, 8-frame burst always. 200 trials per level; scores clipped to [0,1].

## Evaluation hygiene (Q2)
`q2_rules.py` and `q2_timeliness.py` never read `crossing_reference.csv`; decisions use only the evidence columns (and, in the trials, the perturbed copy of them). The scripts load the reference either after all decisions exist (`q2_stage2.py`, `q2_stage3.py`, `q2_stage4.py`) or only inside a scoring function (`q2_stage5*.py`, `q2_ablation.py`, `q2_sensitivity.py`). The person mask in `q2_stage1.py` subtracts the same frame of the `clear_green` episode; that is an offline measurement aid for the annotations and is not used by any rule. Scores are treated as scores, not probabilities; the check of what they mean is in `STAGE5_NOTES.md`.
