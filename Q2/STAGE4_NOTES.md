# Q2 Stage 4 - Is STOP timely? (part d)

d_stop = v*tau + v^2/(2a), tau = 0.15 s, a = 0.8 m/s^2. At the logged v = 0.8 m/s: d_stop = 0.12 + 0.40 = **0.52 m**. Comfortable stopping appears possible when `distance_to_line_m >= d_stop`; equivalently, the constant deceleration needed to stop exactly at the line after the 0.15 s delay, `a_required = v^2 / (2(distance - v*tau))`, is <= 0.8 m/s^2. The check is `q2_timeliness.check`; it uses no reference data. The log has the car at a constant 0.8 m/s throughout, so every number is "if STOP had been requested at that frame".

## First STOP request per episode
| episode | rule | first STOP | distance | d_stop | margin | comfortable? | extra delay the margin could absorb | a_required |
|---|---|---|---|---|---|---|---|---|
| clear_green | baseline | **no STOP request** | | | | | | |
| clear_green | revised | **no STOP request** | | | | | | |
| late_red | baseline | f11 (1.1 s) | 1.87 m | 0.52 m | 1.35 m | yes | 1.69 s | 0.18 m/s^2 |
| late_red | revised | f9 (0.9 s) | 2.03 m | 0.52 m | 1.51 m | yes | 1.89 s | 0.17 m/s^2 |
| person_crossing | baseline | f11 (1.1 s) | 1.87 m | 0.52 m | 1.35 m | yes | 1.69 s | 0.18 m/s^2 |
| person_crossing | revised | f11 (1.1 s) | 1.87 m | 0.52 m | 1.35 m | yes | 1.69 s | 0.18 m/s^2 |

## When SLOW came first: which evidence caused the change to STOP
- **late_red, baseline:** SLOW at f9-10 because V2X (fresh, age 0) said red but `red_score` was 0.43, under the 0.5 needed to count as camera red. STOP at f11 when `red_score` reached 0.99 and the two sources agreed. **Revised:** no SLOW before the STOP; at f9 it STOPs on the fresh V2X red because 0.43 does not clearly contradict it (a score under 0.2 would). The SLOW at f1 in both rules is an unrelated `person_score` spike (0.54).
- **person_crossing, both rules:** SLOW at f7-10 because `person_score` was 0.82, 0.78, 0.61, 0.85 (person probably visible, position unknown); STOP at f11 when it reached 0.99, above the 0.9 "almost certain" threshold. The person was outside the road at f7-8 and entered the path at f10, so the SLOW period covers one frame of real hazard (f10).
- **clear_green:** no STOP in either rule. Its 3 SLOW frames (f6-7, f9) come from `person_score` spikes (0.77, 0.77, 0.51) with no person in the image.

## Was it too late? (reference used only for this column)
| episode | rule | first required | delay | extra travel during the delay | share of the margin at the required frame |
|---|---|---|---|---|---|
| late_red | baseline | 0.9 s | 0.2 s | 0.16 m | 11 % of 1.51 m |
| late_red | revised | 0.9 s | 0.0 s | 0 m | 0 % |
| person_crossing | baseline / revised | 1.0 s | 0.1 s | 0.08 m | 6 % of 1.43 m |

**No STOP is too late by distance in this data**, and none could be: even at the last frame (2.3 s, 0.91 m) the margin is still 0.39 m, and extrapolating the logged speed the last comfortable STOP time is 2.79 s, after the window ends. So the failure shown here is a *response delay*, not a missed stopping point: the baseline spends up to 0.16 m (11 %) of its margin on waiting. The check will flag a genuinely late STOP when it exists (unit test: v = 1.5 m/s, 1.5 m away -> d_stop 1.63 m, not comfortable); with the 2.75 m approach at 0.8 m/s used here the margin is simply generous. Stage 5 applies the same check to the first STOP of every perturbed trial.

## Caveats
- d_stop uses the assignment's tau and a; real braking will differ. A SLOW period would lower speed (and d_stop), which the constant-speed log cannot show.
- "Comfortable" refers to 0.8 m/s^2; physically possible stopping is a weaker condition and is not assessed.

## Files
`q2_timeliness.py` (check), `q2_stage4.py` (run), `stopping_distance_check.csv`, `figures/q2_stopping_margin.png`, `q2_edge_tests_timeliness.py` (16 cases: boundary, too-late, v*tau > distance, standing car, past the line, NaN/None/negative/string inputs, no-STOP episodes; all pass).
