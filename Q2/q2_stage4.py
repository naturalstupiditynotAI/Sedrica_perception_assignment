"""Q2 Stage 4: stopping-distance check at the first STOP request of baseline and revised, per episode.
Decisions first; the reference is loaded only at the end for the eval-only 'first required' column."""
import os, zipfile, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
import q2_rules as Q, q2_timeliness as T
os.makedirs('figures', exist_ok=True); z = zipfile.ZipFile('SeDriCa_perception_starter_data.zip')
ev = pd.read_csv(z.open('city/crossing_evidence.csv')); EPS = ['clear_green', 'late_red', 'person_crossing']
base, rev = [], []
for e in EPS:
    rule = Q.RevisedRule()
    for r in ev[ev.episode == e].sort_values('frame').itertuples():
        base.append(Q.baseline(r.red_score, r.person_score, r.v2x_light)); rev.append(rule.step(r.time_s, r.speed_mps, r.distance_to_line_m, r.red_score, r.person_score, r.v2x_light, r.v2x_sample_time_s))
ev = ev.sort_values(['episode', 'frame']).reset_index(drop=True)
ev['base'], ev['base_reason'] = [b[0] for b in base], [b[1] for b in base]; ev['rev'], ev['rev_reason'] = [x[0] for x in rev], [x[1] for x in rev]
print('speed constant 0.8 m/s in every row:', bool((ev.speed_mps == 0.8).all()), '| d_stop(0.8) = %.3f m' % Q.d_stop(0.8))
rows = []
for e in EPS:
    x = ev[ev.episode == e]
    for rule_name, col, rcol in [('baseline', 'base', 'base_reason'), ('revised', 'rev', 'rev_reason')]:
        fs = T.first_stop(x, col)
        if fs is None:
            rows.append(dict(episode=e, rule=rule_name, first_STOP_frame=None, note='no STOP request in 24 frames')); continue
        c = T.check(fs.speed_mps, fs.distance_to_line_m); before = x[(x.frame < fs.frame)]
        prior = before[col].tolist(); last_state = prior[-1] if prior else 'none'
        rows.append(dict(episode=e, rule=rule_name, first_STOP_frame=int(fs.frame), time_s=fs.time_s, speed_mps=fs.speed_mps, distance_m=fs.distance_to_line_m, d_stop_m=round(c['d_stop'], 3),
                         margin_m=round(c['margin_m'], 3), comfortable=c['comfortable'], decision_budget_s=round(c['budget_s'], 2), a_required=round(c['a_required'], 3), state_just_before=last_state, reason=fs[rcol]))
R = pd.DataFrame(rows)
# latest moment a STOP could still have been comfortable, extrapolating the logged constant speed beyond the window
for e in EPS:
    x = ev[ev.episode == e]; v = x.speed_mps.iloc[-1]; slope = (x.distance_to_line_m.iloc[-1] - x.distance_to_line_m.iloc[0]) / (x.time_s.iloc[-1] - x.time_s.iloc[0])
    t_last = x.time_s.iloc[-1] + (x.distance_to_line_m.iloc[-1] - Q.d_stop(v)) / v
    print(f'{e}: distance slope {slope:.3f} m/s; last comfortable STOP time (extrapolated) = {t_last:.2f} s; window ends at {x.time_s.iloc[-1]:.1f} s; margin at last frame = {x.distance_to_line_m.iloc[-1] - Q.d_stop(v):.2f} m')
pd.set_option('display.width', 260); pd.set_option('display.max_colwidth', 80)
print(R.drop(columns=['reason']).to_string(index=False)); print()
for r in R.itertuples():
    if r.first_STOP_frame == r.first_STOP_frame and r.first_STOP_frame is not None: print(f'{r.episode:16s}{r.rule:9s} f{r.first_STOP_frame}: {r.reason}')
# what came first when SLOW preceded the first STOP: the SLOW run and its evidence
print()
for e in EPS:
    x = ev[ev.episode == e]
    for rule_name, col, rcol in [('baseline', 'base', 'base_reason'), ('revised', 'rev', 'rev_reason')]:
        fs = T.first_stop(x, col); lim = x if fs is None else x[x.frame < fs.frame]
        sl = lim[lim[col] == 'SLOW']
        for f, g in sl.groupby((sl.frame.diff() != 1).cumsum()): print(f'{e:16s}{rule_name:9s} SLOW f{int(g.frame.min())}-{int(g.frame.max())}: {g[rcol].iloc[0]}' + (f'  (+{len(g)-1} more frames, last: {g[rcol].iloc[-1]})' if len(g) > 1 and g[rcol].iloc[0] != g[rcol].iloc[-1] else ''))
# ---- reference, eval only ----
ref = pd.read_csv(z.open('city/crossing_reference.csv')); ref['stop_required'] = ref.stop_required.astype(int).astype(bool)
d = ev.merge(ref, on=['episode', 'frame']); req = d[d.stop_required].groupby('episode').time_s.min()
R['first_required_s (eval only)'] = R.episode.map(req); R['delay_s (eval only)'] = (R.time_s - R['first_required_s (eval only)']).round(2); R['extra_travel_m (eval only)'] = (R['delay_s (eval only)'] * R.speed_mps).round(2)
R.to_csv('stopping_distance_check.csv', index=False); print('\n', R[['episode', 'rule', 'first_STOP_frame', 'first_required_s (eval only)', 'delay_s (eval only)', 'extra_travel_m (eval only)']].to_string(index=False))
# ---- figure ----
fig, ax = plt.subplots(1, 3, figsize=(19, 5.2), sharey=True)
for a, e in zip(ax, EPS):
    x = ev[ev.episode == e]; a.plot(x.time_s, x.distance_to_line_m, 'k-o', ms=3, label='distance_to_line_m'); a.axhline(Q.d_stop(0.8), c='#c0392b', ls='--', label=f'd_stop = {Q.d_stop(0.8):.2f} m (v=0.8)')
    a.fill_between(x.time_s, 0, Q.d_stop(0.8), color='#c0392b', alpha=.12, label='too late zone (distance < d_stop)')
    for rule_name, col, c, off in [('baseline', 'base', '#e67e22', 0.0), ('revised', 'rev', '#2980b9', 0.0)]:
        fs = T.first_stop(x, col)
        if fs is not None: a.axvline(fs.time_s + (0.012 if rule_name == 'revised' else -0.012), c=c, lw=2, label=f'{rule_name} first STOP (t={fs.time_s:.1f} s, margin {fs.distance_to_line_m - Q.d_stop(fs.speed_mps):.2f} m)')
    if e in req.index: a.axvline(req[e], c='grey', ls=':', lw=2, label=f'first required (eval only) t={req[e]:.1f} s')
    if not any(T.first_stop(x, c) is not None for c in ('base', 'rev')): a.text(0.05, 0.5, 'no STOP request by either rule', transform=a.transAxes, fontsize=11, weight='bold')
    a.set_title(e, weight='bold'); a.set_xlabel('time (s)'); a.set_ylim(0, 3); a.grid(alpha=.3); a.legend(fontsize=7, loc='upper right')
ax[0].set_ylabel('metres')
plt.tight_layout(); plt.savefig('figures/q2_stopping_margin.png', dpi=100); plt.close()
