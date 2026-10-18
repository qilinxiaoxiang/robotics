from pathlib import Path
import json,numpy as np,trimesh
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent;W=D.parents[2];HD=W/'enclosed-wiring-repair/head-layout';inv=json.loads((HD/'audio-relocation/positive-y13-native/current-rigid-inventory.json').read_text())['parts']; report=json.loads((D/'horizontal-check.json').read_text()); sources=[]
for q in inv:
 n=q['id']
 if n in ['current_cap','current_amp','REFERENCE Pi current pi','REFERENCE MicroB photo receiving','REFERENCE fixed head jaw_support','REFERENCE fixed head motor13','REFERENCE fixed head motor14','REFERENCE fixed head motor15','REFERENCE current speaker']:
  m=trimesh.load_mesh(q['file']);m.apply_transform(q['worldTransform']);sources.append((n,m))
reg=json.loads((HD/'native-fusion-repair-inputs.json').read_text());r=json.loads((HD/'actual-openrb-components/micro-contact-proof.json').read_text());q=next(q for q in r['records']if q['index']==141);m=trimesh.load_mesh(q['mesh']);m.apply_transform(np.array(report['boardNativeToWorld'])@np.linalg.inv(reg['openrb']['nativeToCurrentWorld']));sources.append(('Proposed actual OpenRB PCB',m))
b=np.array(report['plugBoundsMm']['C_mould22']).reshape(2,3);m=trimesh.creation.box(b[1]-b[0]);m.apply_translation(b.mean(0));sources.append(('Complete USB-C mould',m))
colors=['#e3a21b','#a448a5','#189852','#c13039','#555555','#456fa8','#456fa8','#456fa8','#a8642d','#ed0000','#9b1645'];fig,axes=plt.subplots(1,3,figsize=(15,5))
for ax,(axis,value)in zip(axes,[(1,0),(1,-12),(0,25)]):
 ix=0 if axis==1 else 1
 for (name,m),color in zip(sources,colors):
  origin=np.zeros(3);origin[axis]=value;normal=np.zeros(3);normal[axis]=1;sec=m.section(plane_origin=origin,plane_normal=normal)
  if sec:
   for i,line in enumerate(sec.discrete):ax.plot(line[:,ix],line[:,2],color=color,lw=1.4,label=name.replace('REFERENCE fixed head ','').replace('REFERENCE Pi current ','') if i==0 else None)
 ax.set_title(('XZ at Y='if axis==1 else'YZ at X=')+str(value)+' mm');ax.set_xlabel(('X'if ix==0 else'Y')+' mm');ax.set_ylabel('Z mm');ax.set_ylim(100,160);ax.set_xlim((-40,85)if ix==0 else(-45,65));ax.set_aspect('equal');ax.grid(alpha=.25)
handles={}
for ax in axes:
 h,l=ax.get_legend_handles_labels();handles.update(zip(l,h))
fig.legend(handles.values(),handles.keys(),loc='lower center',ncol=4,fontsize=8);fig.suptitle('Rejected horizontal OpenRB: board crosses motor bodies; full plug crosses the closed head boundary',fontsize=11);fig.subplots_adjust(bottom=.24,top=.9,wspace=.25);fig.savefig(D/'horizontal-sections.png',dpi=140);fig.savefig(D/'horizontal-sections.svg')
