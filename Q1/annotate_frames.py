"""Q1(a) annotated frames. Marks come from image measurements only (no reference CSV).
Solid green = boundary visible at that row; dashed orange = hidden boundary placed with the
road-width model w(v)=1.054*v-16.3 (fitted on the CLEAR sequence images: see AUDIT_REPORT)."""
import zipfile, cv2, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
ZIP='SeDriCa_perception_starter_data.zip'; z=zipfile.ZipFile(ZIP)
W=lambda v:1.054*v-16.33
def load(seq,f): return cv2.imdecode(np.frombuffer(z.read(f'city/lane/{seq}/{f:03d}.png'),np.uint8),cv2.IMREAD_COLOR)
def comps(row,thr):
    m=row>thr;out=[];i=0
    while i<len(row):
        if m[i]:
            j=i
            while j+1<len(row) and m[j+1]:j+=1
            out.append(((i+j)/2,int(row[i:j+1].max())));i=j+1
        else:i+=1
    return out
cases=[('clear',12,'CLEAR f12: both boundaries visible'),
       ('shadow',6,'SHADOW f06: shadow hides LEFT boundary at far row'),
       ('missing',12,'MISSING f12: right boundary absent (far); false seam')]
fig,ax=plt.subplots(1,3,figsize=(18,5.2))
for a,(seq,f,title) in zip(ax,cases):
    bgr=load(seq,f); g=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY); a.imshow(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
    shadow=(g<60).astype(np.uint8)
    cs,_=cv2.findContours(shadow[90:,:].copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for c in cs:
        if cv2.contourArea(c)>3000: c=c[:,0,:]; a.plot(np.r_[c[:,0],c[0,0]],np.r_[c[:,1],c[0,1]]+90,'y:',lw=1.2)
    for v,name in [(260,'near'),(170,'far')]:
        c=comps(g[v],190); L=[p for p,_ in c if p<240]; R=[p for p,_ in c if p>=240]
        seam=[p for p,i in comps(g[v],150) if 150<i<=190]
        l=L[0] if L else None; r=R[0] if R else None
        if l is None and r is not None: l=r-W(v)
        if r is None and l is not None: r=l+W(v)
        for p,seen,side in [(l,bool(L),'L'),(r,bool(R),'R')]:
            if p is None: continue
            a.plot(p,v,'o',ms=9,mfc='none' if not seen else '#2ecc71',mec='#2ecc71' if seen else '#ff9800',mew=2)
        if l is not None and r is not None:
            a.plot((l+r)/2,v,'c*',ms=15); a.text((l+r)/2+8,v-6,f'{name} centre {(l+r)/2:.0f}',color='cyan',fontsize=9,weight='bold')
        else: a.text(120,v-6,f'{name}: no boundary visible -> unknown',color='red',fontsize=9,weight='bold')
        for p in seam: a.plot(p,v,'rx',ms=11,mew=3); a.text(p+6,v+16,f'false seam (I=183)',color='red',fontsize=8)
        a.axhline(v,color='w',ls='--',lw=.6,alpha=.5)
    a.set_title(title,fontsize=10,weight='bold'); a.set_xlabel('u (px)'); a.set_ylabel('v (px)')
fig.text(.5,.005,'green filled = boundary seen | orange hollow = hidden, placed via width model | red x = decoy | yellow dotted = shadow outline | cyan star = lane centre',ha='center',fontsize=9)
plt.tight_layout(rect=(0,.03,1,1)); plt.savefig('annotated_frames.png',dpi=110); print('saved')
