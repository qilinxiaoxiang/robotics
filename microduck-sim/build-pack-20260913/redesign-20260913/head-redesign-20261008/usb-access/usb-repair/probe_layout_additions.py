"""Bounded neutral screening of one changed solid against the explicit current scene."""
from pathlib import Path
import argparse,base64,hashlib,json,os,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent
ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=['bridge','frontFlipUSB'],required=True);ap.add_argument('--mesh',type=Path);ap.add_argument('--pi-candidate',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
hashes={}
def read(p):
    p=Path(p);b=p.read_bytes();hashes[str(p.resolve())]=hashlib.sha256(b).hexdigest();return b
def solid(p):
    p=Path(p)
    if p.suffix=='.json':
        d=json.loads(read(p));m=tm.Trimesh(np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True)
    else:read(p);m=tm.load(p,force='mesh')
    s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)))
    assert s.status()==mf.Error.NoError and s.volume()>0,str(p)
    if not m.is_watertight:
        q=s.to_mesh64();normalized=tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=False)
        def digest(mesh):
            t=np.ascontiguousarray(mesh.vertices[mesh.faces],dtype=np.float64)
            v=np.sort(t.view('V24').reshape(-1,3),axis=1)
            return hashlib.sha256(np.sort(v.view('V72').reshape(-1)).tobytes()).hexdigest()
        assert digest(m)==digest(normalized) and normalized.is_watertight,str(p)
    return s
scene=json.loads(read(D/'positive-x225-obstacle-plan.json'))['obstacles']
if a.kind=='bridge':
    moving=solid(a.mesh or H/'cabling-release-20261008/neck-repair/flat-ribbon-sweep/arch2-bridge-world.stl')
else:
    # Preserves receiving specification: axial25, width8 in PCB-normal direction,
    # thickness18 along PCB edge. This candidate's USB socket exits downward.
    moving=mf.Manifold.cube([8,18,25],True).translate([68.09,-5.9113773,112-12.5])
    candidate=json.loads(read(H/'camera-ribbon-repair/occupancy-layout/frontFlip-0/report.json'))
    for r in candidate['parts']:
        scene[r['key']]={'source':str(H/r['mesh']),'bounds':np.asarray(r['boundsMm']).reshape(2,3).tolist()}
if a.pi_candidate:
    candidate=json.loads(read(a.pi_candidate))
    for r in candidate['parts']:
        scene[r['key']]={'source':str(H/r['mesh']),'bounds':np.asarray(r['boundsMm']).reshape(2,3).tolist()}
mb=np.asarray(moving.bounding_box()).reshape(2,3);rows=[]
for key,item in scene.items():
    if a.kind=='bridge' and key in ('head_bottom','jaw_support'):
        rows.append({'key':key,'notChecked':'Changed attachment owners under neck-agent structural check; no clearance claim from old source'});continue
    bb=np.asarray(item['bounds']);overlap=np.all(mb[0]<bb[1]) and np.all(bb[0]<mb[1])
    if not overlap:
        rows.append({'key':key,'separatedByBounds':True});continue
    sources=[Path(item['source'])]
    if key=='openrb':
        sources=sorted((D/'openrb-component-enclosures').glob('*.stl'));assert len(sources)==142
    for path in sources:
        ob=solid(path);obounds=np.asarray(ob.bounding_box()).reshape(2,3)
        if not(np.all(mb[0]<obounds[1]) and np.all(obounds[0]<mb[1])):continue
        inter=moving^ob;assert inter.status()==mf.Error.NoError
        v=max(0.,float(inter.volume()))
        rows.append({'key':key,'source':str(path),'overlapMm3':v,'gapMm':moving.min_gap(ob,5) if v<1e-6 else 0})
read(Path(__file__))
result={'kind':a.kind,'scope':'Neutral preliminary current-scene screen only; structural attachment contacts are reported, not waived. Old mounting features are retained in this inventory, final integrated geometry and assembly need subsequent checks.','bounds':mb.tolist(),'checks':rows,'hits':[r for r in rows if r.get('overlapMm3',0)>1e-5],'sourceHashes':hashes,'integrationReady':False}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'kind':a.kind,'hits':result['hits']}))
