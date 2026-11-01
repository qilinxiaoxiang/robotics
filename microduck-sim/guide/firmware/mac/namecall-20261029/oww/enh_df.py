"""DeepFilterNet3 front end for the turn-noise trials (Mac mini, ~/.venvs/enh: torch 2.0.1, torchaudio 2.0.2, deepfilternet,
scipy, soundfile). Each ear (or MIX=1: the two-ear mix) is upsampled to 48 kHz, raised by PRE_DB (the duck's 2 m calls
sit near -60 dB, which DF treats as noise at their own level), enhanced, lowered again and brought back to 16 kHz.
  python enh_df.py IN_DIR OUT_DIR [PRE_DB]"""
import glob,os,sys,time,numpy as np,soundfile as sf,torch
from scipy.signal import resample_poly
from df.enhance import init_df,enhance
src,dst=sys.argv[1],sys.argv[2]; pre=float(sys.argv[3]) if len(sys.argv)>3 else 0.0; g=10**(pre/20); os.makedirs(dst,exist_ok=True)
model,state,_=init_df()   # DeepFilterNet3
torch.set_num_threads(1)
t_audio=t_cpu=0
for p in sorted(glob.glob(src+"/*.wav")):
    x,fs=sf.read(p)
    outs=[]
    chans=[x.mean(1)] if os.environ.get('MIX') else [x[:,c] for c in range(x.shape[1])]
    for xc in chans:
        y=(g*resample_poly(xc,3,1)).astype(np.float32)
        t=time.process_time(); e=enhance(model,state,torch.from_numpy(y)[None]).numpy()[0]; t_cpu+=time.process_time()-t
        outs.append(resample_poly(e,1,3)/g)
    t_audio+=len(x)/fs*len(chans)
    outs=outs*2 if len(outs)==1 else outs
    sf.write(os.path.join(dst,os.path.basename(p)),np.stack(outs,1),16000,subtype="PCM_16")
print("real-time factor (1 thread, per channel):",round(t_cpu/t_audio,3))
