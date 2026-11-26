import sys,site; sys.path.append(site.getusersitepackages())
import cv2,numpy as np,os
V=['8e8ad85f2d4df331ad511bd5d12bdbc2','3e86b33c8e06c8027d5484ba722678f4','da680cfd53c783317d25a716dab60c04','bf4caa2c4f7551ab06cd63aa2f3a04f7','0a05a9f8f647548cf0ecf1d653e157fe']
out=os.path.dirname(os.path.abspath(__file__))
for i,f in enumerate(V):
    c=cv2.VideoCapture('C:/Users/mytwo/Downloads/'+f+'.mp4'); fps=c.get(5); F=[]
    while True:
        ok,im=c.read()
        if not ok: break
        h,w=im.shape[:2]; s=480/max(h,w); F.append(cv2.resize(im,(round(w*s),round(h*s)),interpolation=cv2.INTER_AREA))
    F=np.array(F); np.save(f'{out}/v{i}.npy',F)
    g=F.mean(3); d=np.abs(np.diff(g,axis=0)).mean((1,2)); med=np.median(d)
    cuts=[int(k+1) for k in np.where(d>max(8*med,12))[0]]
    print(i,F.shape,fps,'medDiff',round(med,2),'cuts',cuts)
    # grid preview frames
    for k in [0,len(F)//2]:
        im=F[k].copy(); H,W=im.shape[:2]
        for x in range(0,W,40): cv2.line(im,(x,0),(x,H),(0,255,255) if x%200==0 else (80,80,80),1)
        for y in range(0,H,40): cv2.line(im,(0,y),(W,y),(0,255,255) if y%200==0 else (80,80,80),1)
        cv2.imwrite(f'{out}/g{i}_{k}.jpg',im)
