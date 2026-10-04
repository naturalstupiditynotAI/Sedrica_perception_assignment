# Q2 Stage 2 - Baseline rule (part b)

## States (what each means for the car)
- **GO**: continue at current speed; no hazard evidence.
- **SLOW**: approach cautiously (reduce speed, be ready to brake) while evidence is unresolved or a hazard is possible but unconfirmed.
- **STOP**: brake to stand still before the stop line.

## Rule (`q2_rules.baseline`, stateless, message age ignored on purpose)
Thresholds fixed before any scoring and not changed afterwards: `T_RED = 0.5`, `T_PERSON = 0.5`, `T_PERSON_STOP = 0.9`. The scores are not calibrated, so 0.5 is read only as "more likely than not" and 0.9 as "almost certain". Priority order:
1. V2X red **and** camera red (`red_score >= 0.5`) -> **STOP**.
2. `person_score >= 0.9` -> **STOP** (position unknown, so a visible person is treated as possibly in the path).
3. Exactly one source says red -> **SLOW** (unresolved). A single noisy or old source never triggers STOP for the light.
4. `person_score >= 0.5` -> **SLOW**.
5. A camera score is missing/invalid -> **SLOW**.
6. Otherwise **GO**.
Missing or invalid inputs (NaN, None, outside [0,1], light other than red/green) are treated as "not available". `python q2_edge_tests.py`: 18 cases, all pass.

## Results (scored afterwards with `crossing_reference.csv`)
| episode | GO | SLOW | STOP | required STOP frames | missed STOP | unnecessary STOP | first required | first STOP |
|---|---|---|---|---|---|---|---|---|
| clear_green | 21 | 3 | 0 | 0 | 0 | 0 | - | - |
| late_red | 8 | 5 | 11 | 15 | 4 | 0 | f9 | f11 |
| person_crossing | 9 | 6 | 9 | 14 | 5 | 0 | f10 | f11 |

Figure: `figures/q2_baseline_timeline.png` (scores, V2X state with stale frames hatched, message age, decision, and a labelled eval-only band). Per-frame decisions and reasons: `baseline_decisions.csv`.

## What the baseline gets wrong (observed, not tuned away)
- **late_red f9-10:** V2X (fresh, age 0) already says red but `red_score` is 0.43 -> SLOW; STOP only at f11 (0.2 s after the lamp turned red).
- **late_red f12-13:** V2X says green again (sampled 0.6/0.7 s, before the change) while the camera says 0.91 / 0.99 -> SLOW instead of STOP. Reading the old message as current is the cause (part c).
- **person_crossing f15-16:** `person_score` drops to 0.29 while the person is still in the path -> **GO**. This is the most dangerous frame: a stateless rule has no memory that a person was seen a moment ago.
- **person_crossing f10, f22-23:** scores 0.85 / 0.79 / 0.81 fall just under 0.9 -> SLOW with the person in the path.
- **clear_green f6-7, f9:** `person_score` spikes (0.77, 0.77, 0.51) with no person in the image -> 3 needless SLOW frames (no false STOP at these thresholds; a larger spike would cause one).
- Person outside the road (f7-8, scores 0.82 / 0.78) correctly stays SLOW rather than STOP, but only because the scores happened to be below 0.9; the rule cannot actually tell outside from inside.
- With V2X missing, camera red alone can only reach SLOW, by design; to be tested under perturbation (stage 5).
