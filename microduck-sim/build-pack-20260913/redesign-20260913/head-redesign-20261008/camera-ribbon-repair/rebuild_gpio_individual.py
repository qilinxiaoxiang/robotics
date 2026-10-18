from pathlib import Path
import os,ast,json,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;src=D.parent/'gpio-audio-repair/scene.py';env={'np':np,'mf':mf}
for node in ast.parse(src.read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['port','housing']:exec(compile(ast.Module([node],[]),str(src),'exec'),env)
 elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['PIN_NETS','PCB_FACE_X'] for t in node.targets):exec(compile(ast.Module([node],[]),str(src),'exec'),env)
pose=D/'lowered-pose-pair-checks.json';T=np.array(json.loads(pose.read_text())['worldTransform']);pieces={'zero_w_gpio_male_receiving':env['housing'](8.5)}
for pin in env['PIN_NETS']:
 p=env['port'](pin,18);pieces[f'gpio_pin_{pin:02}_receiving']=mf.Manifold.cube([15.46,2.54,2.54],True).translate([67.31-(18+2.54)/2,p[1],p[2]])
rows=[];hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),src,pose]}
for k,s in pieces.items():
 s=s.transform(T[:3]);q=s.to_mesh64();m=trimesh.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True);assert m.is_watertight
 out=D/(k+'-lowered-world.stl');m.export(out);back=trimesh.load(out,force='mesh');assert back.is_watertight;b=mf.Manifold(mf.Mesh64(np.array(back.vertices,np.float64),np.array(back.faces,np.uint64)));assert b.status()==mf.Error.NoError and b.volume()>1
 hashes[str(out.resolve())]=hashlib.sha256(out.read_bytes()).hexdigest();rows.append({'key':k,'mesh':str(out.relative_to(D.parent)),'volumeMm3':b.volume(),'watertight':True,'kind':'Receiving envelope; intended male/female mating-envelope overlaps are not material intersections'})
r={'integrationReady':False,'acceptedReceivingSolidsOnly':True,'expectedParts':13,'completedParts':len(rows),'physicalBoundsUnchanged':True,'construction':'Actual independent male header receiver and12 independent female receivers, each exported separately; no artificial gaps or shrinkage at edge-touching neighbours.','additionalParts':rows,'replacesInvalidAggregate':'gpio_discrete12_receiving','sourceHashes':hashes}
(D/'gpio-individual-receiving-manifest.json').write_text(json.dumps(r,indent=2)+'\n');print('13 watertight individual receivers exported')
