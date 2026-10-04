Q1 STAGE 2 - BASELINE (corrected after audit; supersedes the earlier version)
=============================================================================
Method (lane_baseline.py): grayscale > 190 on two full-width rows (v=260, v=170); brightest
component in each image half = that boundary; centre = midpoint. If only one boundary is
found, the other is placed ROAD_WIDTH=250 px away. "Unknown" only if no white pixel at all.
No 2-D ROI, no line fit, no temporal use.

RESULTS (72 frames, MAE in px over frames with a prediction | unknown rate)
                near v=260           far v=170
  clear         0.13 | 0%            0.20 | 0%
  shadow        1.07 | 0%           25.85 | 0%
  missing       0.97 | 0%           43.62 | 37.5% (9/24 frames)

WHAT THE DATA ACTUALLY CONTAINS (measured)
  * Lane width is a straight-line function of row: w(v)=1.054*v-16.3 (max residual 0.17 px,
    identical across all 24 clear frames): 257.7 px at v=260, 162.9 px at v=170.
  * SHADOW: a dark polygon (grey ~52) fully HIDES one boundary. Which side/row changes over
    time: far row left hidden frames 2-12, right hidden frames 21-23; near row left hidden
    frames 0-3, right hidden 22-23. The paint is not "dimmed" (one frame at 181 is the exception).
  * MISSING: the far-row RIGHT boundary is absent in all 24 frames. A diagonal false seam
    (grey 183, u~190-202 at v=170) lies inside the road. The shadow polygon also appears, hiding
    the far-row left boundary in frames 3-11.

ROOT CAUSE OF EVERY LARGE ERROR: the fixed 250 px width used at the far row.
  With one boundary visible, centre = boundary +/- 125 instead of +/- 81.5, so the error is
  (250-162.9)/2 = 43.5 px whatever the cause of the missing boundary. This matches the observed
  43-45 px errors. Diagnostic counterfactual (NOT the Stage 3 repair): swapping in the measured
  per-row widths gives shadow far 0.45 px, missing far 0.47 px, near 0.22 / 0.17 px, same
  unknown counts. Near row is not "fine": its one-sided frames carry a ~3.9 px error from the same bug.

FRAGILITY OF THE 190 THRESHOLD
  The false seam is 183, 7 grey levels under the threshold. At threshold <=180 the seam is
  accepted as the left boundary and missing-far MAE rises to 54.6 px (max 74 px) with 0 unknowns.
  At >=235 all frames are unknown (paint peaks at 231). The baseline avoided the decoy by margin, not by design.

CONFIDENCE (baseline): mean(left,right intensity)/500, x0.7 if one boundary. It separates
  two-sided (0.91) from one-sided (0.32) frames but measures paint brightness only, so it
  cannot expose near/far disagreement; 34/72 frames have identical near and far confidence.

EDGE CASES: see edge_case_tests.py. Fails (kept in baseline on purpose): hot pixel and brighter
  seam win the "brightest" rule at conf 0.96-0.97; both lines in one half; 0.7x exposure -> all unknown.
