"""Edge cases for q2_rules.RevisedRule (stateful: sequences of frames)."""
import math
import q2_rules as Q
nan = float('nan'); FAR = 3.0   # large distance so the margin escalation stays out of the way unless tested
bad = 0
def run(name, frames, expect, **kw):
    """frames: list of dicts (time_s, red, person, m, ts, [dist], [speed]); checks the decision on the LAST frame"""
    global bad
    rule = Q.RevisedRule(**kw); out = None
    for f in frames:
        out = rule.step(f['t'], f.get('v', 0.8), f.get('d', FAR), f.get('r', 0.0), f.get('p', 0.0), f.get('m', 'green'), f.get('ts', f['t']))
    ok = out[0] == expect; bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name:62s} -> {out[0]:4s} | {out[1][:78]}")
    return out
F = lambda t, **k: dict(t=t, **k)
# ---- V2X ordering / validity ----
run("out-of-order green after fresh red is superseded", [F(1.1, m='red', r=0.9), F(1.2, m='green', ts=0.6, r=0.91)], 'STOP')
o = run("repeat with same sample time does not refresh age", [F(1.1, m='red', r=0.9), F(1.2, m='red', ts=1.1, r=0.9)], 'STOP'); assert o[2]['eff_age'] == 0.1
o = run("sample time in the future is ignored (clock error)", [F(1.0, m='red', ts=2.0, r=0.0)], 'GO'); assert o[2]['eff_state'] is None
o = run("NaN sample time ignored", [F(1.0, m='red', ts=nan, r=0.0)], 'GO'); assert o[2]['eff_state'] is None
o = run("unknown light string ignored", [F(1.0, m='yellow', r=0.0)], 'GO'); assert o[2]['eff_state'] is None
o = run("message None ignored", [F(1.0, m=None, r=0.0)], 'GO')
run("NaN time_s: no crash, V2X treated as missing", [F(nan, m='green', r=0.0)], 'GO')
# ---- age threshold ----
o = run("channel silent, age exactly 0.3 s -> still fresh", [F(0.0, m='green'), F(0.3, m=None, r=0.0)], 'GO'); assert o[2]['fresh']
o = run("channel silent, age 0.4 s -> old, last state green", [F(0.0, m='green'), F(0.4, m=None, r=0.0)], 'GO'); assert not o[2]['fresh']
run("old GREEN message cannot veto a camera red 0.95", [F(0.0, m='green'), F(0.4, m=None, r=0.95)], 'STOP')
run("old RED message + camera shows no red: cannot confirm green -> SLOW", [F(0.0, m='red', r=0.9), F(0.5, m=None, r=0.0)], 'SLOW')
# ---- fresh red / camera ----
run("fresh red + camera exactly 0.2 (T_CLEAR) -> STOP", [F(1.0, m='red', r=0.2)], 'STOP')
run("fresh red + camera 0.19 clearly no red -> SLOW (unresolved)", [F(1.0, m='red', r=0.19)], 'SLOW')
run("fresh red + camera score missing -> STOP", [F(1.0, m='red', r=None)], 'STOP')
run("fresh green + camera 0.5 -> SLOW (two current sources disagree)", [F(1.0, m='green', r=0.5)], 'SLOW')
run("fresh green + camera 0.49 -> GO", [F(1.0, m='green', r=0.49)], 'GO')
run("no V2X, camera 0.9 -> STOP", [F(1.0, m=None, r=0.9)], 'STOP')
run("no V2X, camera 0.89 -> SLOW (single source)", [F(1.0, m=None, r=0.89)], 'SLOW')
# ---- margin escalation (v=0.8: d_stop = 0.52 m) ----
run("unresolved, margin exactly 0.5 -> SLOW", [F(1.0, p=0.6, d=1.02)], 'SLOW')
run("unresolved, margin 0.49 -> STOP", [F(1.0, p=0.6, d=1.01)], 'STOP')
run("unresolved, margin check disabled (ablation switch)", [F(1.0, p=0.6, d=0.6)], 'SLOW', escalate=False)
run("speed 0: d_stop = 0, margin 0.4 < 0.5 -> STOP", [F(1.0, p=0.6, d=0.4, v=0.0)], 'STOP')
run("negative speed invalid -> no margin -> stays SLOW", [F(1.0, p=0.6, d=0.1, v=-1.0)], 'SLOW')
run("distance NaN -> no margin -> stays SLOW", [F(1.0, p=0.6, d=nan)], 'SLOW')
run("all camera evidence missing, far -> SLOW", [F(1.0, r=None, p=None)], 'SLOW')
run("all camera evidence missing, near line -> STOP", [F(1.0, r=None, p=None, d=0.9)], 'STOP')
# ---- person memory (H = 0.3 s) ----
run("person 0.95 then dropout 0.1 s later -> held STOP", [F(1.0, p=0.95), F(1.1, p=0.1)], 'STOP')
run("dropout 0.3 s later (boundary) -> still held", [F(1.0, p=0.95), F(1.1, p=0.1), F(1.2, p=0.1), F(1.3, p=0.1)], 'STOP')
run("dropout 0.4 s later -> released (not extended by held frames)", [F(1.0, p=0.95), F(1.1, p=0.1), F(1.2, p=0.1), F(1.3, p=0.1), F(1.4, p=0.1)], 'GO')
run("person score missing right after a 0.95 -> held", [F(1.0, p=0.95), F(1.1, p=None)], 'STOP')
run("0.85 is not 'almost certain': no hold afterwards", [F(1.0, p=0.85), F(1.1, p=0.1)], 'GO')
run("memory switched off (ablation)", [F(1.0, p=0.95), F(1.1, p=0.1)], 'GO', person_hold=False)
run("person 0.9 outranks fresh green agreement", [F(1.0, m='green', r=0.0, p=0.9)], 'STOP')
# ---- state isolation ----
a = Q.RevisedRule(); a.step(1.0, 0.8, FAR, 0.9, 0.95, 'red', 1.0); b = Q.RevisedRule(); o = b.step(1.1, 0.8, FAR, 0.0, 0.1, 'green', 1.1)
ok = o[0] == 'GO'; bad += not ok; print(f"{'PASS' if ok else 'FAIL'}  new instance does not inherit another episode's state -> {o[0]}")
print('\nfailures:', bad)
