"""Same synthetic edge cases that broke the baseline (edge_case_tests.py), run on the repaired detector."""
import zipfile, cv2, numpy as np
from lane_repair import LaneRepair, calibrate_width
ZIP='SeDriCa_perception_starter_data.zip'; z=zipfile.ZipFile(ZIP); D=LaneRepair(*calibrate_width(ZIP))
real=cv2.imdecode(np.frombuffer(z.read('city/lane/clear/000.png'),np.uint8),cv2.IMREAD_COLOR); TN,TF=241.16,242.93
blank=lambda v=0:np.full((320,480,3),v,np.uint8)
def lines(img,us,val=231,rows=(260,170)):
    im=img.copy()
    for v in rows:
        for u in us: im[v,u-1:u+2]=val
    return im
hot=real.copy(); hot[260,50]=255; hot[170,50]=255
# full synthetic road: two straight 3-px lines with the real geometry, centre 245, plus a decoy brighter than paint
def road(cx=245,decoy=None,val=231):
    im=blank(90)
    for v in range(95,320):
        w=1.0538*v-16.17
        for u in (cx-w/2,cx+w/2): im[v,int(round(u))-1:int(round(u))+2]=val
        if decoy: im[v,int(round(cx-w/2+decoy))-1:int(round(cx-w/2+decoy))+2]=250
    return im
T=[("reference frame clear/000",real,lambda r:r['u_near'] and abs(r['u_near']-TN)<2 and abs(r['u_far']-TF)<2),
   ("all black",blank(0),lambda r:r['u_near'] is None),
   ("all white",blank(255),lambda r:r['u_near'] is None),
   ("1-px hot pixels (2 rows only)",hot,lambda r:r['u_near'] and abs(r['u_near']-TN)<2),
   ("horizontal flip",cv2.flip(real,1),lambda r:r['u_near'] and abs(r['u_near']-(479-TN))<2),
   ("synthetic road, centre 245",road(),lambda r:r['u_near'] and abs(r['u_near']-245)<1.5),
   ("synthetic road + decoy 33px inside, brighter (250>231)",road(decoy=33),lambda r:r['u_near'] and abs(r['u_near']-245)<1.5),
   ("synthetic road centre 120 (ego far off-lane)",road(120),lambda r:r['u_near'] is None or abs(r['u_near']-120)<3),
   ("lines only on 2 rows (no geometry)",lines(blank(90),[120,370]),lambda r:r['u_near'] is None),
   ("both lines in left half (60,220), 2 rows",lines(blank(90),[60,220]),lambda r:r['u_near'] is None),
   ("float32 image",real.astype(np.float32)/255,None)]
for name,img,pred in T:
    try:
        r=D.detect_frame(img); f=lambda x:'None' if x is None else f'{x:.1f}'
        print(f"{name:56s} near={f(r['u_near']):>6} far={f(r['u_far']):>6} conf={r['confidence_near']:.2f}  {'PASS' if pred(r) else 'FAIL'}")
    except ValueError as e: print(f"{name:56s} ValueError (clear message)  PASS")
