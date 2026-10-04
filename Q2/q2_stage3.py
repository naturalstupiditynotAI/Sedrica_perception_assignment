"""Q2 Stage 3: baseline vs revised on the 3 episodes. Decisions first; reference only afterwards, for scoring."""
import os, zipfile, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import q2_rules as Q
os.makedirs('figures', exist_ok=True); z = zipfile.ZipFile('SeDriCa_perception_starter_data.zip')
ev = pd.read_csv(z.open('city/crossing_evidence.csv')); ev['age_s'] = (ev.time_s - ev.v2x_sample_time_s).round(2)
EPS = ['clear_green', 'late_red', 'person_crossing']; COL = {'GO': '#2ecc71', 'SLOW': '#f1c40f', 'STOP': '#e74c3c'}

def run_revised(df, cfg=None):
    out = []
    for e in EPS:
        rule = Q.RevisedRule()
        for r in df[df.episode == e].sort_values('frame').itertuples():
            out.append(rule.step(r.time_s, r.speed_mps, r.distance_to_line_m, r.red_score, r.person_score, r.v2x_light, r.v2x_sample_time_s))
    return out
base = [Q.baseline(r.red_score, r.person_score, r.v2x_light) for r in ev.itertuples()]
rev = run_revised(ev)
ev['base'], ev['base_reason'] = [b[0] for b in base], [b[1] for b in base]
ev['rev'], ev['rev_reason'] = [x[0] for x in rev], [x[1] for x in rev]
ev['eff_state'], ev['eff_age'], ev['margin_m'] = [x[2]['eff_state'] for x in rev], [x[2]['eff_age'] for x in rev], [x[2]['margin'] for x in rev]
ev.to_csv('revised_decisions.csv', index=False)

# ---- which messages mislead if age is ignored? (row state differs from the newest information already received) ----
mis = ev[(ev.age_s > 0) & (ev.v2x_light != ev.eff_state)][['episode', 'frame', 'time_s', 'v2x_light', 'v2x_sample_time_s', 'age_s', 'eff_state', 'eff_age', 'red_score']]
print('rows whose message contradicts newer information already received:'); print(mis.to_string(index=False))
print('\nall stale rows (age>0), effective age after supersession:'); print(ev[ev.age_s > 0][['episode', 'frame', 'age_s', 'eff_age']].groupby('episode').agg(rows=('frame', 'count'), max_row_age=('age_s', 'max'), max_eff_age=('eff_age', 'max')).to_string())

# ---- reference only now ----
ref = pd.read_csv(z.open('city/crossing_reference.csv')); d = ev.merge(ref, on=['episode', 'frame']); d['stop_required'] = d.stop_required.astype(int).astype(bool)
def summary(col):
    rows = []
    for e in EPS:
        x = d[d.episode == e]; req = x[x.stop_required]; st = x[x[col] == 'STOP']
        rows.append(dict(episode=e, rule=col, GO=int((x[col] == 'GO').sum()), SLOW=int((x[col] == 'SLOW').sum()), STOP=len(st), required=len(req),
                         missed_STOP=int((x.stop_required & (x[col] != 'STOP')).sum()), unnecessary_STOP=int((~x.stop_required & (x[col] == 'STOP')).sum()),
                         first_required_s=None if req.empty else req.time_s.min(), first_STOP_s=None if st.empty else st.time_s.min()))
    return rows
S = pd.DataFrame(summary('base') + summary('rev')); S['rule'] = S.rule.map({'base': 'baseline', 'rev': 'revised'}); print('\n', S.to_string(index=False)); S.to_csv('stage3_summary.csv', index=False)
print('\nframes where the revision changed the decision:')
ch = d[d.base != d.rev][['episode', 'frame', 'time_s', 'base', 'rev', 'stop_required', 'rev_reason']]; pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 110); print(ch.to_string(index=False))
d.to_csv('revised_decisions_with_reference.csv', index=False)

# ---- timeline figure ----
fig, axs = plt.subplots(7, 3, figsize=(20, 14.5), gridspec_kw=dict(height_ratios=[3, 1, 1.2, 1, 1, 1, 1]), sharex='col')
for j, e in enumerate(EPS):
    x = d[d.episode == e]; t = x.time_s.values
    a = axs[0, j]; a.plot(t, x.red_score, 'r-o', ms=3, label='red_score'); a.plot(t, x.person_score, 'b-o', ms=3, label='person_score'); a.set_ylim(0, 1.08); a.set_title(e, weight='bold'); a.legend(fontsize=7, loc='upper left'); a.set_ylabel('score')
    for y in (Q.T_RED, Q.T_PERSON_STOP): a.axhline(y, c='grey', ls=':', lw=.8)
    labels = ['V2X state in this row\n(hatched = row age >= 0.3 s)', 'message age (s)\nbars: row, line: effective', 'baseline', 'revised', 'reference: STOP\nrequired (eval only)']
    for i, lab in enumerate(labels):
        a = axs[i + 1, j]; a.set_yticks([]); a.set_ylim(0, 1); a.set_ylabel(lab, rotation=0, ha='right', va='center', fontsize=8); a.set_xlim(t[0] - .08, t[-1] + .08)
        for row in x.itertuples():
            tt = row.time_s
            if i == 0: a.add_patch(Rectangle((tt - .05, 0), .1, 1, fc='#2ecc71' if row.v2x_light == 'green' else '#e74c3c', ec='w', hatch='///' if row.age_s >= 0.3 else None))
            elif i == 1: a.add_patch(Rectangle((tt - .04, 0), .08, min(1, row.age_s / .7), fc='#7f8c8d' if row.age_s < .3 else '#e67e22'))
            elif i in (2, 3): c = row.base if i == 2 else row.rev; a.add_patch(Rectangle((tt - .05, 0), .1, 1, fc=COL[c], ec='w')); a.text(tt, .5, {'GO': 'GO', 'SLOW': 'SL', 'STOP': 'ST'}[c], ha='center', va='center', fontsize=7, weight='bold')
            else: a.add_patch(Rectangle((tt - .05, 0), .1, 1, fc='#c0392b' if row.stop_required else '#ecf0f1', ec='w'))
        if i == 1: a.step(t, np.minimum(1, x.eff_age.fillna(.7).values / .7), where='mid', c='k', lw=1.4)
    axs[6, j].set_xlabel('time (s)')
# the figure has 6 data rows + score row; hide the unused 7th row
for j in range(3): axs[6, j].remove()
fig.suptitle('Baseline vs revised decisions beside the inputs (nominal data)', fontsize=13, weight='bold'); plt.tight_layout(); plt.savefig('figures/q2_revised_timeline.png', dpi=100); plt.close()
