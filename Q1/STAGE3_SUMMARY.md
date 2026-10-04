# Q1 Stage 3 - Repair (lane_repair.py)

**Failure repaired:** one boundary hidden/absent at the queried row → baseline placed it a fixed 250 px away; true width at v=170 is ~163 px → ~43.5 px centre error.

**Method:** every paint run on rows 95-319 is a centre measurement (`u ± w(v)/2`); one straight centre line `c(v)` is fitted by exhaustive (offset, slope) vote and read at v=260 and v=170. A boundary hidden at v=170 is bridged from rows where it is visible. Decoys (parallel false seam, hot pixels) fail because they never form a left/right pair and have less support. Width model `w(v)=1.0538·v−16.17` is calibrated from the CLEAR images only (no reference CSV).

**Priors (stated, can fail):** fixed camera/flat road (width model); straight centre, |slope|≤0.10; ego vehicle inside lane (centre within 170-310 px); paint ≥75 % of the frame's bright level, 2-10 px wide.

## Before / after (72 frames, MAE px | unknown %)
| seq | base near | base far | repaired near | repaired far |
|---|---|---|---|---|
| clear | 0.13 \| 0 | 0.20 \| 0 | 0.22 \| 0 | 0.25 \| 0 |
| shadow | 1.07 \| 0 | 25.85 \| 0 | 0.23 \| 0 | 0.25 \| 0 |
| missing | 0.97 \| 0 | 43.62 \| 37.5 | 0.22 \| 0 | 0.25 \| 0 |
Worst single error: baseline 45.2 px → repaired 0.4 px. Clear got ~0.1 px worse (line fit vs single-row midpoint).

## Confidence (evidence support, not a calibrated error probability)
`support rows × distance-to-evidence (×0.6 if extrapolating) × straightness × (1 − independent rival) × two-sided-rows factor`; unknown below 0.25.
Clear 0.84 · one boundary erased 0.58 · decoy at paint brightness 0.57 · rows outside the evidence → withheld.

## Stress results (repair_stress_tests.py, repair_edge_cases.py)
Held (≤0.4 px): either boundary erased everywhere, noise σ≤30, salt noise, exposure ×0.5-1.3, seam boosted to paint brightness, brighter decoy on synthetic road, hot pixels, flip. Correct unknown: blank/white image, road-as-paint (×2.2 exposure), no geometry, ego far off-lane, evidence only in top 35 rows.

## Limitations (honest)
1. **Width prior is the weak point:** width model off by 3 % → ~1.9 px errors and 50 % unknown; ≥6 % → all unknown. Camera pitch change on bumps would do this.
2. **Straight-centre prior untested on curves:** no curved data exists here; expect unknown/low confidence, not validated.
3. **Abstention is conservative:** withheld estimates in the erased-band tests had 0.2-0.7 px error.
4. **Confidence cannot be validated against error here:** errors never exceed 0.4 px, so it only reflects evidence, not proven error prediction.
5. Frames are synthetic straight lines; real footage will be worse. No temporal filter. 53 ms/frame in numpy on this sandbox (Jetson untested).
6. Width model calibrated on the same dataset's clear frames (label-free, but same camera).
