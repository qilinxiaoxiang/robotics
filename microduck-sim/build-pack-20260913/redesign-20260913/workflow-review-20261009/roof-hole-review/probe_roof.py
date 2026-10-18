import os,json,hashlib
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
D=Path(__file__).resolve().parent;R=D.parent.parent;H=R/'head-redesign-20261008';U=H/'usb-access/usb-repair'
paths={'native':H/'curved-head/community-curved-head-world.stl','current':H/'gpio-audio-repair/speaker-final-export/speaker-pilot-fix/cap-speaker-pilot-fixed-world.stl','spec':U/'positive-x225-service-opening-spec.json','pose':H/'camera-ribbon-repair/positive-x225-pose.json','spacer':H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();spec=json.loads(paths['spec'].read_text());pose=json.loads(paths['pose'].read_text());sp=json.loads(paths['spacer'].read_text());rot=np.column_stack([spec['widthAxis'],spec['heightAxis'],spec['axis']])
def box(start,w,h,l):
 T=np.column_stack([rot,np.array(start)+rot[:,2]*l/2]);return mf.Manifold.cube([w,h,l],True).transform(T)
cut=box(spec['cutStartMm'],9,19,55.5);plug=box(pose['usbShoulderWorldMm'],8,18,25);newplug=plug.translate(sp['translationFromPositiveX225Mm'])
report={'scope':'two cap meshes and final seated receiving solids only; no full scene','sourceHashes':{str(p):sha(p)for p in paths.values()},'connectorBoundary':'SC0727 25x18x8 declared receiving box, NOT measured/manufacturer moulding CAD','rows':[]};fig,axs=plt.subplots(1,2,figsize=(12,5))
for i,key in enumerate(['native','current']):
 m=tm.load(paths[key],force='mesh');s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError
 row={'cap':key,'watertight':bool(m.is_watertight),'volumeMm3':s.volume(),'materialInsideApertureCutMm3':(s^cut).volume()}
 for n,p in [('positiveX225SeatedPlug',plug),('currentSpacer2SeatedPlug',newplug)]:
  inter=s^p;row[n]={'overlapMm3':max(0,inter.volume()),'overlapBoundsMm':list(inter.bounding_box()) if inter.volume()>1e-8 else None}
 report['rows'].append(row)
 tri=m.triangles;mask=(m.face_normals[:,2]>.08)&(tri[:,:,2].min(axis=1)>130)
 axs[i].add_collection(PolyCollection(tri[mask,:,:2],facecolors='#ed983d',edgecolors='none'));axs[i].autoscale();axs[i].set_aspect('equal');axs[i].set_title(['Original community cap','Current cap: deliberate USB aperture'][i]);axs[i].set_xlabel('World X (mm)');axs[i].set_ylabel('World Y (mm)')
 # cut cross section near shell Z155
 c=np.array(spec['cutStartMm']);c=c+rot[:,2]*(155-c[2])/rot[2,2];corners=np.array([c+sx*4.5*rot[:,0]+sy*9.5*rot[:,1]for sx,sy in[(-1,-1),(1,-1),(1,1),(-1,1),(-1,-1)]])
 axs[i].plot(corners[:,0],corners[:,1],color='#ad1230',lw=1.5,label='9 x 19 mm cutter section');axs[i].legend(fontsize=8)
fig.tight_layout();fig.savefig(D/'roof-top-comparison.png',dpi=140);plt.close(fig)
a=tm.load(paths['native'],force='mesh');b=tm.load(paths['current'],force='mesh');ma=mf.Manifold(mf.Mesh64(np.asarray(a.vertices,np.float64),np.asarray(a.faces,np.uint64)));mb=mf.Manifold(mf.Mesh64(np.asarray(b.vertices,np.float64),np.asarray(b.faces,np.uint64)));roi=mf.Manifold.cube([40,45,25]).translate([50,-20,140]);missing=(ma-mb)^roi;report['combinedFrontRoofRemoval']={'volumeMm3':missing.volume(),'boundsMm':list(missing.bounding_box()),'meaning':'Original native material absent in front roof ROI; includes inherited earlier USB cut plus later pose-bound opening, not just 9x19 cutter'};report['scriptSha256']=sha(Path(__file__));report['visual']='roof-top-comparison.png';(D/'roof-probe.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['rows']))
