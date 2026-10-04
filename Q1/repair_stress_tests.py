"""Stress tests for lane_repair.LaneRepair on perturbed REAL frames. Reference CSV is used only to score.
Run: python repair_stress_tests.py"""
import zipfile, cv2, numpy as np, pandas as pd
from lane_repair import LaneRepair, calibrate_width
ZIP='SeDriCa_perception_starter_data.zip'; z=zipfile.ZipFile(ZIP)
k,b=calibrate_width(ZIP); ref=pd.read_csv(z.open('city/lane_reference.csv'))
def load(seq,f): return cv2.imdecode(np.frombuffer(z.read(f'city/lane/{seq}/{f:03d}.png'),np.uint8),cv2.IMREAD_COLOR)
def gray(im): return cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
ROAD=(93,93,93)
def erase(im,rows=None,side=None,seam=False):
    """paint pixels (gray>190) -> road grey, restricted by rows / image half"""
    im=im.copy(); g=gray(im); m=g>190
    if side=='L': m[:,240:]=False
    if side=='R': m[:,:240]=False
    keep=np.zeros_like(m)
    r0,r1=rows if rows else (0,320); keep[r0:r1]=True
    im[m&keep]=ROAD; return im
def boost_seam(im,val=240):
    im=im.copy(); g=gray(im); m=(g>150)&(g<=190); m[:90]=False; im[m]=val; return im
def salt(im,p=0.002,seed=0):
    rng=np.random.default_rng(seed); im=im.copy(); m=rng.random(im.shape[:2])<p; im[m]=255; return im
def gnoise(s): return lambda im: np.clip(im.astype(float)+np.random.default_rng(1).normal(0,s,im.shape),0,255).astype(np.uint8)
def expo(a): return lambda im: np.clip(im.astype(float)*a,0,255).astype(np.uint8)

S=[("no perturbation (clear)",'clear',lambda im:im),
   ("left paint erased everywhere",'clear',lambda im:erase(im,side='L')),
   ("right paint erased everywhere",'clear',lambda im:erase(im,side='R')),
   ("BOTH erased rows 130-319 (only top 35 rows)",'clear',lambda im:erase(im,rows=(130,320))),
   ("BOTH erased rows 95-249 (only near 70 rows)",'clear',lambda im:erase(im,rows=(0,250))),
   ("BOTH erased rows 95-200",'clear',lambda im:erase(im,rows=(0,200))),
   ("seam boosted to paint level (missing seq)",'missing',boost_seam),
   ("seam boosted + left erased rows 95-250",'missing',lambda im:erase(boost_seam(im),rows=(95,250),side='L')),
   ("salt noise 0.2% px",'clear',lambda im:salt(im)),
   ("gaussian noise sigma=15",'clear',gnoise(15)),
   ("gaussian noise sigma=30",'clear',gnoise(30)),
   ("exposure x0.7",'clear',expo(0.7)),
   ("exposure x0.5",'clear',expo(0.5)),
   ("exposure x1.3",'clear',expo(1.3)),
   ("exposure x2.2 (road>paint level)",'clear',expo(2.2)),
   ("blank grey image",'clear',lambda im:np.full_like(im,100)),
   ("all white",'clear',lambda im:np.full_like(im,255))]
print(f"{'scenario':46s} {'n':>2} {'unk%':>5} {'MAEn':>6} {'MAEf':>6} {'maxE':>6} {'conf':>5}  answered&err>3  | err of withheld")
for name,seq,fn in S:
    E=[];C=[];unk=0;n=0;bad=0;W=[]
    for f in range(0,24,2):
        r=LaneRepair(k,b).detect_frame(fn(load(seq,f))); t=ref[(ref.sequence==seq)&(ref.frame==f)].iloc[0]
        for key,ck,tv in [('u_near','confidence_near',t.near_center_x_px),('u_far','confidence_far',t.far_center_x_px)]:
            n+=1; C.append(r[ck])
            if r[key] is None:
                unk+=1; W.append(abs(r['raw_'+key[2:]]-tv) if r['raw_'+key[2:]] is not None else np.nan)
            else:
                E.append((abs(r[key]-tv),key)); bad+=abs(r[key]-tv)>3
    en=[e for e,kk in E if kk=='u_near']; ef=[e for e,kk in E if kk=='u_far']; f_=lambda x:f"{np.mean(x):6.2f}" if x else "   n/a"
    print(f"{name:46s} {n//2:2d} {unk/n*100:5.0f} {f_(en)} {f_(ef)} {max([e for e,_ in E],default=float('nan')):6.1f} {np.mean(C):5.2f}  {bad:>3}   {('mean %.1f max %.1f'%(np.nanmean(W),np.nanmax(W))) if W and not np.all(np.isnan(W)) else '-'}")
# width-model sensitivity
print("\nwidth-model error (camera pitch / calibration drift), clear frames:")
for sc in [0.97,1.03,1.06,1.10]:
    E=[];U=0
    for f in range(0,24,2):
        r=LaneRepair(k*sc,b*sc).detect_frame(load('clear',f)); t=ref[(ref.sequence=='clear')&(ref.frame==f)].iloc[0]
        for key,tv in [('u_near',t.near_center_x_px),('u_far',t.far_center_x_px)]:
            if r[key] is None: U+=1
            else: E.append(abs(r[key]-tv))
    print(f"  width x{sc:.2f}: mean err={np.mean(E) if E else float('nan'):.2f} max={np.max(E) if E else float('nan'):.2f} unknown={U}/24")
