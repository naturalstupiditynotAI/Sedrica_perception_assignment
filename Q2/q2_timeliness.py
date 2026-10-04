"""Q2 part (d): is a STOP request timely?  d_stop = v*tau + v^2/(2a), tau = 0.15 s, a = 0.8 m/s^2 (assignment values).
Comfortable stopping appears possible when distance_to_line_m >= d_stop. Uses no reference data."""
import math
from q2_rules import TAU, A_DECEL, d_stop, _num

def check(speed_mps, distance_m):
    """Timeliness of a STOP requested NOW at this speed and distance. Returns a dict; 'comfortable' is None if it cannot be assessed.
      margin_m      distance - d_stop            (>= 0 means comfortable braking at 0.8 m/s^2 still reaches the line)
      budget_s      margin / v                   (how much more decision delay could be tolerated at constant speed)
      a_required    v^2 / (2*(distance - v*tau)) (constant deceleration that would just stop at the line after the delay;
                                                  inf if the car cannot stop before the line even with the delay alone)"""
    v, d = _num(speed_mps), _num(distance_m)
    if v is None or d is None or v < 0:
        return dict(comfortable=None, d_stop=None, margin_m=None, budget_s=None, a_required=None, note='speed/distance invalid or missing')
    ds = d_stop(v); margin = d - ds
    if d < 0:
        return dict(comfortable=False, d_stop=ds, margin_m=margin, budget_s=0.0, a_required=math.inf, note='car is already past the line')
    avail = d - v * TAU
    a_req = 0.0 if v == 0 else (math.inf if avail <= 0 else v * v / (2 * avail))
    return dict(comfortable=margin >= 0, d_stop=ds, margin_m=margin, budget_s=(math.inf if v == 0 else max(0.0, margin / v)), a_required=a_req, note='')

def first_stop(df, decision_col):
    """first row (by frame) of one episode whose decision is STOP, or None"""
    x = df.sort_values('frame'); s = x[x[decision_col] == 'STOP']
    return None if s.empty else s.iloc[0]
