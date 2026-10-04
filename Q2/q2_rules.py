"""Q2 decision rules. Pure functions of the evidence available to the running car.
Nothing here reads crossing_reference.csv.

STATE MEANINGS
  GO    continue at the current speed: no hazard evidence.
  SLOW  approach cautiously (reduce speed, be ready to brake): evidence is unresolved or a hazard is possible but not confirmed.
  STOP  brake to stand still before the stop line.
"""
import math

# ---- BASELINE (Stage 2): supplied scores + V2X state; message age is deliberately ignored ----
T_RED = 0.5          # camera "says red" at or above this (scores are not probabilities; 0.5 = more likely than not)
T_PERSON = 0.5       # person "probably visible"
T_PERSON_STOP = 0.9  # person "almost certainly visible"; position unknown, so treated as possibly in the path

def _score(x):
    """valid score in [0,1] or None (missing / NaN / out of range / not numeric)"""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if (not math.isnan(x) and 0.0 <= x <= 1.0) else None

def _light(m):
    m = m.strip().lower() if isinstance(m, str) else None
    return m if m in ('red', 'green') else None

def baseline(red_score, person_score, v2x_light):
    """returns (decision, reason). Stateless; the V2X message is read as if it described the present moment."""
    r, p, m = _score(red_score), _score(person_score), _light(v2x_light)
    cam_red = r is not None and r >= T_RED
    v2x_red = m == 'red'
    if v2x_red and cam_red:
        return 'STOP', f'red: V2X red and camera red ({r:.3g}) agree'
    if p is not None and p >= T_PERSON_STOP:
        return 'STOP', f'person almost certainly visible ({p:.3g}), position unknown: treat as in path'
    if v2x_red != cam_red:
        if v2x_red:
            return 'SLOW', 'V2X says red but camera does not confirm' + ('' if r is None else f' ({r:.3g})')
        return 'SLOW', f'camera says red ({r:.3g}) but ' + ('V2X message missing' if m is None else 'V2X says green')
    if p is not None and p >= T_PERSON:
        return 'SLOW', f'person probably visible ({p:.3g}), position unknown'
    if r is None or p is None:
        return 'SLOW', 'camera score missing: cannot rule out a hazard'
    return 'GO', 'no red (camera and V2X) and no person evidence' if m is not None else 'camera: no red, no person; V2X missing'


# ================= REVISED RULE (Stage 3): stale V2X + camera/message disagreement =================
TAU, A_DECEL = 0.15, 0.8        # processing+actuation delay (s), comfortable braking (m/s^2), from the assignment
A_FRESH = 0.3          # s: a message older than this (twice the 0.15 s system delay) is not treated as describing "now"
T_CLEAR = 0.2          # camera "clearly sees no red" below this (fresh V2X red is only doubted when the camera is this sure)
T_RED_STRONG = 0.9     # camera alone may request STOP at or above this, only when V2X is old or missing
H_PERSON = 0.3        # s: a person almost certainly seen this recently is not assumed to have vanished (2x the 0.15 s system delay)
M_ESC = 0.5            # m: unresolved evidence may not be waited out once distance - d_stop falls below this (~0.6 s of travel at 0.8 m/s)

def d_stop(v):
    """approximate stopping distance v*tau + v^2/(2a)"""
    return v * TAU + v * v / (2 * A_DECEL)

def _num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None

class RevisedRule:
    """Stateful, causal (current + earlier frames only). Make a NEW instance per episode.
    V2X handling: keep the message with the LATEST sample time seen so far. A message sampled earlier than that
    (a repeated/delayed one) is superseded and ignored; the effective age is time_s - latest sample time.
    If nothing newer arrives, the effective age grows and the state becomes 'old' (see A_FRESH)."""
    def __init__(self, supersede=True, escalate=True, use_age=True, person_hold=True, h_person=None):
        # switches exist only for the ablation study (q2_stage3.py); defaults = the revised rule
        self.m = None; self.t = None; self.supersede, self.escalate, self.use_age = supersede, escalate, use_age
        self.person_hold, self.h_person, self.p_hi_t = person_hold, (H_PERSON if h_person is None else h_person), None

    def _update(self, time_s, m_new, t_new):
        m_new, t_new = _light(m_new), _num(t_new)
        if m_new is None or t_new is None or time_s is None or t_new > time_s + 1e-9:
            return                                   # no message, unreadable, or sampled "in the future" (clock error): ignore
        if self.t is None or t_new > self.t or not self.supersede:   # strictly newer information only
            self.m, self.t = m_new, t_new

    def step(self, time_s, speed_mps, distance_to_line_m, red_score, person_score, v2x_light, v2x_sample_time_s):
        time_s = _num(time_s)
        self._update(time_s, v2x_light, v2x_sample_time_s)
        r, p = _score(red_score), _score(person_score)
        age = None if (self.t is None or time_s is None) else round(time_s - self.t, 3)
        fresh = age is not None and age <= A_FRESH
        if not self.use_age and age is not None:      # ablation: read every message as describing the present
            age, fresh = 0.0, True
        v, d = _num(speed_mps), _num(distance_to_line_m)
        margin = None if (v is None or d is None or v < 0) else d - d_stop(v)
        info = dict(eff_state=self.m, eff_age=age, fresh=fresh, margin=None if margin is None else round(margin, 3))
        rs = 'n/a' if r is None else f'{r:.3g}'
        if p is not None and p >= T_PERSON_STOP:
            if time_s is not None: self.p_hi_t = time_s
            return 'STOP', f'person almost certainly visible ({p:.3g}), position unknown: treat as in path', info
        if self.person_hold and self.p_hi_t is not None and time_s is not None and 0 < time_s - self.p_hi_t <= self.h_person + 1e-9:
            ps = 'missing' if p is None else f'{p:.3g}'
            return 'STOP', f'person almost certainly seen {time_s - self.p_hi_t:.1f}s ago, score now {ps}: held, not released on a dropout', info
        unresolved = None
        if fresh and self.m == 'red':
            if r is None or r >= T_CLEAR:
                return 'STOP', f'fresh V2X red (age {age:.1f}s); camera ({rs}) does not contradict it', info
            unresolved = f'fresh V2X red but camera clearly sees no red ({rs})'
        elif fresh and self.m == 'green':
            if r is not None and r >= T_RED:
                unresolved = f'camera red ({rs}) vs fresh V2X green: two current sources disagree'
        else:                                         # old or no V2X: it cannot confirm or deny the present
            why = 'V2X missing' if self.m is None else f'last V2X ({self.m}) is {age:.1f}s old'
            if r is not None and r >= T_RED_STRONG:
                return 'STOP', f'camera strongly red ({rs}); {why}', info
            if r is not None and r >= T_RED:
                unresolved = f'camera red ({rs}) is the only current source; {why}'
            elif self.m == 'red':
                unresolved = f'last V2X was red {age:.1f}s ago and camera shows no red ({rs}): cannot confirm green'
        if unresolved is None:
            if p is not None and p >= T_PERSON:
                unresolved = f'person probably visible ({p:.3g}), position unknown'
            elif r is None or p is None:
                unresolved = 'camera score missing: cannot rule out a hazard'
        if unresolved is None:
            src = 'V2X unavailable' if self.m is None else (f'V2X {self.m}, age {age:.1f}s' + ('' if fresh else ' (old)'))
            return 'GO', f'no red, no person evidence ({src})', info
        if self.escalate and margin is not None and margin < M_ESC:
            return 'STOP', f'{unresolved}; stopping margin {margin:.2f} m < {M_ESC} m: cannot wait for resolution', info
        return 'SLOW', unresolved, info
