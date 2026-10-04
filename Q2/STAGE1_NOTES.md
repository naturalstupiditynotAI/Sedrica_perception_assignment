# Q2 Stage 1 - Map what the car knows (part a)

Measured from the images and `crossing_evidence.csv`; `crossing_reference.csv` not read.

## What is in the data
- Every episode: 24 frames, 0.1 s apart, speed 0.8 m/s constant, distance to line 2.75 -> 0.91 m. The car is approaching, so road lines and crosswalk move between frames (frame differencing against frame 0 mostly measures ego-motion).
- Message age (time_s - v2x_sample_time_s) is 0 except frames 5-6, 12-13, 19-20 in every episode, where it is 0.5-0.6 s: the message is repeated from an older sample.
- Lamp (colour pixels in the image): `late_red` turns red at frame 9 (221 red px from then on, 0 before). `clear_green` and `person_crossing` stay green on all 24 frames.
- Person (`person_crossing`): visible frames 7-23, foot row fixed at v=238, moves left 10 px/frame (u=392 -> 232). Road edges at that row: u~132-136 and ~369-371. So the person is OUTSIDE the road in frames 7-8, on the edge at frame 9, INSIDE from frame 10.

## Direct vs uncertain
| quantity | status | evidence |
|---|---|---|
| time_s, speed_mps, distance_to_line_m | direct (treated as exact) | used for d_stop = v*tau + v^2/(2a) = 0.8*0.15 + 0.64/1.6 = 0.52 m |
| message age | exact arithmetic | |
| v2x_light | true only as of its sample time | `late_red` f12-13: says GREEN but was sampled at 0.6/0.7 s, before the lamp turned red (0.9 s); fresh messages at f9-11 had already said RED |
| red_score | uncertain, lags and is noisy | `late_red` f9-10: lamp already red in the image, score only 0.43 |
| person_score | uncertain, both ways | `clear_green` f6-7: 0.77 with no person in the image; `person_crossing` f15-16: 0.29 with the person in the path |

## Why a visible person need not mean STOP
`person_score` says "a person is visible", not "a person is in the car's path". In `person_crossing` f7-8 the person is on the sidewalk at u~380-390, beyond the right road edge (~369): a high score (0.8) with no conflict with the car's path. The path test needs the person's foot position against the road edges at that row; this is the Q1 idea (white boundary lines found on a row) reused. It is a refinement; the baseline uses the supplied scores only.

## Deliverables
`figures/q2_annotated_frames.png` (one frame per episode + a second person frame), `figures/q2_signal_flow.png`, `q2_stage1.py`.
Note: the person mask in `q2_stage1.py` subtracts the same frame of `clear_green`, which only an offline inspection can do; it is a measurement aid, not part of the decision system.

## Plan for the remaining stages
2. (b) Baseline rule on supplied scores + V2X; define GO/SLOW/STOP; thresholds; timelines.
3. (c) Message age, find the misleading frame, revised rule, what the car does while unresolved; both timelines.
4. (d) Stopping-distance check at the first STOP in each episode.
5. (e) >=20 seeded perturbation trials, baseline vs revision, missed/unnecessary STOP frames, response delays, false-alarm and dangerous-delay frames.
6. Report, README, appendix; optional person-position / belief-filter extension.
