# Q2 Stage 3 - Stale V2X, disagreement, and short memory (part c)

Scope chosen: stale V2X + camera/message disagreement (what part c asks), plus a short memory for the person score (the dropout at person_crossing f15-16 was the baseline's most dangerous frame). Thresholds below were set from reasoning before scoring; see "Limits" for the two that the data bounds.

## Which message misleads if its age is ignored
`late_red` **f12 and f13**: V2X says GREEN, sampled at 0.6 s / 0.7 s (age 0.6 s). The lamp turned red at 0.9 s and fresh messages at f9-11 had already said RED, so this green describes a moment *before* the change. A rule that reads it as "now" sees a conflict with the camera (0.91 / 0.99) and only slows. The same stale repeats occur at f5-6 and f19-20 in every episode; they are harmless there because they carry the same state as the newer message.

## The revised rule (`q2_rules.RevisedRule`, causal: current + earlier frames only)
1. **Latest information wins.** Keep the V2X message with the newest *sample time* seen so far; a message sampled earlier than that (a repeat/delay) is ignored. Effective age = `time_s - newest sample time`. Unreadable messages and sample times in the future are ignored.
2. **Age gate.** Effective age <= 0.3 s (2 x the 0.15 s system delay) = fresh; otherwise the message cannot confirm or deny the present. Only matters when the channel goes quiet (here, max effective age is 0.2 s, so the gate never binds on the given data).
3. **Fresh V2X red** -> STOP unless the camera *clearly* sees no red (`red_score < 0.2`); then unresolved. A weak camera score (0.43 at f9-10) no longer vetoes a current message.
4. **Fresh V2X green + camera red (>=0.5)** -> two current sources disagree -> unresolved. **Old/missing V2X:** camera >= 0.9 -> STOP; 0.5-0.9 -> unresolved (single source); an old *red* with no camera red -> unresolved ("cannot confirm green"); an old *green* cannot veto a red camera.
5. **Person memory:** `person_score >= 0.9` -> STOP (as before); for 0.3 s afterwards a score dropout or a missing score does not release it (not extended by held frames).
6. **While unresolved the car does SLOW** (reduce speed, keep approaching cautiously, keep reading new evidence). It may not wait forever: if stopping margin `distance - d_stop` falls below 0.5 m (about 0.6 s of travel at 0.8 m/s), unresolved becomes **STOP**. d_stop = v*0.15 + v^2/(2*0.8) = 0.52 m at 0.8 m/s.
Everything else (person >= 0.5 -> unresolved, missing camera score -> unresolved) is unchanged from the baseline.

## Result on the given data (scored afterwards with the reference)
| episode | rule | GO | SLOW | STOP | required | missed STOP | unnecessary STOP | first required | first STOP |
|---|---|---|---|---|---|---|---|---|---|
| clear_green | baseline | 21 | 3 | 0 | 0 | 0 | 0 | - | - |
| clear_green | revised | 21 | 3 | 0 | 0 | 0 | 0 | - | - |
| late_red | baseline | 8 | 5 | 11 | 15 | 4 | 0 | 0.9 s | 1.1 s |
| late_red | revised | 8 | 1 | 15 | 15 | **0** | 0 | 0.9 s | **0.9 s** |
| person_crossing | baseline | 9 | 6 | 9 | 14 | 5 | 0 | 1.0 s | 1.1 s |
| person_crossing | revised | 7 | 4 | 13 | 14 | **1** | 0 | 1.0 s | 1.1 s |

Changed frames: late_red f9-10 (fresh red vs weak camera) and f12-13 (stale green) SLOW -> STOP; person_crossing f15-16 (dropout) GO -> STOP and f22-23 SLOW -> STOP. Still missed: person_crossing f10, score 0.85 one frame after the person stepped into the path; without position the rule cannot do better. Figure: `figures/q2_revised_timeline.png`; per-frame reasons: `revised_decisions.csv`.

## What each mechanism contributes (`q2_ablation.py`; missed STOP / unnecessary STOP, three episodes in order)
| variant | nominal data | late_red, V2X silent from f8 |
|---|---|---|
| baseline | 0/0, 4/0, 5/0 | 0/0, **15**/0, 5/0 |
| age ignored, fresh-red rule only | 0/0, 2/0, 5/0 | 15/0 for late_red |
| + age threshold only | 0/0, 0/0, 5/0 | 5/0 |
| + supersession | 0/0, 0/0, 5/0 | 5/0 |
| + margin escalation | 0/0, 0/0, 3/0 | 5/0 |
| + person memory (= revised) | 0/0, 0/0, **1**/0 | 5/0 |
Reading: the fresh-red rule fixes f9-10; either age handling fixes f12-13 on this data; the person memory fixes f15-16 and, with the 0.3 s window, f22-23 (so the margin escalation changes nothing on the nominal data once memory exists; it is covered only by unit tests). V2X blackout is a deterministic stress scenario I constructed (messages removed from f8); the baseline then never STOPs for the red light (every frame is SLOW, single source), the revision STOPs from f11. The revision still misses f9-10 (last message green, 0.2-0.3 s old = still fresh, camera 0.43) and f14, f15, f17 (camera 0.86 / 0.87 / 0.76, below the 0.9 needed for a camera-only STOP).

## Sensitivity (`q2_sensitivity.py`, nominal missed STOP / unnecessary)
A_FRESH 0.1-0.7, T_RED_STRONG 0.7-0.95, M_ESC 0.3-0.8: nominal unchanged (1 / 0). T_CLEAR 0.1-0.4: unchanged; 0.45: 3 missed (f9-10 would be vetoed by the 0.43 camera score). H_PERSON 0.2-1.0: 1 missed; 0.1: 2; 0: 3. Blackout scenario: T_RED_STRONG 0.7 -> 3 missed, 0.95 -> 10.

## Limits
- T_CLEAR must stay below 0.43 and H_PERSON at or above 0.2 s: both are bounded by this data, not by independent evidence.
- The person memory also prolongs a *false* high-score spike by up to 0.3 s (a possible unnecessary STOP); the nominal data has no spike above 0.77, so this is untested until the perturbation trials (stage 5).
- Only 3 episodes; no unnecessary STOP was observed, which is not a rate.
- Tests: `q2_edge_tests.py` (baseline, 18 cases) and `q2_edge_tests_revised.py` (revised, 34 cases covering out-of-order/future/NaN messages, age and score boundaries, margin boundary, memory window, state isolation): all pass.
