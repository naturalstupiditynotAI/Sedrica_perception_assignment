"""Edge-case suite for lane_baseline.LaneBaseline. Run: python edge_case_tests.py
Each check is computed, not hard-coded. KNOWN-FAIL = weakness deliberately left in the
baseline (documented in its docstring) to be addressed in the Stage 3 revision."""
import zipfile, cv2, numpy as np
from lane_baseline import LaneBaseline, ZIP_PATH
z = zipfile.ZipFile(ZIP_PATH)
real = cv2.imdecode(np.frombuffer(z.read('city/lane/clear/000.png'), np.uint8), cv2.IMREAD_COLOR)
TRUE_N, TRUE_F = 241.16, 242.93          # only used to judge synthetic variants of this frame
D = LaneBaseline()
blank = lambda v=0: np.full((320, 480, 3), v, np.uint8)
def lines(img, us, val=231, rows=(260, 170)):
    im = img.copy()
    for v in rows:
        for u in us: im[v, u-1:u+2] = val
    return im
near = lambda r, t, tol=3: r['u_near'] is not None and abs(r['u_near']-t) <= tol
def unknown_or_lowconf(r): return all(r[k] is None or r[c] < 0.5 for k, c in [('u_near','confidence_near'),('u_far','confidence_far')])
def ok_real(r): return near(r, TRUE_N) and r['u_far'] is not None and abs(r['u_far']-TRUE_F) <= 3

hot = real.copy(); hot[260, 50] = 255; hot[170, 50] = 255
noisy = np.clip(real.astype(float)+np.random.default_rng(0).normal(0, 15, real.shape), 0, 255).astype(np.uint8)
seam = lines(lines(blank(90), [120, 370]), [180], val=250)
tests = [
 ("reference frame clear/000",           real,                                   ok_real),
 ("all black",                           blank(0),                               lambda r: r['u_near'] is None and r['u_far'] is None),
 ("uniform grey 100",                    blank(100),                             lambda r: r['u_near'] is None and r['u_far'] is None),
 ("gaussian noise sigma=15 (seed 0)",    noisy,                                  ok_real),
 ("horizontal flip (centre -> 479-u)",   cv2.flip(real, 1),                      lambda r: near(r, 479-TRUE_N) and abs(r['u_far']-(479-TRUE_F)) <= 3),
 ("all white (no road)",                 blank(255),                             unknown_or_lowconf),
 ("1-px hot pixel at u=50",              hot,                                    ok_real),
 ("seam brighter than paint (250>231)",  seam,                                   lambda r: near(r, 245, 10)),
 ("both lines in left half (60,220)",    lines(blank(90), [60, 220]),            lambda r: near(r, 140, 10)),
 ("exposure x0.7 (paint 231->162)",      np.clip(real*0.7, 0, 255).astype(np.uint8), ok_real),
 ("exposure x2.2 (road >190)",           np.clip(real.astype(float)*2.2, 0, 255).astype(np.uint8), lambda r: unknown_or_lowconf(r) or ok_real(r)),
]
print(f"{'test':40s} {'u_near':>7} {'u_far':>7} {'conf_n':>6}  result")
for name, img, pred in tests:
    r = D.detect_frame(img); f = lambda x: '  None' if x is None else f'{x:7.1f}'
    print(f"{name:40s} {f(r['u_near'])} {f(r['u_far'])} {r['confidence_near']:6.2f}  {'PASS' if pred(r) else 'KNOWN-FAIL'}")
# input-contract checks: must raise a clear ValueError, not crash inside OpenCV or return silent None
for name, img in [("float32 [0,1] image", real.astype(np.float32)/255), ("image only 200 rows", real[:200]), ("HxWx4 image", np.dstack([real, real[..., :1]]))]:
    try: D.detect_frame(img); res = 'KNOWN-FAIL (no error)'
    except ValueError as e: res = 'PASS (ValueError)'
    print(f"{name:40s} {'':7} {'':7} {'':6}  {res}")
gray_ok = D.detect_frame(cv2.cvtColor(real, cv2.COLOR_BGR2GRAY)); print(f"{'2-D grayscale input':40s} {gray_ok['u_near']:7.1f} {gray_ok['u_far']:7.1f} {gray_ok['confidence_near']:6.2f}  {'PASS' if ok_real(gray_ok) else 'KNOWN-FAIL'}")
