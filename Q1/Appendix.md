# Appendix - Question 1

## 1. References
*(Keep only what you actually read; delete the rest before submitting.)*
- OpenCV documentation, "Changing Colorspaces" and "Canny Edge Detection" tutorials (assignment's suggested reading). Canny was read about but not used in the final method.
- Bosch Future Mobility Challenge track description (assignment's suggested reading; add the link from the assignment PDF).
- R. O. Duda and P. E. Hart, "Use of the Hough transformation to detect lines and curves in pictures", Communications of the ACM 15(1), 1972, pp. 11-15. Basis for voting over line parameters (here: centre offset and slope).
- M. A. Fischler and R. C. Bolles, "Random sample consensus: a paradigm for model fitting...", Communications of the ACM 24(6), 1981, pp. 381-395. Basis for scoring a model by its inliers (an exhaustive vote replaces random sampling).

## 2. Decision log
| decision | why |
|---|---|
| Baseline threshold 190 on gray | Paint peaks at 231 on every frame; the false seam peaks at 183. 190 is the smallest round number above the seam, which I only learned during the audit; it works by a 7-level margin, not robustly (threshold <=180 lets the seam win; >=235 returns nothing). |
| Keep the baseline's fixed 250 px width unchanged when I found it was wrong | The assignment asks for the *unchanged* baseline on 72 frames and a before/after comparison; fixing it silently would erase the comparison. The limitation is documented in the script. |
| Vote on the lane *centre* instead of fitting each boundary | Every paint run gives a centre hypothesis (u +/- w/2). A parallel decoy (the seam) cannot be rejected by slope, but it never forms a left/right pair and gets fewer votes. No left/right split at the image middle is needed. |
| Exhaustive (Hough-style) vote, not RANSAC | Deterministic, no random seed, small search space (281 offsets x 41 slopes). |
| Width model w(v)=1.054v-16.3 calibrated from CLEAR images only | Fixed camera and flat road make width a function of row; it uses no labels. Risk: calibration drift (limitation in the report). |
| Priors: slope <=0.10, centre in u=170-310 | Measured centre slope on clear frames is -0.02 to 0.04; the centre range stops "the right paint is the left boundary of the next lane" solutions. Both will fail on sharp turns or lane changes, by design they then give unknown or low confidence. |
| Relative paint threshold 0.75 x 99.9th percentile (floor 100) | Survives exposure scaling (x0.5-x1.3 tested); the floor makes a paint-free frame return unknown. Deliberately low enough to admit the seam, so that geometry (not a lucky threshold) rejects it. |
| Confidence as a product of five evidence terms | Any weak term should pull trust down. The rival term was changed after the first stress test showed the original version counted the same pixels as competing explanations (confidence never exceeded 0.6 even on clear frames); the two-sided-rows term was added because one-sided evidence depends entirely on the width prior. The constants (60 rows, 30 px, 2.5 px, 20 rows) were chosen by reasoning and were not fitted to the reference CSV. |
| Unknown threshold 0.25 | Conservative: in the stress tests withheld estimates had 0.2-0.7 px error, i.e. some good answers are discarded. |
| MAE on answered frames + unknown fraction, per sequence and row | Required by the assignment so refusing hard frames cannot look like accuracy. |
| No temporal filtering | Not needed to fix the observed failure and keeps each frame independent (causal by construction). Listed as unfinished. |

## 3. Failure log
**What went wrong during the work (found in an audit of Stages 1-2, see `notes/AUDIT_REPORT.md`):**
- My first written analysis of the frames (AI-generated) contained measurements that were wrong (boundary positions off by roughly 25-50 px), a self-contradictory width assumption ("constant 250 px" and "narrowing trapezoid"), and invented visual cues (road texture, glossy paint, a 120->80 luminance edge). The images are flat synthetic colours.
- I first blamed the far-row failures on the shadow "dimming" the paint and on the missing left line. The real cause was the fixed 250 px width at a row where the lane is 163 px wide; correcting only the width took the error from 25.85 / 43.62 px to 0.45 / 0.47 px.
- The hidden boundary actually alternates between left and right by frame and row in the shadow sequence, and in the missing sequence it is the *right* boundary that is absent at the far row.
- The first revision confidence barely separated clear from degraded frames and ignored whether the width prior was verified; fixed as described in the decision log.
- The provided frames are straight-line synthetic scenes, so near-perfect revision accuracy (<=0.4 px) says little about real footage.

**What did not work / remains open:**
- Sensitivity to the width model: 3 % error -> ~2-4 px errors and dropped trust; 6 % -> everything withheld (failure frame C).
- Curved roads, lane changes and ego vehicle off the lane centre violate the priors; untested because no such data exists here.
- Confidence cannot be validated against error on this data (revision errors never exceed 0.4 px).
- Abstention is conservative (withheld estimates were 0.2-0.7 px off).
- Further exploration (temporal filtering, segmentation, bird's-eye view from the calibration points) not attempted. Timing measured only on a sandbox CPU (~53 ms/frame), not on a Jetson.

**With another week:** add a width scale factor to the vote so the method self-calibrates against pitch changes; a quadratic centre model with a curvature prior; temporal smoothing using earlier frames; test on real BFMC footage and calibrate the confidence against measured error; use the calibration files for a bird's-eye view.

## 4. AI usage note
Claude (Anthropic) was used heavily on this question: to plan the stages, write and debug all code, run the measurements, generate figures and draft this report. I asked it to work in stages and not to move on until I said so. **My prompts in this working session were:**
1. "Goal: Build a very comprehensive solution to the problem statements given in the sedrica assigment pdf leaving as few logical gaps as possible. Workflow: We will tackle the perception section first and move to the motion planning section. Do not bother with the general questions. We will first complete the mandatory questions first of both the sections and then move to the optional questions, if time remains. Solve question in stages. First provide the outline of what you're going to do and then start with the first stage of work, explaining briefly but clearly the underlying assumptions and thought process. Do not move to the next stage of the solution until I explicitly tell you to so as to ensure my complete understanding of the solution."
2. "yes"  (start Stage 1)
3. "give solutions with explanations"
4. "yes"  (start Stage 2)
5. "where is whatever u've built"
6. "proof read every thing that we've done so far and ensure there are no errors or logical gaps also test for edge cases"
7. "Go"  (Stage 3)
8. "Go"  (Stage 4: report, README, appendix)

*(Add any prompts from other sessions. The earlier hand-annotation step of part (a) was done by the AI from measurements of the frames rather than by me sketching a hypothesis first; say so if that is how it went. The full transcript is available on request.)*
