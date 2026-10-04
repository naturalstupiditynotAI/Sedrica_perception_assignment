# Perception Q1 - The road disappears

All numbers below are produced by the code in this folder (`python lane_baseline.py`, `run_repair.py`, `make_figures.py`). Reference labels are read only after all predictions exist. Coordinates: 480x320 px, origin top-left, u right, v down; rows v_n=260 and v_f=170.

## (a) Look before coding
Figure: `figures/annotated_frames.png` (clear f12, shadow f06, missing f12). Solid green = boundary seen at that row, hollow orange = hidden boundary placed by my hypothesis, cyan star = lane centre I would want the car to follow, red x = decoy.

**Hypothesis and evidence for hidden boundaries.** (1) Lane boundaries are straight, so a hidden stretch continues the visible stretches above and below it (in shadow f06 the left paint is visible on rows 90-137 and 233-317 but not in between). (2) Lane width is a fixed function of the row. Measured on the clear frames: w(v)=1.054*v-16.3 (257.7 px at v=260, 162.9 px at v=170, residual <0.2 px), so one visible boundary plus w(v) places the other.

**What fools a white-pixel threshold.** (i) The dark shadow polygon (grey ~52 against road ~93) hides paint and its border is a strong 93->52 step. (ii) A false seam: a bright diagonal line inside the road (grey 183, rows 105-192, u~190-202 at v=170). It is exactly parallel to the left boundary, 33 px inside it, so slope cannot separate it from a real boundary.

*Note on provenance:* these annotations were generated from measurements of the frames with AI assistance, not hand-drawn before looking at the data (see appendix, AI usage).

## (b) Baseline (`lane_baseline.py`)
- Region: two full-width pixel rows, v=260 and v=170. No 2-D ROI, no line fit, no temporal information.
- Cue: grayscale > 190 (paint peaks at 231). Brightest white run in the left half (u<240) = left boundary, brightest in the right half = right boundary.
- Assumption: if only one boundary is found, the other is placed 250 px away (wrong by design at the far row; see (c)). Unknown only if no white pixel is found on the row.
- Confidence: mean(I_left, I_right)/500, times 0.7 if one boundary was inferred.
- Run unchanged on all 72 frames -> `baseline_results.csv`.

## (c) Interrogating the evidence
Figures: `figures/fig_c_evidence_baseline.png` (stages 1-4: original + ROI, ROI strips, gray-level profile with the threshold, result) and `figures/fig_c_evidence_revision.png`, each with a clear frame (f12) above a difficult frame (missing f06).

- **Clear f12, v=170:** exactly two paint runs exceed the threshold, u=169.5 and u=332.5 (I=231). They persuade the method, correctly; centre 251 (reference 251).
- **Difficult f06, v=170:** no pixel exceeds 190. The left paint sits inside the shadow (u~115-200, grey 52), the right paint is absent, and the only bright structure is the seam at u=195.5 with I=183, 7 grey levels below the threshold. The baseline returns *unknown*. With the threshold at 180 the seam is accepted as the left boundary (failure B below). The baseline's far-row answer was therefore right by margin, not by design.
- **Why grayscale + threshold:** paint vs road vs off-road vs shadow are separated by luminance alone here (231 / 93 / 65 / 52), so no colour-space change or edge operator was used; the price is that the threshold cannot tell the seam (183) or a dimmed line from a shadow edge without further evidence.
- **Root cause of the large baseline errors:** not the threshold. When one boundary is missing the fixed 250 px width is used at the far row, where the true width is 163 px, giving a (250-163)/2 = 43.5 px centre error. Swapping in the measured widths alone brings far-row error to 0.45 px (shadow) and 0.47 px (missing).

## (d) Repair (`lane_repair.py`)
**Failure repaired:** a hidden or absent boundary at the queried row (shadow, missing paint), together with the decoy seam.

**Cue and justification.** Every paint run on every row 95-319 is a centre measurement: u+w(v)/2 if it is a left boundary, u-w(v)/2 if it is a right boundary. One straight centre line c(v) (|slope|<=0.1, centre within u=170-310) is fitted by exhaustive vote over (offset, slope) in 0.5 px x 0.005 steps, then read at v=260 and v=170. A boundary hidden at v=170 is bridged by the rows where it is visible. The decoy loses because its hypotheses form a separate cluster (u~278, see `fig_c_evidence_revision.png`) with less support and no left/right partner. The width model is calibrated from the clear images only. Paint = gray >= 0.75 x (99.9th percentile of the road region), >= 100, 2-10 px wide per row. Uses only the current frame, so it is causal; it takes ~53 ms/frame in numpy on my sandbox CPU (Jetson not measured).

**Confidence rule** (a ranking of trust, not a probability). conf = coverage x proximity x straightness x rival x pairing, unknown if conf < 0.25 or fewer than 15 supporting rows:
| term | formula | lowers confidence when |
|---|---|---|
| coverage | min(1, supporting rows / 60) | little of the road supports the fit |
| proximity | exp(-d/30), x0.6 if extrapolating | the queried row is far from any supporting row (d in px) |
| straightness | max(0, 1 - rms/2.5) | the supporting points are not collinear |
| rival | 1 - min(1, S2/S1) | an independent explanation (e.g. seam) with S2 votes competes with the best (S1 votes) |
| pairing | 0.7 + 0.3 x min(1, two-sided rows/20) | no row shows both boundaries, so the width prior is unverified |

Observed values: clear sequence 0.83-0.85; shadow sequence 0.79-0.85 (both boundaries still supported on most rows); missing sequence 0.49-0.64 (lowest during the shadow band, frames 3-11); one boundary erased everywhere 0.58; decoy brightened to paint level 0.44-0.57.

**Near/far disagreement.** Example, unchanged baseline on shadow f06: near centre 248 (conf 0.86, correct) but far centre 204 (conf 0.31, true 248). A controller reading these numbers would conclude that the lane bends ~44 px to the left within the look-ahead and steer left, although the road is straight. The baseline's confidence exposes this: the far row had to *invent* a boundary and is scored 0.31 against 0.86. In the revision, both rows come from one fitted line, so the two centres cannot disagree geometrically; a row that lacks evidence instead loses confidence through `proximity` (and is withheld if it falls below 0.25), e.g. when both boundaries are erased on rows 95-200 the near row is answered and the far row withheld.

**What it fixed:** the fixed-width fallback (43-45 px far-row errors), the unknown frames on the missing sequence, and exposure to a bright decoy; see the table in (e).

## (e) Measured change
MAE is over frames where a coordinate was returned; unknown % is reported beside it (24 frames per sequence and row).

| sequence   | row          |   baseline MAE (px) |   baseline unknown (%) |   baseline n/24 |   revision MAE (px) |   revision unknown (%) |   revision n/24 |
|:-----------|:-------------|--------------------:|-----------------------:|----------------:|--------------------:|-----------------------:|----------------:|
| clear      | near (v=260) |                0.13 |                    0   |              24 |                0.22 |                      0 |              24 |
| clear      | far (v=170)  |                0.2  |                    0   |              24 |                0.25 |                      0 |              24 |
| shadow     | near (v=260) |                1.07 |                    0   |              24 |                0.23 |                      0 |              24 |
| shadow     | far (v=170)  |               25.85 |                    0   |              24 |                0.25 |                      0 |              24 |
| missing    | near (v=260) |                0.97 |                    0   |              24 |                0.22 |                      0 |              24 |
| missing    | far (v=170)  |               43.62 |                   37.5 |              15 |                0.25 |                      0 |              24 |

Worst single error over all 72 frames and both rows: baseline 45.2 px, revision 0.4 px. On clear frames the revision is ~0.1 px *worse* (line fit versus a single-row midpoint).

Plot through the missing-line sequence: `figures/fig_e_missing_sequence.png` (estimate vs reference for u_n and u_f, confidence underneath). Baseline and revision confidences are not comparable with each other: each ranks trust within its own method (a revision confidence of ~0.6 is not "less sure" than a baseline confidence of 0.92).

**Failure frames** (`figures/fig_e_failures.png`):
- **A - baseline, shadow f06 (near plausible, far wrong).** Left paint is hidden by the shadow at v=170, only the right line (u=329.5) is found, and the code places the left boundary 250 px away: far centre 204 instead of 248. The near row had both lines, so the two rows disagree and confidence reads 0.86 vs 0.31.
- **B - a plausible bright line was wrong (baseline with threshold lowered to 180, missing f11).** The shadow hides the real left paint, so the seam (I=183, u~200) is the only left-half candidate. It passes the lowered threshold, the code takes it as the left boundary and places the right one 250 px beyond: far centre 325 vs true 251 (74 px error), confidence 0.26. The revision on the same frame returns near 252.2 / far 250.3 (errors 0.2 / 0.3 px) because the seam's hypotheses do not agree with the many rows of paint that do.
- **C - the revision's own failure (width model 3 % too small, shadow f06).** Left- and right-paint hypotheses no longer coincide (each is off by ~1.5 % of w), the fit follows one boundary only: near 252 (true 248, 3.6 px off), far 250 (1.8 px off), confidence drops from 0.84 to 0.40-0.46. At 6 % all answers are withheld. Camera pitch changes on bumps would cause this.

## Limits
Width prior is the weak point (above); straight-centre and ego-in-lane priors are untested on curves (no curved data); the stress tests in `repair_stress_tests.py` are perturbations of these synthetic frames, not real footage; confidence has not been validated against error because revision errors never exceed 0.4 px on this data. Further exploration (temporal filtering, segmentation, bird's-eye view) was not attempted.
