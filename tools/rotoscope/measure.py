"""Fold relative ROI signals into one phase-aligned cycle each; writes roto_measure.json (periods, 48-sample waveforms in metres, amplitudes, lags).
Screen-to-body scale: px of a reference body length per clip (see SCALE). Waveforms are smoothed to 5 harmonics."""
import sys,site,os; sys.path.append(site.getusersitepackages())
import numpy as np,json
NB=48; D=os.path.dirname(os.path.abspath(__file__))
def hp(x,w):
    w=int(w)|1; return x-np.convolve(np.pad(x,(w,w),mode='edge'),np.ones(w)/w,'same')[w:-w]
def fold(x,P,off):
    t=np.arange(len(x)); b=((((t-off)/P)%1)*NB).astype(int); return np.array([x[b==k].mean() for k in range(NB)])
def harm(m,k=5):
    F=np.fft.rfft(m); F[k+1:]=0; return np.fft.irfft(F,len(m))
def refine(x,P0):
    best=None
    for P in np.linspace(P0*.95,P0*1.05,81):
        t=np.arange(len(x)); b=((((t)/P)%1)*NB).astype(int); xx=hp(x,P); m=np.array([xx[b==k].mean() for k in range(NB)]); s=np.mean([xx[b==k].var() for k in range(NB)])
        r=s/(m.var()+1e-12)
        if best is None or r<best[0]: best=(r,P)
    return best[1]
# clip: (video, seg, period-guess s, ref signal, scale px, metres, {name: (roiA, roiB or None, axis, sign)})
CLIPS={
 'twerk':(0,'D',.905,('Rc','anc',0),250,.40,{'pel_x':('Rc+Lc','anc',0,1),'pel_y':('Rc+Lc','anc',1,-1),'cheekL_y':('Lc','anc',1,-1),'cheekR_y':('Rc','anc',1,-1),'thigh_x':('thigh','anc',0,1),'back_x':('back','anc',0,1),'back_y':('back','anc',1,-1)}),
 'idle_sway':(1,'A',1.268,('pelv','anc',0),320,.72,{'pel_x':('pelv','anc',0,1),'pel_y':('pelv','anc',1,-1),'hipL_y':('Lh','anc',1,-1),'hipR_y':('Rh','anc',1,-1),'chest_x':('chest','anc',0,1),'head_x':('head','anc',0,1),'head_y':('head','anc',1,-1)}),
 'doggy':(2,'A',.504,('him','butt',0),265,.75,{'stroke':('him','butt',0,1),'her_x':('butt','anc',0,1),'torso_x':('torso','anc',0,1),'head_x':('head','anc',0,1),'head_y':('head','anc',1,-1)}),
 'press':(3,'A',.398,('his','butt',1),290,.40,{'stroke':('his','butt',1,-1),'her_y':('butt','anc',1,-1),'head_y':('head','anc',1,-1)}),
 'oral':(4,'A',.600,('face','shaft',0),125,.15,{'stroke':('face','shaft',0,1),'head_x':('face','anc',0,1),'head_y':('face','anc',1,-1),'chest_y':('chest','anc',1,-1)}),
}
out={}
for nm,(v,sn,P0,ref,px,met,sig) in CLIPS.items():
    T=json.load(open(f'{D}/trk{v}.json')); fps=T['fps']; S=T['segs'][sn]; P={k:np.array(p) for k,p in S['pos'].items()}
    def g(a,b,c):
        xa=sum(P[q][:,c] for q in a.split('+'))/len(a.split('+')); return xa-(P[b][:,c] if b else 0)
    Pf=refine(g(*ref),P0*fps); r=hp(g(*ref),Pf); m=harm(fold(r,Pf,0)); off=np.argmax(m)/NB*Pf
    k2m=met/px; W={}
    for s,(a,b,c,sg) in sig.items():
        f=harm(fold(hp(g(a,b,c),Pf),Pf,off))*sg*k2m; W[s]={'w':np.round(f,5).tolist(),'amp_m':round(float(np.ptp(f)/2),5),'peak_phase':round(float(np.argmax(f)/NB),3)}
    out[nm]={'video':v,'seg':sn,'phase0_frame':round(S['a']+off,2),'period_frames':round(Pf,3),'fps':fps,'period_s':round(Pf/fps,4),'cycles_used':round((S['b']-S['a'])/Pf,1),'scale':{'px':px,'metres':met},'sig':W}
    print(nm,'period',round(Pf/fps,3),{s:(round(w['amp_m']*100,2),w['peak_phase']) for s,w in W.items()})
json.dump(out,open(f'{D}/roto_measure.json','w'),indent=1)
