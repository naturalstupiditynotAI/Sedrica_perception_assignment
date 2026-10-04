# Q2 Stage 5 - Uncertainty test (part e)

## Protocol (identical for every rule)
- Seed **2026**; trial *i* of level L draws from `SeedSequence([2026, ord(L), i])`, so a trial is reproducible and independent of call order (checked). Each trial builds ONE perturbed copy of the evidence; baseline, revised and the two ablation variants all run on exactly that copy.
- Perturbations (per episode): Gaussian noise on `red_score` and `person_score` (clipped to [0,1]); camera frames lost (both scores missing) with probability p_cam; V2X messages dropped with probability p_msg; plus an outage burst of consecutive dropped messages. **Level A (primary):** sigma 0.15, p_cam 0.10, p_msg 0.15, 6-frame burst with probability 0.5. **Level B (stress):** sigma 0.30, p_cam 0.20, p_msg 0.30, 8-frame burst always. 200 trials per level; the first 20 of level A are shown below.
- Scoring (reference used only here): **missed STOP** = required frame whose decision is not STOP (SLOW and GO both count); **unnecessary STOP** = STOP on a frame where it is not required; **delay** = time from the first required frame to the first STOP at or after it, "none" if there is none (an earlier false STOP is counted as unnecessary, not as a negative delay). `clear_green` requires no STOP: only unnecessary STOP applies.
- The first STOP after the required frame is also run through the part-(d) check: **0 of 800 per rule were not comfortable** (2 levels x 200 trials x 2 required episodes; the margin is never exhausted inside the 2.3 s window).

## 20 trials, level A (baseline / revised)
|   trial | clear_green: unnecessary STOP   | late_red: missed STOP   | late_red: unnecessary STOP   | late_red: delay (s)   | person_crossing: missed STOP   | person_crossing: unnecessary STOP   | person_crossing: delay (s)   |
|--------:|:--------------------------------|:------------------------|:-----------------------------|:----------------------|:-------------------------------|:------------------------------------|:-----------------------------|
|       0 | 0 / 0                           | 10 / 1                  | 0 / 0                        | 0.1 / 0.0             | 7 / 2                          | 0 / 0                               | 0.0 / 0.0                    |
|       1 | 0 / 1                           | 8 / 0                   | 0 / 0                        | 0.5 / 0.0             | 7 / 1                          | 0 / 0                               | 0.1 / 0.1                    |
|       2 | 1 / 5                           | 12 / 5                  | 0 / 0                        | 0.0 / 0.0             | 7 / 0                          | 1 / 3                               | 0.0 / 0.0                    |
|       3 | 0 / 0                           | 6 / 0                   | 0 / 0                        | 0.0 / 0.0             | 8 / 0                          | 1 / 2                               | 0.0 / 0.0                    |
|       4 | 1 / 5                           | 4 / 1                   | 0 / 0                        | 0.2 / 0.1             | 6 / 1                          | 0 / 0                               | 0.1 / 0.1                    |
|       5 | 1 / 4                           | 4 / 0                   | 0 / 0                        | 0.2 / 0.0             | 8 / 0                          | 1 / 3                               | 0.1 / 0.0                    |
|       6 | 0 / 1                           | 9 / 0                   | 0 / 0                        | 0.2 / 0.0             | 8 / 0                          | 1 / 3                               | 0.1 / 0.0                    |
|       7 | 0 / 0                           | 5 / 0                   | 0 / 0                        | 0.2 / 0.0             | 7 / 2                          | 0 / 0                               | 0.2 / 0.2                    |
|       8 | 0 / 0                           | 6 / 0                   | 0 / 0                        | 0.2 / 0.0             | 7 / 2                          | 1 / 2                               | 0.1 / 0.0                    |
|       9 | 1 / 5                           | 7 / 0                   | 0 / 0                        | 0.0 / 0.0             | 11 / 5                         | 0 / 0                               | 0.1 / 0.1                    |
|      10 | 1 / 5                           | 5 / 0                   | 0 / 0                        | 0.0 / 0.0             | 10 / 5                         | 0 / 0                               | 0.2 / 0.2                    |
|      11 | 0 / 0                           | 5 / 1                   | 0 / 0                        | 0.1 / 0.1             | 9 / 0                          | 2 / 3                               | 0.1 / 0.0                    |
|      12 | 2 / 6                           | 7 / 0                   | 0 / 0                        | 0.5 / 0.0             | 5 / 0                          | 0 / 0                               | 0.0 / 0.0                    |
|      13 | 0 / 0                           | 6 / 0                   | 0 / 0                        | 0.2 / 0.0             | 11 / 7                         | 0 / 0                               | 0.7 / 0.7                    |
|      14 | 0 / 0                           | 10 / 3                  | 0 / 0                        | 0.2 / 0.2             | 7 / 1                          | 0 / 0                               | 0.0 / 0.0                    |
|      15 | 0 / 0                           | 6 / 0                   | 0 / 0                        | 0.2 / 0.0             | 7 / 1                          | 1 / 3                               | 0.0 / 0.0                    |
|      16 | 1 / 4                           | 5 / 0                   | 0 / 0                        | 0.2 / 0.0             | 8 / 2                          | 0 / 0                               | 0.2 / 0.2                    |
|      17 | 1 / 4                           | 7 / 1                   | 0 / 0                        | 0.0 / 0.0             | 10 / 2                         | 0 / 0                               | 0.1 / 0.1                    |
|      18 | 0 / 1                           | 8 / 0                   | 1 / 4                        | 0.1 / 0.0             | 6 / 0                          | 0 / 0                               | 0.0 / 0.0                    |
|      19 | 1 / 4                           | 10 / 4                  | 0 / 0                        | 0.6 / 0.2             | 10 / 3                         | 0 / 0                               | 0.2 / 0.2                    |

## All 200 trials
| level | episode (required frames) | missed STOP, mean (p90) baseline -> revised | unnecessary STOP, mean (% trials with any) baseline -> revised | delay, median (p90) s baseline -> revised |
|---|---|---|---|---|
| A | late_red (15) | 7.38 (10.1) -> **1.12 (3.0)** | 0.01 (1 %) -> 0.04 (1 %) | 0.2 (0.6) -> **0.0 (0.2)** |
| A | person_crossing (14) | 7.38 (10.0) -> **1.14 (3.0)** | 0.50 (43 %) -> 1.11 (43 %) | 0.1 (0.2) -> 0.0 (0.2) |
| A | clear_green (0) | - | 0.38 (34 %) -> **1.70 (51.5 %)** | - |
| B | late_red (15) | 10.96 (13.0) -> **3.82 (6.1)** | 0.12 (12 %) -> 0.50 (12 %) | 0.5 (1.0) -> **0.2 (0.4)** |
| B | person_crossing (14) | 8.66 (11.0) -> **1.89 (4.0)** | 0.88 (62.5 %) -> 1.62 (63 %) | 0.1 (0.31) -> 0.0 (0.2) |
| B | clear_green (0) | - | 0.90 (63 %) -> **3.75 (82 %)** | - |
Paired on the same trials, the revision has fewer missed STOP frames in **200 of 200** trials for both required episodes at both levels, never more. At level B the baseline gave no STOP at all after the required frame in 2 of 200 late_red trials (1 %); the revision in 0. Figure: `figures/q2_trials_summary.png`; all rows: `trials_all.csv`.

## The price: more unnecessary STOPs (this is a trade-off, not a free win)
Unnecessary STOP frames by cause, summed over 200 level-A trials and all three episodes (`q2_stage5_causes.py`):
| cause | baseline | revised |
|---|---|---|
| `person_score >= 0.9` (raw, a noisy spike) | 177 | 177 |
| person memory hold (0.3 s after a score >= 0.9) | - | **334** |
| margin escalation (camera frame missing / person probable, near the line) | - | 59 |
| fresh V2X red / camera strongly red with V2X old (stale-message handling) | - | **0** (level B: 6) |
Reading: the stale-V2X and disagreement changes (part c) cost no unnecessary STOPs at level A and only 6 frames at level B (camera strongly red while V2X was old or missing, all 200 trials). The extra false STOPs come from the person memory, which holds *any* score >= 0.9 for 0.3 s, so each noise spike is stretched by ~2 frames, and from the margin escalation, which turns "cannot rule out a hazard" into STOP near the line. The memory is also what repairs `person_crossing` (missed 5.96 -> 1.14 per trial; `revised_no_person_memory` row in `aggregate_level_A.csv`). I did **not** retune the rule after seeing these trials. Two candidate fixes I have not implemented: arm the memory only after two consecutive scores >= 0.9; do not escalate on a missing camera frame while a fresh V2X message says green.

## False alarm and dangerous delay in the original frames (`figures/q2_false_alarm_dangerous_delay.png`)
- **False alarm: clear_green f6.** `person_score` jumps to 0.77 (and 0.77 at f7, 0.51 at f9) with only an empty road and a green lamp in the image. Both rules SLOW. It happened because the person score is a noisy detector output, not a person; it stayed SLOW only because 0.77 < 0.9. In the perturbation trials the same kind of spike crosses 0.9 and causes a false STOP (177 frames at level A).
- **Dangerous delay 1: late_red f9.** The lamp is red in the image and V2X says red (age 0), but `red_score` is 0.43, below the 0.5 the baseline needs for "camera red"; two sources "disagree" so it only slows. STOP comes at f11, 0.2 s late (0.16 m of travel), and at f12-13 the baseline drops back to SLOW because a stale green (sampled before the change) conflicts again. Why: the baseline requires the camera to agree before STOP and reads the old message as current. Revised: STOP at f9.
- **Dangerous delay 2: person_crossing f15-16.** The person is in the path, `person_score` falls to 0.29 for two frames (0.99 before and after) and the baseline says GO: a stateless rule has no memory that a person was almost certainly there 0.1 s ago. Revised: STOP held.

## What the scores mean (checked against the reference, 72 frames; evaluation only)
Scores are used as **scores, not probabilities**. `red_score`: below 0.2: 0 red of 48 frames; 0.2-0.5: 2 of 11; 0.5-0.9: 3 of 3; above 0.9: 10 of 10. `person_score` vs person on the crossing: below 0.2: 0 of 44; 0.2-0.5: 2 of 9; 0.5-0.9: **3 of 10**; 0.9 or above: 9 of 9. The ordering is useful but a "0.8" is not 80 %; the 0.9 threshold was right on all 9 frames here, but 72 frames cannot calibrate it.

## Limits
- The perturbations are my model of sensor trouble, not measured failures; results depend on level, and the base data are three episodes of 24 frames.
- Missed STOP counts SLOW as a miss. The revised rule still misses about 1.1 required frames per trial at level A (3.8 and 1.9 at level B); I did not break these down by cause.
- Because every trial starts from the same 72 frames, the 200 trials are not independent samples of the world.
- Part (d) is unaffected: no first STOP was ever too late by distance.

## Files
`q2_stage5.py` (trials), `q2_stage5_causes.py`, `q2_stage5_report.py`, `trials_all.csv`, `aggregate_level_A.csv`, `aggregate_level_B.csv`, `trial_table_20.csv/.md`, `unnecessary_stop_causes.csv`, `figures/q2_trials_summary.png`, `figures/q2_false_alarm_dangerous_delay.png`.
