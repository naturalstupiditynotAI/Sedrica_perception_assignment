# Perception Q2 - Crossing with conflicting evidence

Every number below comes from the code in this folder (run instructions in `../README.md`). `crossing_reference.csv` is used only to score decisions after they exist, never as an input to a rule. Per-frame decisions with reasons are in `baseline_decisions.csv` and `revised_decisions.csv`.

## (a) Look before building
Figures: `figures/q2_annotated_frames.png` (one frame per episode, plus a second person frame) and `figures/q2_signal_flow.png`.

**What the data contains (measured).** Each episode has 24 frames at 0.1 s, speed 0.8 m/s, distance to the line 2.75 -> 0.91 m. The car approaches, so road lines and crosswalk move between frames. Message age (`time_s - v2x_sample_time_s`) is 0 except at frames 5-6, 12-13, 19-20, where it is 0.5-0.6 s: the message is a repeat of an older sample. In `late_red` the lamp turns red at frame 9 (221 red pixels from then on). In `person_crossing` the person is visible from frame 7 to 23, walks left 10 px per frame, with the foot at row 238; the road edges at that row are u~132-136 and ~369-371, so the person is outside the road in frames 7-8, on the edge at frame 9 and inside the path from frame 10.

**Direct versus uncertain.**
| quantity | status | evidence |
|---|---|---|
| `time_s`, `speed_mps`, `distance_to_line_m` | direct (treated as exact) | give d_stop = 0.8 x 0.15 + 0.8^2/(2 x 0.8) = 0.52 m |
| message age | exact arithmetic | |
| `v2x_light` | true only as of its sample time | `late_red` f12-13 say GREEN but were sampled at 0.6 / 0.7 s, before the lamp changed; fresh messages at f9-11 had already said RED |
| `red_score` | uncertain, lags and is noisy | `late_red` f9-10: lamp already red in the image, score 0.43 |
| `person_score` | uncertain in both directions | `clear_green` f6-7: 0.77 with nobody in the image; `person_crossing` f15-16: 0.29 with the person in the path |

**Why a visible person need not mean STOP.** `person_score` says a person is visible, not that the person is in the car's path. In `person_crossing` f7-8 the person stands beyond the right road edge with scores of 0.82 / 0.78. A path test would compare the person's foot position with the road edges on that row (the Q1 idea), which I did not build into the rule (see Further exploration); the rules use the supplied scores only.

*Provenance:* the person mask used for the annotation subtracts the same frame of the `clear_green` episode, which only an offline analysis can do; it is a measurement aid, not part of any decision rule. The annotated frames were chosen to show these cases, not at random, and were produced with AI assistance (see appendix).

## (b) Baseline rule (`q2_rules.baseline`, stateless, message age ignored)
States: **GO** continue; **SLOW** approach cautiously while evidence is unresolved or a hazard is unconfirmed; **STOP** brake to stand before the line. Thresholds were fixed before any scoring: 0.5 (camera "red", person "probable") and 0.9 (person "almost certain"; scores are not probabilities, so 0.5 means only "more likely than not").
1. V2X red **and** camera red -> STOP. 2. `person_score >= 0.9` -> STOP (position unknown, so treated as possibly in the path). 3. Exactly one source says red -> SLOW (a single noisy or old source never triggers STOP for the light). 4. `person_score >= 0.5` -> SLOW. 5. A camera score missing or invalid -> SLOW. 6. Otherwise GO. Invalid inputs (NaN, None, outside [0,1], a light other than red/green) count as "not available" (18 edge-case tests pass).

Timeline beside the inputs: `figures/q2_baseline_timeline.png`.
| episode | GO / SLOW / STOP | required STOP frames | missed STOP | unnecessary STOP | first required | first STOP |
|---|---|---|---|---|---|---|
| clear_green | 21 / 3 / 0 | 0 | 0 | 0 | - | none |
| late_red | 8 / 5 / 11 | 15 | 4 | 0 | 0.9 s | 1.1 s |
| person_crossing | 9 / 6 / 9 | 14 | 5 | 0 | 1.0 s | 1.1 s |
Where it fails: late_red f9-10 (fresh V2X red but `red_score` 0.43 -> only SLOW) and f12-13 (stale green conflicts with the camera -> SLOW); person_crossing f15-16 (score drops to 0.29 -> **GO** with the person in the path), f10 and f22-23 (scores 0.85 / 0.79 / 0.81, just under 0.9); clear_green f6-7 and f9 (score spikes -> needless SLOW).

## (c) Stale V2X and disagreement (`q2_rules.RevisedRule`)
**Misleading message if its age is ignored:** `late_red` **f12 and f13**: V2X says GREEN, sampled at 0.6 s and 0.7 s, i.e. before the lamp turned red at 0.9 s, while the previous (fresh) messages said RED. Read as "now", it conflicts with the camera (0.91 / 0.99) and the baseline only slows. Stale repeats at f5-6 and f19-20 carry the same state as the newer message and are harmless.

**The revised rule** (causal, one instance per episode; timelines with message age: `figures/q2_revised_timeline.png`):
1. *Latest information wins:* keep the V2X message with the newest sample time; a message sampled earlier is ignored. Effective age = `time_s - newest sample time`. Unreadable messages and sample times in the future are ignored.
2. *Age gate:* effective age <= 0.3 s (twice the 0.15 s system delay) is fresh; an older message cannot confirm or deny the present. On the given data the effective age never exceeds 0.2 s, so the gate only matters when the channel goes quiet (blackout test below).
3. *Fresh V2X red* -> STOP unless the camera clearly sees no red (`red_score < 0.2`); then unresolved. *Fresh green + camera red (>= 0.5)* -> two current sources disagree -> unresolved. *Old or missing V2X:* camera >= 0.9 -> STOP; 0.5-0.9 -> unresolved; an old red with no camera red -> unresolved; an old green cannot veto a red camera.
4. *Person memory (short memory):* a score >= 0.9 means STOP and, for 0.3 s afterwards, a dropout or a missing score does not release it.
5. **What the car does while it cannot resolve a disagreement:** SLOW (reduce speed, keep approaching cautiously, keep reading evidence). It may not wait forever: when the stopping margin `distance - d_stop` falls below 0.5 m (about 0.6 s of travel at 0.8 m/s) unresolved becomes STOP.

Nominal result (scored afterwards):
| episode | rule | GO / SLOW / STOP | missed STOP | unnecessary STOP | first STOP |
|---|---|---|---|---|---|
| late_red | baseline -> revised | 8/5/11 -> 8/1/15 | 4 -> **0** | 0 -> 0 | 1.1 s -> **0.9 s** |
| person_crossing | baseline -> revised | 9/6/9 -> 7/4/13 | 5 -> **1** | 0 -> 0 | 1.1 s -> 1.1 s |
| clear_green | both | 21/3/0 | 0 | 0 | none |
The one remaining miss is person_crossing f10: the person has just stepped into the path and the score is 0.85, just under 0.9.

**Which mechanism does what** (`q2_ablation.py`; missed STOP, three episodes in order). Fresh-red rule alone fixes f9-10; either age handling fixes f12-13 on this data; the person memory fixes f15-16 (and f22-23): nominal missed (clear/late/person): baseline 0/4/5; + fresh-red rule 0/2/5; + age threshold 0/0/5; + supersession 0/0/5; + margin escalation 0/0/3; + person memory (= revised) **0/0/1**. In a deterministic stress scenario I constructed (V2X silent from f8) the baseline never STOPs for the red light (15 missed, every frame SLOW because a single source cannot STOP) and the revision STOPs from f11 but still misses 5 frames (f9-10: last message green and only 0.2-0.3 s old, camera 0.43; f14, 15, 17: camera 0.86 / 0.87 / 0.76, below the 0.9 needed without V2X).

Sensitivity (`q2_sensitivity.py`): nominal results are unchanged over A_FRESH 0.1-0.7, T_RED_STRONG 0.7-0.95, M_ESC 0.3-0.8; `T_CLEAR` must stay below 0.43 and the memory window must be at least 0.2 s, because those are what the weak 0.43 score and the 0.2 s dropout in this data demand. 34 edge-case tests for the revised rule pass.

## (d) Stopping distance at the first STOP request
d_stop = v tau + v^2/(2a), tau = 0.15 s, a = 0.8 m/s^2 -> **0.52 m** at 0.8 m/s. Comfortable stopping appears possible when `distance_to_line_m >= d_stop` (equivalently the deceleration needed to stop at the line after the delay is <= 0.8 m/s^2). Figure: `figures/q2_stopping_margin.png`.
| episode | rule | first STOP | distance | d_stop | margin | comfortable? | extra decision delay absorbable | a_required |
|---|---|---|---|---|---|---|---|---|
| clear_green | baseline and revised | **no STOP request** | | | | | | |
| late_red | baseline | f11 (1.1 s) | 1.87 m | 0.52 m | 1.35 m | yes | 1.69 s | 0.18 m/s^2 |
| late_red | revised | f9 (0.9 s) | 2.03 m | 0.52 m | 1.51 m | yes | 1.89 s | 0.17 m/s^2 |
| person_crossing | baseline and revised | f11 (1.1 s) | 1.87 m | 0.52 m | 1.35 m | yes | 1.69 s | 0.18 m/s^2 |
**When SLOW came first:** late_red baseline: SLOW f9-10 because fresh V2X said red but `red_score` was 0.43 < 0.5; STOP at f11 when it reached 0.99 and the sources agreed (revised: STOP at f9, 0.43 does not clearly contradict a fresh red). person_crossing: SLOW f7-10 on `person_score` 0.82 / 0.78 / 0.61 / 0.85 (probable, position unknown); STOP at f11 when it hit 0.99. clear_green: its 3 SLOW frames are score spikes with no person in the image.
**Was it too late?** No STOP here is too late by distance, and none could be: even at the last frame (2.3 s, 0.91 m) the margin is 0.39 m, and the last comfortable STOP time is 2.79 s, after the window ends. The real cost is response delay: the baseline wastes 0.16 m (11 % of a 1.51 m margin) in late_red and 0.08 m (6 %) in person_crossing (reference used for the delays). The log has the car at constant speed, so the numbers mean "if STOP had been requested at that frame". The check does flag a late STOP (unit test: 1.5 m/s at 1.5 m -> d_stop 1.63 m).

## (e) Uncertainty test
**Protocol.** Seed **2026** (trial *i* of level *L*: `SeedSequence([2026, ord(L), i])`). Each trial builds one perturbed copy of the evidence; the baseline, the revised rule and two ablation variants all run on exactly that copy. Perturbations: Gaussian noise on both scores (clipped to [0,1]), lost camera frames (both scores missing), dropped V2X messages, plus an outage burst. Level A (primary): sigma 0.15, 10 % frames lost, 15 % messages dropped, 6-frame burst with probability 0.5. Level B (stress): 0.30, 20 %, 30 %, 8-frame burst always. 200 trials per level; the first 20 of level A are tabulated. *Missed STOP* = required frame whose decision is not STOP (SLOW and GO both count); *unnecessary STOP* = STOP on a frame where it is not required; *delay* = first required frame to the first STOP at or after it, "none" if none.

**20 trials, level A (baseline / revised):**
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

**All 200 trials** (figure `figures/q2_trials_summary.png`):
| level | episode (required) | missed STOP mean (p90): baseline -> revised | unnecessary STOP mean (% trials with any) | delay median (p90) s |
|---|---|---|---|---|
| A | late_red (15) | 7.38 (10.1) -> **1.12 (3.0)** | 0.01 (1 %) -> 0.04 (1 %) | 0.2 (0.6) -> **0.0 (0.2)** |
| A | person_crossing (14) | 7.38 (10.0) -> **1.14 (3.0)** | 0.50 (43 %) -> 1.11 (43 %) | 0.1 (0.2) -> 0.0 (0.2) |
| A | clear_green (0) | - | 0.38 (34 %) -> **1.70 (51.5 %)** | - |
| B | late_red (15) | 10.96 (13.0) -> **3.82 (6.1)** | 0.12 (12 %) -> 0.50 (12 %) | 0.5 (1.0) -> **0.2 (0.4)** |
| B | person_crossing (14) | 8.66 (11.0) -> **1.89 (4.0)** | 0.88 (62.5 %) -> 1.62 (63 %) | 0.1 (0.31) -> 0.0 (0.2) |
| B | clear_green (0) | - | 0.90 (63 %) -> **3.75 (82 %)** | - |
Paired on identical trials the revision has fewer missed frames in 200 of 200 trials for both required episodes at both levels, never more. At level B the baseline gave no STOP at all after the required frame in 2 of 200 late_red trials; the revision in none. No first STOP was too late by distance in any trial (0 of 800 per rule).

**The price.** Unnecessary STOP frames by cause, level A, summed over 200 trials and three episodes: baseline 177, all raw `person_score >= 0.9` noise spikes; revised 570 = the same 177 + **334 from the person memory** (a 0.3 s hold stretches every spike by ~2 frames) + 59 from the margin escalation (camera frame missing / person probable near the line) + 0 from the stale-V2X and disagreement logic (level B: 6 frames, camera strongly red while V2X old or missing). So the revision trades fewer missed STOPs for more false STOPs, almost all of them from the person memory. I did not retune the rule after seeing the trials.

**False alarm and dangerous delay in the original frames** (`figures/q2_false_alarm_dangerous_delay.png`).
- *False alarm, clear_green f6:* `person_score` 0.77 (and 0.77 at f7, 0.51 at f9) with only an empty road and a green lamp visible. Both rules SLOW. It happens because the score is a noisy detector output, not a person; it stays SLOW only because 0.77 < 0.9. In the trials such spikes cross 0.9 and cause false STOPs (177 frames at level A).
- *Dangerous delay 1, late_red f9:* lamp red and V2X red (age 0) but `red_score` is 0.43. The baseline requires the camera to agree before STOP and reads the old message as current: STOP comes at f11 (0.2 s, 0.16 m late) and at f12-13 it falls back to SLOW on a stale green. The revision STOPs at f9.
- *Dangerous delay 2, person_crossing f15-16:* person in the path, score falls to 0.29 for two frames (0.99 before and after), the baseline says GO: a stateless rule has no memory that a person was almost certainly there 0.1 s ago. The revision holds the STOP.

**What the scores mean.** Used as scores, not probabilities. Checked against the reference on 72 frames: `red_score` below 0.2: 0 of 48 frames truly red; 0.2-0.5: 2 of 11; 0.5-0.9: 3 of 3; 0.9 or above: 10 of 10. `person_score` vs person on the crossing: below 0.2: 0 of 44; 0.2-0.5: 2 of 9; 0.5-0.9: **3 of 10**; 0.9 or above: 9 of 9. The ordering is informative but a "0.8" is not 80 %, and 72 frames cannot calibrate the 0.9 threshold.

## Limits
- The perturbations are my model of sensor trouble, not measured failures, and all 200 trials start from the same 72 frames.
- `T_CLEAR` (< 0.43) and the memory window (>= 0.2 s) are bounded by this data, not by independent evidence.
- Without person position, the rules cannot tell a person on the sidewalk from one in the path; the 0.9 rule treats every near-certain person as in the path.
- The data never reaches the too-late zone, so part (d) shows a generous margin, not that timeliness is solved.
- About 1.1 required frames per trial are still missed at level A; I did not break these down by cause.

## Further exploration (not done)
Measuring the pedestrian's position and using the Q1 road region instead of the score alone, and a belief filter for the light state, were not attempted (see `APPENDIX_Q2.md`).
