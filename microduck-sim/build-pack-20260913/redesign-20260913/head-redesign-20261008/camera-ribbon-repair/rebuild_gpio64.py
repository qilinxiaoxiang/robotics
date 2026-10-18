from pathlib import Path
import os,ast,json,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;src=D.parent/'gpio-audio-repair/scene.py';env={'np':np,'mf':mf}
for node in ast.parse(src.read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['port','housing','discrete_header']:exec(compile(ast.Module([node],[]),str(src),'exec'),env)
 elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['PIN_NETS','PCB_FACE_X'] for t in node.targets):exec(compile(ast.Module([node],[]),str(src),'exec'),env)
pose=D/'lowered-pose-pair-checks.json';T=np.array(json.loads(pose.read_text())['worldTransform']);pieces=[mf.Manifold.cube([8500,52000,7000]).translate([-8500,-1870,-2230])]
for pin in env['PIN_NETS']:
 pieces.append(mf.Manifold.cube([15460,2540,2540]).translate([-18000,2540*((pin-1)//2)-1270,(2540 if pin%2==0 else 0)-1270]))
# Exact decimal dimensions on an integer micron lattice; no arbitrary overlap/fattening.
solid=mf.Manifold.batch_boolean(pieces,mf.OpType.Add).scale([.001,.001,.001]).translate([67.31,-24.141,118.2796]).transform(T[:3]);assert solid.status()==mf.Error.NoError and solid.volume()>3000
q=solid.to_mesh64();m=trimesh.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True);assert m.is_watertight
out=D/'gpio-discrete12-lowered-precise-world.stl'
with out.open('w') as f:
 f.write('solid gpio\n')
 for tri in m.triangles:
  f.write('facet normal 0 0 0\nouter loop\n')
  for xyz in tri:f.write('vertex '+' '.join(repr(float(z)) for z in xyz)+'\n')
  f.write('endloop\nendfacet\n')
 f.write('endsolid gpio\n')
back=trimesh.load(out,force='mesh');assert back.is_watertight
b=mf.Manifold(mf.Mesh64(np.array(back.vertices,np.float64),np.array(back.faces,np.uint64)));assert b.status()==mf.Error.NoError
oldp=D/'gpio_discrete12_receiving-lowered-pose-world.stl';old=trimesh.load(oldp,force='mesh');oldmf=mf.Manifold(mf.Mesh(np.array(old.vertices,np.float32),np.array(old.faces,np.uint32)))
r={'acceptedReceivingSolidOnly':True,'physicalConnectorBoundsUnchanged':True,'construction':'Same exact source decimal bounds evaluated on an integer-micron lattice before rigid transform; no expanded receivers or holes filled','volumeMm3':solid.volume(),'bodies':len(solid.decompose()),'watertight':bool(back.is_watertight),'roundtripDifferenceMm3':max(0,(b-solid).volume())+max(0,(solid-b).volume()),'oldWatertight':bool(old.is_watertight),'oldManifoldStatus':str(oldmf.status()),'oldManifoldVolumeMm3':oldmf.volume(),'sourceHashes':{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),src,pose,oldp,out]}}
(D/'gpio-precise-rebuild.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
