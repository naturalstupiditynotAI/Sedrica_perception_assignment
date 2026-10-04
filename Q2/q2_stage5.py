"""Q2 Stage 5 (part e): seeded perturbation trials, baseline vs revised (same perturbed evidence for every rule).
Decisions use only the perturbed evidence; crossing_reference.csv is used only to score them."""
import os, zipfile, numpy as np, pandas as pd
import q2_rules as Q, q2_timeliness as T
SEED = 2026; N_TRIALS = 200
LEVELS = {  # perturbation rule, identical for all rules
  'A': dict(sigma=0.15, p_cam_drop=0.10, p_msg_drop=0.15, burst_len=6, p_burst=0.5),   # primary
  'B': dict(sigma=0.30, p_cam_drop=0.20, p_msg_drop=0.30, burst_len=8, p_burst=1.0)}   # harsher stress
EPS = ['clear_green', 'late_red', 'person_crossing']
z = zipfile.ZipFile('SeDriCa_perception_starter_data.zip')
ev = pd.read_csv(z.open('city/crossing_evidence.csv')).sort_values(['episode', 'frame']).reset_index(drop=True)
RULES = {'baseline': 'baseline', 'revised': dict(), 'revised_no_person_memory': dict(person_hold=False), 'revised_no_escalation': dict(escalate=False)}

def perturb(df, level, trial):
    """one perturbed copy of the evidence. Draw order is fixed, so every rule sees exactly the same numbers."""
    L = LEVELS[level]; rng = np.random.default_rng(np.random.SeedSequence([SEED, ord(level), trial])); d = df.copy(); d['v2x_light'] = d['v2x_light'].astype(object)
    for e in EPS:
        idx = d.index[d.episode == e]; n = len(idx)
        nr, npn = rng.normal(0, L['sigma'], n), rng.normal(0, L['sigma'], n)
        cam_drop = rng.random(n) < L['p_cam_drop']; msg_drop = rng.random(n) < L['p_msg_drop']
        burst = rng.random() < L['p_burst']; start = int(rng.integers(0, n - L['burst_len'] + 1))
        if burst: msg_drop[start:start + L['burst_len']] = True
        d.loc[idx, 'red_score'] = np.clip(d.loc[idx, 'red_score'].values + nr, 0, 1); d.loc[idx, 'person_score'] = np.clip(d.loc[idx, 'person_score'].values + npn, 0, 1)
        d.loc[idx[cam_drop], ['red_score', 'person_score']] = np.nan
        d.loc[idx[msg_drop], 'v2x_light'] = None; d.loc[idx[msg_drop], 'v2x_sample_time_s'] = np.nan
    return d

def decide(d, rule):
    out = []
    for e in EPS:
        inst = None if rule == 'baseline' else Q.RevisedRule(**RULES[rule])
        for r in d[d.episode == e].itertuples():
            out.append(Q.baseline(r.red_score, r.person_score, r.v2x_light)[0] if inst is None else inst.step(r.time_s, r.speed_mps, r.distance_to_line_m, r.red_score, r.person_score, r.v2x_light, r.v2x_sample_time_s)[0])
    return out

# ---- reference, used only inside score() ----
ref = pd.read_csv(z.open('city/crossing_reference.csv')); ref['stop_required'] = ref.stop_required.astype(int).astype(bool)
REQ = {e: ref[ref.episode == e].sort_values('frame').stop_required.values for e in EPS}
def score(d, dec, rule, level, trial):
    d = d.assign(dec=dec); rows = []
    for e in EPS:
        x = d[d.episode == e].sort_values('frame'); req = REQ[e]; isstop = (x.dec == 'STOP').values
        t_req = x.time_s.values[req.argmax()] if req.any() else np.nan
        later = isstop & (x.time_s.values >= t_req) if req.any() else np.zeros(len(x), bool)
        delay, comf = np.nan, None
        if later.any():
            k = int(np.argmax(later)); delay = round(x.time_s.values[k] - t_req, 2); comf = T.check(x.speed_mps.values[k], x.distance_to_line_m.values[k])['comfortable']
        rows.append(dict(level=level, trial=trial, rule=rule, episode=e, required=int(req.sum()), missed=int((req & ~isstop).sum()), unnecessary=int((~req & isstop).sum()), stop_before_required=bool(req.any() and isstop[:req.argmax()].any()),
                         delay_s=delay, any_stop_after_required=bool(later.any()), comfortable=comf, slow_or_go_while_required=int((req & ~isstop).sum())))
    return rows

if __name__ == '__main__':
    allrows = []
    for level in LEVELS:
        for tr in range(N_TRIALS):
            d = perturb(ev, level, tr)
            for rule in RULES: allrows += score(d, decide(d, rule), rule, level, tr)
    R = pd.DataFrame(allrows); R.to_csv('trials_all.csv', index=False)
    print('seed', SEED, '| trials per level', N_TRIALS, '| levels', LEVELS)
    for level in LEVELS:
        print(f'\n=== LEVEL {level} ===')
        agg = []
        for rule in RULES:
            for e in EPS:
                x = R[(R.level == level) & (R.rule == rule) & (R.episode == e)]
                agg.append(dict(rule=rule, episode=e, required=int(x.required.iloc[0]), missed_mean=round(x.missed.mean(), 2), missed_p90=x.missed.quantile(.9), unnec_mean=round(x.unnecessary.mean(), 2), trials_with_unnec_pct=round(100 * (x.unnecessary > 0).mean(), 1),
                                delay_median_s=x.delay_s.median(), delay_p90_s=x.delay_s.quantile(.9), no_stop_after_required_pct=round(100 * (~x.any_stop_after_required).mean(), 1) if x.required.iloc[0] else np.nan,
                                not_comfortable_trials=int((x.comfortable == False).sum())))
        A = pd.DataFrame(agg); A.insert(0, 'level', level); pd.set_option('display.width', 250); print(A.drop(columns=['level']).to_string(index=False)); A.to_csv(f'aggregate_level_{level}.csv', index=False)
        # paired comparison baseline vs revised on the same perturbed trials
        for e in EPS:
            b = R[(R.level == level) & (R.rule == 'baseline') & (R.episode == e)].set_index('trial'); r = R[(R.level == level) & (R.rule == 'revised') & (R.episode == e)].set_index('trial')
            print(f"  paired {e:16s} missed: revised fewer {int((r.missed < b.missed).sum())}, equal {int((r.missed == b.missed).sum())}, more {int((r.missed > b.missed).sum())} | unnecessary: revised fewer {int((r.unnecessary < b.unnecessary).sum())}, equal {int((r.unnecessary == b.unnecessary).sum())}, more {int((r.unnecessary > b.unnecessary).sum())}")
