"""
Q1 Stage 3 - repaired lane-centre detector.

FAILURE REPAIRED: when one boundary is hidden (shadow) or absent (missing paint) at the queried
row, the baseline placed it a fixed 250 px away. True lane width at v=170 is ~163 px, so the
centre was ~43.5 px off. Root cause = wrong geometry, not a weak threshold.

IDEA: the lane centre c(v) is a straight line in the image (max residual 1.1 px on clear
frames) and the lane width is a known function w(v) of the row (fixed camera, flat road). Every
paint component seen on ANY row gives a centre measurement: u + w(v)/2 (if it is a left
boundary) or u - w(v)/2 (if it is a right boundary). Fit one straight line c(v) to all rows
by exhaustive vote, then read it at v=260 and v=170. A boundary hidden at v=170 is bridged by
the rows where it is visible. Decoys (false seam, hot pixel) do not form a consistent pair
and have less support, so they lose the vote.

PRIORS (all stated, all can fail):
  P1 fixed camera / flat road: w(v)=k*v+b, calibrated label-free on the CLEAR images.
  P2 lane centre is a straight line in rows 95-319, |slope|<=0.10 (clear frames: -0.02..0.04).
  P3 ego vehicle is inside its lane: centre within CENTRE_RANGE at v=215. This is what stops
     "right paint = left boundary of the next lane" hypotheses. Sharp turns / lane changes
     will violate P2-P3 and give unknown or low confidence, not a confident answer.
  P4 paint is >=75 % of the frame's bright level (99.9th pct of the road region) and >=100
     grey, 2-10 px wide per row. Relative, so it survives exposure scaling (x0.7 tested).

Independent per frame; no temporal filtering; no reference labels are read here.
"""
import zipfile, cv2, numpy as np

V_MIN, V_MAX, V_REF = 95, 319, 215
SLOPES = np.linspace(-0.10, 0.10, 41)
CENTRES = np.arange(170.0, 310.5, 0.5)          # P3
TOL = 2.5                                         # px, vote tolerance
MIN_ROWS, CONF_MIN = 15, 0.25


def calibrate_width(zip_path):
    """w(v)=k*v+b from clear-sequence IMAGES only (two paint runs per row, thr 190)."""
    z = zipfile.ZipFile(zip_path); V, Wd = [], []
    for f in range(24):
        g = cv2.cvtColor(cv2.imdecode(np.frombuffer(z.read(f'city/lane/clear/{f:03d}.png'), np.uint8), 1), cv2.COLOR_BGR2GRAY)
        for v in range(100, 300, 5):
            runs = _runs(g[v] > 190)
            if len(runs) == 2: V.append(v); Wd.append(runs[1][2] - runs[0][2])
    k, b = np.polyfit(V, Wd, 1)
    return k, b


def _runs(mask):
    idx = np.flatnonzero(mask)
    if idx.size == 0: return []
    parts = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    return [(p[0], p[-1], (p[0] + p[-1]) / 2.0) for p in parts]


class LaneRepair:
    def __init__(self, k, b):
        self.k, self.b = float(k), float(b)
        self.w = lambda v: self.k * np.asarray(v, float) + self.b

    # ---- 1. paint components -> centre hypotheses ------------------------------------
    def _hypotheses(self, gray):
        region = gray[V_MIN:V_MAX + 1]
        T = max(100.0, 0.75 * np.percentile(region, 99.9))
        V, H, TY = [], [], []
        for v in range(V_MIN, V_MAX + 1):
            runs = [r for r in _runs(gray[v] >= T) if 2 <= r[1] - r[0] + 1 <= 10]
            if len(runs) > 6: continue                      # texture/noise row
            for _, _, u in runs:
                half = self.w(v) / 2
                V += [v, v]; H += [u + half, u - half]; TY += [0, 1]   # as-left, as-right
        return np.array(V), np.array(H), np.array(TY), T

    # ---- 2. exhaustive vote over (c0, slope) ---------------------------------------
    def _vote(self, V, H):
        P = (CENTRES[:, None, None] + SLOPES[None, :, None] * (V[None, None, :] - V_REF)).astype(np.float32)
        ok = np.abs(P - H[None, None, :].astype(np.float32)) < TOL
        return ok.sum(axis=2), ok                                    # (n_c0, n_slope), mask

    def detect_frame(self, img, v_near=260, v_far=170):
        if img.dtype != np.uint8 or img.ndim not in (2, 3) or img.shape[0] <= v_near:
            raise ValueError('need uint8 HxW or HxWx3 image with more than v_near rows')
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        V, H, TY, T = self._hypotheses(gray)
        out = {'u_near': None, 'u_far': None, 'confidence_near': 0.0, 'confidence_far': 0.0, 'n_rows': 0, 'raw_near': None, 'raw_far': None}
        if V.size < 2 * MIN_ROWS: return out
        S, OK = self._vote(V, H)
        ic, isl = np.unravel_index(np.argmax(S), S.shape)
        c0, s = CENTRES[ic], SLOPES[isl]
        for _ in range(3):                                   # refit on inliers
            pred = c0 + s * (V - V_REF); inl = np.abs(pred - H) < TOL
            if inl.sum() < 4 or np.ptp(V[inl]) < 20: return out
            s, c0 = np.polyfit(V[inl] - V_REF, H[inl], 1)
        pred = c0 + s * (V - V_REF); inl = np.abs(pred - H) < TOL
        rows = np.unique(V[inl]); rms = float(np.sqrt(np.mean((pred[inl] - H[inl]) ** 2)))
        out['n_rows'] = int(rows.size)
        if rows.size < MIN_ROWS: return out
        best = int(inl.sum())
        # rival explanations may only count hypotheses the best line does NOT already explain
        S_ind = (OK & ~inl[None, None, :]).sum(axis=2)
        two_sided = np.intersect1d(V[inl & (TY == 0)], V[inl & (TY == 1)]).size
        pair = 0.7 + 0.3 * min(1.0, two_sided / 20)   # rows with both boundaries are the only check on w(v)
        for name, v, ck in [('u_near', v_near, 'confidence_near'), ('u_far', v_far, 'confidence_far')]:
            centre = c0 + s * (v - V_REF)
            # runner-up explanation: any line whose centre at this row differs by >8 px
            P_eval = CENTRES[:, None] + SLOPES[None, :] * (v - V_REF)
            S2 = int(np.where(np.abs(P_eval - centre) > 8, S_ind, 0).max())
            d = float(np.min(np.abs(rows - v)))
            bracketed = rows.min() <= v <= rows.max()
            conf = (min(1.0, rows.size / 60)                       # how much of the road supports the fit
                    * np.exp(-d / 30) * (1.0 if bracketed else 0.6)  # how far this row is from evidence
                    * max(0.0, 1 - rms / 2.5)                        # how straight the evidence is
                    * (1 - min(1.0, S2 / best))                      # independent rival explanation
                    * pair)                                          # width prior verified by two-sided rows?
            out[ck] = float(conf); out['raw_' + name[2:]] = float(centre)
            out[name] = float(centre) if conf >= CONF_MIN else None
        return out
