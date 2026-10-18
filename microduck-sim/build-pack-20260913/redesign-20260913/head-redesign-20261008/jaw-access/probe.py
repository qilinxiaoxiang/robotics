from pathlib import Path
p=Path(__file__).resolve().parent.parent/'head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns);globals().update(ns)
S=solid('jaw_support');H=solid('head_bottom');J={k:solid(k) for k in ['jaw_frame','lower_pad']};M=solid('motor15');sweep=(J['jaw_frame']+J['lower_pad']).minkowski_sum(box([-.2,-.2,-.2],[.2,32.2,.2]))
for i,m in enumerate((H^sweep).decompose()):print('shellcutcomponent',i,m.volume(),m.bounding_box(),flush=True)
for y in [-30,-20,-14,-10]:
 keep=S^box([-100,-100,0],[150,y-.1,250]);main=S-box([-100,-100,0],[150,y+.1,250])
 print('split',y,'keep',keep.volume(),len(keep.decompose()),'main',len(main.decompose()),flush=True)
 print('jaw',samples(J,{'main':main,'motor':M},[0,32,0],step=1)['peakContactsMm3'],flush=True)
 print('keeper',samples({'keeper':keep},{'main':main,'motor':M,**J},[0,-32,0],step=1)['peakContactsMm3'],flush=True)
