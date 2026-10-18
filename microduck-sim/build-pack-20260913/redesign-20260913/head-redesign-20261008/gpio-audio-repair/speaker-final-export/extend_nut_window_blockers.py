from pathlib import Path
import os,json,hashlib,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;O=D/'orange-hole-blockers';sys.path.insert(0,str(D.parent));import precision_mesh as pm
class C:pass
c=C();c.tm=tm;c.np=np;c.mf=mf
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();a=json.loads((O/'repaired-cap-manifest.json').read_text());updates=[]
for row in a['blockers']:
 if row['name']not in('E-openrb-01','E-openrb-03'):continue
 source=Path(row['worldMesh']);s=pm.load(c,source);axis=np.array(row['worldAxis']);p=np.array(row['worldOrigin']);T=tm.geometry.align_vectors([0,0,1],axis);T[:3,3]=p+axis*4.1
 # Exact source side-entry nut window8x4.3x1.8, with .2 local margin on each side.
 window=mf.Manifold.cube([8.4,4.7,2.2],True).transform(T[:3,:]);u=s+window
 out=O/(row['name']+'-nut-window-support-blocker-world.stl');info=pm.export(c,u,out);row.update(worldMesh=str(out),worldMeshSha256=sha(out),positiveVolumeMm3=float(u.volume()),nutWindow={'originalDimensionsMm':[8,4.3,1.8],'blockerDimensionsMm':[8.4,4.7,2.2],'axisCenterMm':4.1,'worldTransform':T.tolist(),'reason':'Native tree support remained in side nut-window ceiling, then crossed otherwise blocked bolt bore.'})
 updates.append({'name':row['name'],'originalModifierSha256':sha(source),'modifiedModifierSha256':sha(out),'readback':info})
a['modifierRevision']=2;a['modifierRevisionEvidence']={'baselineGcodeSha256':'1f881ffc69408a80094e620f37aafebdb0332cdd5787aa075d9f38b875ffba83','remainingCoreCounts':{'E-openrb-01':46,'E-openrb-03':46},'remainingAlongAxisMm':[4.349,5.135],'sourceRecipe':'curved-head/build_mounts.py exact lateral slot8x4.3x1.8 at seat+axis2.5; seat=pcbHoleCenter+axis1.6','updates':updates};(O/'repaired-cap-manifest-v2.json').write_text(json.dumps(a,indent=2)+'\n');print(O/'repaired-cap-manifest-v2.json')
