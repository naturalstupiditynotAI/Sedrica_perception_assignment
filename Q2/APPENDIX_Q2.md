# Appendix - Question 2

## 1. References
*(Keep only what you actually read; delete the rest before submitting.)*
- Bosch Future Mobility Challenge track and V2X rules on crossings and smart lights (assignment's suggested reading; add the link from the assignment PDF).
- OpenCV background-subtraction tutorial (assignment's suggested reading). Used only as an *offline measurement aid*: the person mask in `q2_stage1.py` subtracts the same frame of the `clear_green` episode. No decision rule uses a motion cue.
- No other external source was used for the decision rules; the stopping-distance formula is the one given in the assignment.

## 2. Decision log
| decision | why |
|---|---|
| States: GO / SLOW / STOP with SLOW meaning "approach cautiously while evidence is unresolved" | Gives the car something safe to do between "nothing wrong" and "brake now"; unresolved conflict maps to SLOW, not a coin flip. |
| Thresholds 0.5 / 0.5 / 0.9, fixed before scoring | Scores are not probabilities, so 0.5 is only "more likely than not" and 0.9 "almost certain"; they were not tuned on the reference. |
| Baseline needs two sources (V2X red + camera red) to STOP for the light | A single noisy score (spikes up to 0.38 under a green lamp) or an old message should not stop the car; cost: slower response when the camera lags (f9-10). |
| `person_score >= 0.9` -> STOP although position is unknown | Without the person's position the safe reading of "almost certainly there" is "possibly in the path"; this is the main source of false STOPs under noise. |
| Revised rule keeps the V2X message with the *newest sample time* and ignores older repeats | A message sampled before one already received cannot describe the present better; this uses only earlier frames (causal) and fixes f12-13 without a threshold. |
| Age gate 0.3 s (twice tau = 0.15 s) | The message should be no older than about the system's own delay; on the given data every effective age is <= 0.2 s so the choice is untested there. It only matters when the channel goes silent. |
| Fresh V2X red wins unless camera < 0.2 (`T_CLEAR`) | A weak score (0.43) should not veto a current infrastructure message; 0.2 is "camera clearly sees no red". Any value below 0.43 gives the same nominal result, so it is bounded by this data, not independently justified. |
| Camera alone may STOP only at >= 0.9 and only when V2X is old or missing | Keeps "one source never stops the car" except when it is the only source and very sure; costs 6 false-STOP frames at level B. |
| Person memory 0.3 s | After you were almost certain a person was there, a 0.1-0.2 s score dropout is not evidence they left (twice tau). The dropout in this data lasts 0.2 s, so the window is bounded below by the data. Chosen after the user asked for a short memory; its false-STOP cost was only measured in stage 5. |
| Margin escalation at `distance - d_stop < 0.5 m` | Unresolved evidence cannot be waited out forever; 0.5 m is about 0.6 s of travel. On the nominal data it changes nothing once the memory exists; it adds 59 false STOP frames per 200 level-A trials. |
| Stage 3 scope: first stale V2X only, then add the person memory | Isolating the age handling first made the ablation possible; the memory was added when asked and ablated separately. |
| Perturbation protocol: one perturbed copy per trial shared by all rules, two levels, 200 trials, seed 2026 | A fair paired comparison; the level B stress shows how the ranking holds up. 200 trials make the means stable; the first 20 are tabulated as required. |
| Missed STOP counts SLOW and GO alike; delay measured from the first required frame to the first STOP at or after it | Strict reading of the assignment's "missed-STOP frames"; an earlier false STOP is counted as unnecessary, not as a negative delay. |
| No retuning after the trials; two fixes only listed | Retuning on the same trials would make the comparison optimistic. |
| Scores treated as scores, not probabilities | A reliability check on 72 frames showed `person_score` 0.5-0.9 means "person on the crossing" in 3 of 10 frames. |

## 3. Failure log
**What went wrong during the work (all caught before submission):**
- The first annotated figure drew the person box around the *lamp* on the late_red frame because the person mask subtracted `clear_green`, where the lamp differs; fixed by restricting the mask to the person episode.
- Label columns in the reference file are integers, not booleans; the first scoring run crashed on `x[x.stop_required]`. Fixed.
- A reason string displayed 0.499 as "0.50" and described a *missing* V2X message as "V2X does not say red"; fixed after the edge-case tests exposed it.
- My own output filter once hid the indented table rows of a result; found when the printed table looked empty and re-run with a safe marker.
- Two statements in the stage-5 notes were wrong on re-check (the denominator "1,200" should be 800; a cause given for the remaining misses had not been analysed) and one glossed over 6 level-B false STOPs; corrected before packaging.

**What did not work or remains open:**
- The person memory trades fewer missed STOPs for more false ones: unnecessary STOP frames per clear_green trial rise from 0.38 to 1.70 (level A); 334 of the revision's 570 unnecessary frames come from the 0.3 s hold.
- The nominal data never reaches the too-late zone (margin 0.39 m at the last frame), so part (d) cannot show a failure; I could only unit-test the check.
- `T_CLEAR` and the memory window are bounded by this data (0.43 weak score, 0.2 s dropout), not by independent evidence.
- About 1.1 required frames per trial are still missed at level A (3.8 and 1.9 at level B); not broken down by cause.
- The perturbations model sensor trouble; they are not real V2X latency or camera failure, and every trial starts from the same 72 frames.
- Not attempted: measuring the pedestrian's position and using the Q1 road region, and a belief filter for the light state (the assignment's optional further exploration), to save time for the mandatory Motion Planning question.

**With another week:** build the person-in-path flag (foot position against the Q1 road edges) and replace the "0.9 means possibly in the path" rule; arm the person memory only after two consecutive scores >= 0.9 and skip the escalation when a fresh V2X green is present and only a camera frame is missing; a hazard-rate belief filter for the light with the V2X age as its observation noise; calibrate the scores on more footage; test with measured V2X latency.

## 4. AI usage note
Claude (Anthropic) was used heavily on this question: to plan the stages, write and debug all code and tests, run the measurements, generate the figures and draft the report. I asked it to work in stages and wait for my go-ahead. **My prompts for Question 2 in this working session:**
1. "Go. Also you don't need to use the context of 1 in 2 completely, so don't keep going over the files that were produced in Q1."  (start Q2; Stage 1 delivered)
2. "Go"  (Stage 2: baseline)
3. "Go"  (Stage 3: stale V2X)
4. "use the short memory and answer"  (add the person-score memory and deliver Stage 3)
5. "go"  (Stage 4: stopping distance)
6. "go"  (Stage 5: uncertainty trials)
7. "Go"  (Stage 6: this report, README and appendix)
The initial planning prompt of this working session is the one quoted in `Q1/APPENDIX_Q1.md`.
*(Add any prompts from other sessions. As in Q1, the annotated frames and measurements in part (a) were produced by the AI from the images, not hand-drawn by me beforehand; say so if that is how it went. The full transcript is available on request.)*
