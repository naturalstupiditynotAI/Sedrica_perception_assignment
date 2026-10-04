"""Q2 Stage 1 - map what the car knows. Produces figures/q2_annotated_frames.png and figures/q2_signal_flow.png.
Image measurements here (lamp colour, person mask, road edges) are INSPECTION aids. The person mask uses the same
frame index of clear_green as background (only possible offline); a running system could not do that.
crossing_reference.csv is never read."""
import os, zipfile, cv2, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
os.makedirs('figures', exist_ok=True)
z = zipfile.ZipFile('SeDriCa_perception_starter_data.zip')
ev = pd.read_csv(z.open('city/crossing_evidence.csv')); ev['age_s'] = (ev.time_s - ev.v2x_sample_time_s).round(2)
def load(e, f): return cv2.imdecode(np.frombuffer(z.read(f'city/crossing/{e}/{f:03d}.png'), np.uint8), cv2.IMREAD_COLOR)
def lamp(img):
    c = img.astype(int); R, G, B = c[..., 2], c[..., 1], c[..., 0]
    red = (R > 170) & (G < 100) & (B < 100); grn = (G > 150) & (R < 120) & (B < 150)
    m = red if red.sum() > grn.sum() else grn; ys, xs = np.where(m)
    return ('red' if red.sum() > grn.sum() else 'green'), int(m.sum()), (xs.min(), ys.min(), xs.max(), ys.max())
def road_edges(img, v):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[v]; idx = np.flatnonzero(g > 190)
    runs = [(p[0] + p[-1]) / 2 for p in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)]
    return min(runs), max(runs)
def person(e, f):
    m = np.abs(load(e, f).astype(int) - load('clear_green', f).astype(int)).sum(2) > 60
    if e != 'person_crossing' or m.sum() == 0: return None   # other episodes differ from clear_green only by the lamp
    ys, xs = np.where(m); v = ys.max(); return xs.min(), ys.min(), xs.max(), v, xs[ys >= v - 2].mean()

# ---------- annotated frames ----------
cases = [('clear_green', 7, 'GREEN episode, f7'), ('late_red', 12, 'LATE-RED episode, f12'), ('person_crossing', 8, 'PERSON episode, f8 (person outside road)'), ('person_crossing', 12, 'PERSON episode, f12 (person in path)')]
fig, ax = plt.subplots(1, 4, figsize=(26, 6.6))
for a, (e, f, name) in zip(ax, cases):
    img = load(e, f); r = ev[(ev.episode == e) & (ev.frame == f)].iloc[0]; a.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)); a.set_title(name, fontsize=11, weight='bold')
    col, npx, (x0, y0, x1, y1) = lamp(img); a.add_patch(Rectangle((x0 - 8, y0 - 12), x1 - x0 + 16, y1 - y0 + 24, fc='none', ec='yellow', lw=2))
    a.text(x0 - 150, y0 - 18, f'lamp (image): {col.upper()}, {npx} px\nred_score = {r.red_score:.2f}', color='yellow', fontsize=9, weight='bold')
    pp = person(e, f); verdict = 'no person in image'
    if pp is not None:
        ux0, vy0, ux1, vy1, uf = pp; L, Rr = road_edges(load('clear_green', f), vy1)       # edges from the person-free background (inspection only)
        inside = L < uf < Rr; verdict = f'person foot u={uf:.0f}, road edges u={L:.0f}..{Rr:.0f} -> ' + ('INSIDE the path' if inside else 'OUTSIDE the path')
        a.add_patch(Rectangle((ux0 - 3, vy0 - 3), ux1 - ux0 + 6, vy1 - vy0 + 6, fc='none', ec='cyan', lw=2)); a.plot(uf, vy1, 'c*', ms=14)
        a.hlines(vy1, L, Rr, colors='lime', linestyles='--', lw=1.5); a.plot([L, Rr], [vy1, vy1], 'g|', ms=18, mew=3)
        a.text(60, 300, f'person_score = {r.person_score:.2f}', color='cyan', fontsize=10, weight='bold')
    else: a.text(60, 300, f'person_score = {r.person_score:.2f}  (no person visible)', color='cyan', fontsize=10, weight='bold')
    txt = (f'time {r.time_s:.1f} s | speed {r.speed_mps:.1f} m/s | distance to line {r.distance_to_line_m:.2f} m\n'
           f'V2X: {r.v2x_light.upper()}, sampled at {r.v2x_sample_time_s:.1f} s  ->  age {r.age_s:.1f} s\n{verdict}')
    a.set_xlabel(txt, fontsize=9, loc='left'); a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); plt.savefig('figures/q2_annotated_frames.png', dpi=100); plt.close()

# ---------- signal-flow diagram ----------
fig, ax = plt.subplots(figsize=(17, 9.5)); ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis('off')
DIRECT, UNC, DEC, EVAL = '#d8f0d8', '#ffe2b8', '#cfe3ff', '#f7d4d4'
def box(x, y, w, h, t, fc, ec='k', ls='-', fs=9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.3', fc=fc, ec=ec, lw=1.6, ls=ls)); ax.text(x + w/2, y + h/2, t, ha='center', va='center', fontsize=fs, weight='bold' if bold else 'normal')
def arrow(x0, y0, x1, y1, ls='-', c='k'): ax.annotate('', (x1, y1), (x0, y0), arrowprops=dict(arrowstyle='->', lw=1.6, ls=ls, color=c))
ax.text(50, 58.3, 'Q2 signal flow: what the running system knows (labels are NOT part of it)', ha='center', fontsize=13, weight='bold')
box(1, 44, 17, 9, 'Camera frame\n480x320 image\n(lamp + person visible)', UNC, ls='--', bold=True)
box(1, 30, 17, 9, 'V2X message\nlight state + sample time\n(describes an OLDER moment)', UNC, ls='--', bold=True)
box(1, 14, 17, 11, 'Ego state\ntime_s, speed_mps,\ndistance_to_line_m\n(treated as direct)', DIRECT, bold=True)
box(26, 46, 19, 8, 'Light cue\nred_score in [0,1]\nnoisy, not a probability', UNC, ls='--')
box(26, 35.5, 19, 8, 'Person cue\nperson_score in [0,1]\n(+ position vs road region)', UNC, ls='--')
box(26, 25, 19, 8, 'V2X state + age\nage = time_s - v2x_sample_time_s\n(state is true only as of its sample time)', DIRECT)
box(26, 13, 19, 9.5, 'Stopping distance\nd_stop = v*tau + v^2/(2a)\ntau = 0.15 s, a = 0.8 m/s^2\nvs distance_to_line_m', DIRECT)
box(55, 25, 20, 20, 'Decision logic\n(rules / state machine)\n\nreconcile camera vs V2X,\ndiscount stale messages,\ncheck timeliness of STOP', DEC, bold=True)
box(83, 33, 15, 12, 'GO / SLOW / STOP\n+ reason string\n(per frame)', DEC, bold=True, fs=10)
for (x0, y0, x1, y1, ls) in [(18.3, 49, 25.7, 50, '--'), (18.3, 47, 25.7, 40, '--'), (18.3, 34, 25.7, 28, '--'), (18.3, 20, 25.7, 18, '-'), (13, 29.5, 13, 25.4, '-'), (18.3, 21, 25.7, 28, '-'), (45.3, 50, 54.7, 40, '--'), (45.3, 39.5, 54.7, 36, '--'), (45.3, 29, 54.7, 31, '-'), (45.3, 17.5, 54.7, 27, '-'), (75.3, 38, 82.7, 38, '-')]: arrow(x0, y0, x1, y1, ls)
box(55, 4, 43, 11, 'EVALUATION ONLY (offline, after decisions exist)\ncrossing_reference.csv: true light, person on crossing, STOP required\n-> counts missed-STOP and unnecessary-STOP frames, response delays', EVAL, ec='#b00000', ls='--', bold=True)
arrow(90.5, 32.6, 90.5, 15.6, c='#b00000'); ax.text(91.5, 24, 'decisions\nare scored', fontsize=8, color='#b00000')
ax.plot([48, 52], [12, 12], 'r-', lw=0); ax.text(47.5, 6.3, 'X  no path from labels\nto the decision logic', fontsize=9, color='#b00000', weight='bold', ha='center')
ax.add_patch(Rectangle((1, 1), 2.4, 2, fc=DIRECT, ec='k')); ax.text(4, 2, 'direct / computed exactly', fontsize=8, va='center')
ax.add_patch(Rectangle((22, 1), 2.4, 2, fc=UNC, ec='k', ls='--')); ax.text(25, 2, 'uncertain (late, noisy, or old)', fontsize=8, va='center')
ax.add_patch(Rectangle((44, 1), 2.4, 2, fc=DEC, ec='k')); ax.text(47, 2, 'decision', fontsize=8, va='center')
plt.tight_layout(); plt.savefig('figures/q2_signal_flow.png', dpi=100); plt.close()
print('ok')
