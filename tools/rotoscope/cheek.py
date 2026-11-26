import sys,site,os; sys.path.append(site.getusersitepackages()); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import numpy as np,json,track
track.CFG[0]={'fps':60,'segs':{'A':(5,220,{'Lt':(110,130,170,180),'Rt':(260,140,320,190),'Lb':(100,200,180,250),'Rb':(250,210,330,260),'anc':(0,0,80,100)}),
 'B':(285,515,{'Lt':(60,130,120,180),'Rt':(220,110,290,160),'Lb':(50,200,130,250),'Rb':(200,190,280,240),'anc':(400,0,480,80)}),
 'D':(880,1160,{'Lt':(200,120,250,170),'Rt':(350,110,400,160),'Lb':(190,200,260,250),'Rb':(330,200,410,250),'anc':(0,0,80,100)})}}
import shutil; track.run(0); shutil.move('trk0.json','trk0_cheek.json')
T=json.load(open('trk0_cheek.json')); P0=54.0
def hp(x,w): w=int(w)|1; return x-np.convolve(np.pad(x,(w,w),mode='edge'),np.ones(w)/w,'same')[w:-w]
for sn,px in (('A',230),('B',280),('D',250)):
    S=T['segs'][sn]; P={k:np.array(v) for k,v in S['pos'].items()}; a=P.pop('anc'); P={k:v-(a-a[0]) for k,v in P.items()}
    d=hp(P['Lt'][:,1]-P['Rt'][:,1],P0); sep=np.mean(P['Rt'][:,0]-P['Lt'][:,0])
    dl=hp(P['Lt'][:,1],P0); dr=hp(P['Rt'][:,1],P0); c=np.corrcoef(dl,dr)[0,1]
    amp=np.percentile(np.abs(d),95)
    print(sn,'L-R dy amp95 %.1fpx sep %.0fpx -> roll %.1f deg; L/R y amp95 %.1f %.1f px (=%.1f %.1f cm); corr(L,R) %.2f'%(amp,sep,np.degrees(np.arctan(amp/sep)),np.percentile(np.abs(dl),95),np.percentile(np.abs(dr),95),np.percentile(np.abs(dl),95)/px*40,np.percentile(np.abs(dr),95)/px*40,c))
