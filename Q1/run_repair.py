"""Runs the repaired detector on all 72 frames (predictions first, labels afterwards) and
compares with the frozen baseline. Usage: python run_repair.py"""
import zipfile, cv2, numpy as np, pandas as pd, time
from lane_repair import LaneRepair, calibrate_width
ZIP='SeDriCa_perception_starter_data.zip'
k,b=calibrate_width(ZIP); print(f"calibrated width model (clear images only): w(v)={k:.4f}*v{b:+.2f}")
det=LaneRepair(k,b); z=zipfile.ZipFile(ZIP); rows=[]; t0=time.time()
for seq in ['clear','shadow','missing']:
    for f in range(24):
        img=cv2.imdecode(np.frombuffer(z.read(f'city/lane/{seq}/{f:03d}.png'),np.uint8),cv2.IMREAD_COLOR)
        r=det.detect_frame(img); rows.append(dict(sequence=seq,frame=f,pred_u_near=r['u_near'],pred_u_far=r['u_far'],conf_near=r['confidence_near'],conf_far=r['confidence_far'],n_rows=r['n_rows']))
print(f"time/frame: {(time.time()-t0)/72*1000:.0f} ms")
d=pd.DataFrame(rows); ref=pd.read_csv(z.open('city/lane_reference.csv'))      # labels loaded only now
d=d.merge(ref,on=['sequence','frame']); d['err_near']=(d.pred_u_near-d.near_center_x_px).abs(); d['err_far']=(d.pred_u_far-d.far_center_x_px).abs()
d.to_csv('repair_results.csv',index=False)
base=pd.read_csv('baseline_results.csv')
print("\n            BASELINE (near | far)                REPAIRED (near | far)")
print("seq        MAE   unk%   MAE   unk%   maxE      MAE   unk%   MAE   unk%   maxE")
for s in ['clear','shadow','missing']:
    b_=base[base.sequence==s]; r_=d[d.sequence==s]
    bn,bf=b_.error_u_near,b_.error_u_far
    print(f"{s:8s} {bn.mean():5.2f} {bn.isna().mean()*100:5.1f} {bf.mean():5.2f} {bf.isna().mean()*100:5.1f} {max(bn.max(),bf.max()):6.1f}   "
          f"{r_.err_near.mean():5.2f} {r_.err_near.isna().mean()*100:5.1f} {r_.err_far.mean():5.2f} {r_.err_far.isna().mean()*100:5.1f} {max(r_.err_near.max(),r_.err_far.max()):6.1f}")
print("\nunknown frames (near/far):", d[d.pred_u_near.isna()][['sequence','frame']].values.tolist(), d[d.pred_u_far.isna()][['sequence','frame']].values.tolist())
print("\nconfidence vs error (both rows pooled):")
P=pd.concat([d[['sequence','frame','conf_near','err_near']].set_axis(['sequence','frame','c','e'],axis=1),d[['sequence','frame','conf_far','err_far']].set_axis(['sequence','frame','c','e'],axis=1)])
for lo,hi in [(0,.25),(.25,.5),(.5,.75),(.75,1.01)]:
    x=P[(P.c>=lo)&(P.c<hi)]; print(f"  conf [{lo:.2f},{hi:.2f}): n={len(x):3d}  answered={x.e.notna().sum():3d}  mean err={x.e.mean():.2f}  max err={x.e.max():.2f}")
print("  answered with err>3 px:", int((P.e>3).sum()), "| worst frames:", P.sort_values('e',ascending=False).head(3)[['sequence','frame','c','e']].round(2).values.tolist())
