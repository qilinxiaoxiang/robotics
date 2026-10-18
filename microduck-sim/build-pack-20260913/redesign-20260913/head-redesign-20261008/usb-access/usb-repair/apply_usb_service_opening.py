"""Apply the pose-bound local USB aperture to an explicit current cap candidate.

Does not change published geometry. Full shell assembly and mounting tests must
still use the resulting cap, never a receipt for its predecessor.
"""
from pathlib import Path
import argparse,hashlib,json,os,sys,types
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1','Use run_bounded_cad.py'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cap',required=True,type=Path);p.add_argument('--spec',type=Path,default=D/'lowered-usb-service-opening-spec.json');p.add_argument('--output',type=Path,default=D/'head-cap-usb-service-world.stl');args=p.parse_args();hashes={}
def read(path):
    b=path.read_bytes();hashes[str(path.resolve())]=hashlib.sha256(b).hexdigest();return b
def man(mesh):
    assert mesh.is_watertight and mesh.is_volume,'Invalid input cap'
    result=mf.Manifold(mf.Mesh64(np.asarray(mesh.vertices,np.float64),np.asarray(mesh.faces,np.uint64)))
    assert result.status()==mf.Error.NoError and result.volume()>0
    return result
def placed_box(start,length,width,height,R):
    T=np.eye(4);T[:3,:3]=R;T[:3,3]=np.array(start)+R[:,2]*length/2
    return mf.Manifold.cube([width,height,length],True).transform(T[:3])
spec=json.loads(read(args.spec));posePath=Path(spec['poseFile']);assert hashlib.sha256(read(posePath)).hexdigest()==spec['poseSha256'],'Stale Pi pose'
pose=json.loads(posePath.read_text());R=np.column_stack([spec['widthAxis'],spec['heightAxis'],spec['axis']]);assert np.allclose(R.T@R,np.eye(3)) and np.linalg.det(R)>.999
read(args.cap);cap=man(trimesh.load(args.cap,force='mesh'));cut=placed_box(spec['cutStartMm'],spec['cutLengthMm'],spec['cutWidthMm'],spec['cutHeightMm'],R);new=cap-cut
assert new.status()==mf.Error.NoError,'Invalid subtraction'
m=new.to_mesh64();mesh=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=True)
assert mesh.is_watertight and len(new.decompose())==1,'USB cut disconnected the cap'
added=max(0.,float((new-cap).volume()));assert added<1e-6,'Unexpected exterior addition'
args.output.parent.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(D.parent.parent/'gpio-audio-repair'));from precision_mesh import export as preciseExport
exportEvidence=preciseExport(types.SimpleNamespace(np=np,tm=trimesh,mf=mf),new,args.output);read(args.output)
read(D.parent.parent/'gpio-audio-repair/precision_mesh.py')
plug=placed_box(pose['usbShoulderWorldMm'],25,8,18,R);rows=[]
trace=args.output.with_suffix('.entry.jsonl')
with trace.open('w') as f:
    for offset in np.arange(30,-.001,-.25):
        current=plug.translate(R[:,2]*offset);before=max(0.,float((current^cap).volume()));after=max(0.,float((current^new).volume()))
        row={'offsetMm':float(offset),'beforeMm3':before,'afterMm3':after};rows.append(row);f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
read(Path(__file__));read(trace)
report={'status':'LOCAL_APERTURE_AND_ENTRY_ONLY','sourceHashes':hashes,'removedVolumeMm3':float((cap^cut).volume()),'addedVolumeMm3':added,'exportReadback':exportEvidence,'watertight':bool(mesh.is_watertight),'bodies':len(new.decompose()),'entryStepMm':.25,'entrySamples':len(rows),'oldApertureNegativeReproduced':any(r['beforeMm3']>1e-5 for r in rows),'newEntryClear':all(r['afterMm3']<1e-5 for r in rows),'wholeHeadAccepted':False,'physicalFitVerified':False,'remaining':['Recheck complete shell closure with current internal geometry','Validate cable restraint, plug seating and full joint motion','Integrate final head and print review; deploy through Mac mini and inspect Chrome']}
args.output.with_suffix('.report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['removedVolumeMm3','entrySamples','oldApertureNegativeReproduced','newEntryClear','wholeHeadAccepted']}))
