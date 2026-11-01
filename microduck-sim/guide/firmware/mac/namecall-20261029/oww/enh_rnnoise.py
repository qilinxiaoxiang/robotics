"""RNNoise on each ear of every 16 kHz 2-ch clip, with a pre-gain (dB) undone after."""
import glob,os,sys,time,numpy as np,soundfile as sf
from scipy.signal import resample_poly
from pyrnnoise import RNNoise
src,dst,pre=sys.argv[1],sys.argv[2],float(sys.argv[3]); os.makedirs(dst,exist_ok=True); g=10**(pre/20)
tc=ta=0
for p in sorted(glob.glob(src+"/*.wav")):
    x,fs=sf.read(p); outs=[]
    for c in range(x.shape[1]):
        y=np.clip(g*resample_poly(x[:,c],3,1),-1,1); y=(y*32767).astype(np.int16)
        r=RNNoise(48000); t=time.process_time()
        o=[]
        for prob,fr in r.denoise_chunk(y[None,:]):
            o.append(np.asarray(fr).reshape(-1))
        tc+=time.process_time()-t
        e=np.concatenate(o).astype(float)/32767/g
        e=np.pad(e,(0,max(0,len(y)-len(e))))[:len(y)]
        outs.append(resample_poly(e,1,3))
    ta+=len(x)/fs*x.shape[1]
    sf.write(os.path.join(dst,os.path.basename(p)),np.stack(outs,1),16000,subtype="PCM_16")
print("rnnoise real-time factor per channel:",round(tc/ta,4))
