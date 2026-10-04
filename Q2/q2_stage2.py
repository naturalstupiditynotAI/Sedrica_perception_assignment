"""Q2 Stage 2: run the baseline on all 3 episodes (decisions first, reference afterwards for scoring only)."""
import os, zipfile, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from q2_rules import baseline, T_RED, T_PERSON, T_PERSON_STOP
os.makedirs('figures', exist_ok=True); z = zipfile.ZipFile('SeDriCa_perception_starter_data.zip')
ev = pd.read_csv(z.open('city/crossing_evidence.csv')); ev['age_s'] = (ev.time_s - ev.v2x_sample_time_s).round(2)
out = [baseline(r.red_score, r.person_score, r.v2x_light) for r in ev.itertuples()]
ev['decision'], ev['reason'] = [o[0] for o in out], [o[1] for o in out]
ev.to_csv('baseline_decisions.csv', index=False)
EPS = ['clear_green', 'late_red', 'person_crossing']; COL = {'GO': '#2ecc71', 'SLOW': '#f1c40f', 'STOP': '#e74c3c'}
# ---- reference loaded only now, for scoring and for the labelled band in the figure ----
ref = pd.read_csv(z.open('city/crossing_reference.csv')); d = ev.merge(ref, on=['episode', 'frame']); d['stop_required'] = d.stop_required.astype(int).astype(bool); d['person_on_crossing'] = d.person_on_crossing.astype(int).astype(bool)
def timeline(d, decision_col, path, title):
    fig, axs = plt.subplots(5, 3, figsize=(20, 11.5), gridspec_kw=dict(height_ratios=[3, 1, 1, 1, 1]), sharex='col')
    for j, e in enumerate(EPS):
        x = d[d.episode == e]; t = x.time_s.values
        a = axs[0, j]; a.plot(t, x.red_score, 'r-o', ms=3, label='red_score'); a.plot(t, x.person_score, 'b-o', ms=3, label='person_score')
        for y, ls in [(T_RED, ':'), (T_PERSON_STOP, '--')]: a.axhline(y, c='grey', ls=ls, lw=.8)
        a.text(t[-1], T_RED + .02, f'{T_RED} (red / person-probable)', fontsize=7, color='grey', ha='right'); a.text(t[-1], T_PERSON_STOP + .02, f'{T_PERSON_STOP} (person-stop)', fontsize=7, color='grey', ha='right')
        a.set_ylim(0, 1.08); a.set_title(e, weight='bold'); a.legend(fontsize=7, loc='upper left'); a.set_ylabel('score')
        for i, (col, lab) in enumerate([('v2x_light', 'V2X state'), ('age_s', 'message age (s)'), (decision_col, 'decision'), ('stop_required', 'reference: STOP\nrequired (eval only)')]):
            a = axs[i + 1, j]; a.set_yticks([]); a.set_ylim(0, 1); a.set_ylabel(lab, rotation=0, ha='right', va='center', fontsize=8)
            for k, row in enumerate(x.itertuples()):
                tt = row.time_s
                if col == 'v2x_light': a.add_patch(Rectangle((tt - .05, 0), .1, 1, fc='#2ecc71' if row.v2x_light == 'green' else '#e74c3c', ec='w', hatch='///' if row.age_s >= 0.3 else None)); 
                elif col == 'age_s': a.add_patch(Rectangle((tt - .04, 0), .08, min(1, row.age_s / .7), fc='#7f8c8d' if row.age_s < .3 else '#e67e22'))
                elif col == decision_col: a.add_patch(Rectangle((tt - .05, 0), .1, 1, fc=COL[row.__getattribute__(decision_col)], ec='w')); a.text(tt, .5, {'GO':'GO','SLOW':'SL','STOP':'ST'}[row.__getattribute__(decision_col)], ha='center', va='center', fontsize=7, weight='bold')
                else: a.add_patch(Rectangle((tt - .05, 0), .1, 1, fc='#c0392b' if row.stop_required else '#ecf0f1', ec='w'))
            a.set_xlim(t[0] - .08, t[-1] + .08)
        axs[4, j].set_xlabel('time (s)  [hatched V2X = message age >= 0.3 s]')
    fig.suptitle(title, fontsize=13, weight='bold'); plt.tight_layout(); plt.savefig(path, dpi=100); plt.close()
timeline(d, 'decision', 'figures/q2_baseline_timeline.png', 'Baseline decisions beside the inputs (message age ignored by the rule)')
# ---- summary ----
print('thresholds fixed in advance: T_RED=%.1f T_PERSON=%.1f T_PERSON_STOP=%.1f' % (T_RED, T_PERSON, T_PERSON_STOP))
rows = []
for e in EPS:
    x = d[d.episode == e]; req = x[x.stop_required]; stops = x[x.decision == 'STOP']
    rows.append(dict(episode=e, GO=int((x.decision == 'GO').sum()), SLOW=int((x.decision == 'SLOW').sum()), STOP=len(stops), required_STOP_frames=len(req),
                     missed_STOP=int((x.stop_required & (x.decision != 'STOP')).sum()), unnecessary_STOP=int((~x.stop_required & (x.decision == 'STOP')).sum()),
                     first_required=None if req.empty else int(req.frame.min()), first_STOP=None if stops.empty else int(stops.frame.min())))
print(pd.DataFrame(rows).to_string(index=False))
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 90)
for e in EPS:
    x = d[d.episode == e]; ch = x[x.decision != x.decision.shift()]
    print('\n', e, '- decision changes:'); print(ch[['frame', 'time_s', 'decision', 'reason']].to_string(index=False))
d.to_csv('baseline_decisions_with_reference.csv', index=False)
