"""Bounded export simplification with explicit accumulated surface deviation."""
import argparse,json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,manifold3d as mf
D=Path(__file__).resolve().parent;O=D/'flat-yaw-sweep';a=argparse.ArgumentParser();a.add_argument('--part',required=True);o=a.parse_args();rp=O/f'{o.part}.json';sp=O/f'{o.part}.npz';r=json.loads(rp.read_text());assert c.sha(sp)==r['stateSha256'];z=np.load(sp);s=mf.Manifold(mf.Mesh64(z['vertices'],z['faces']));assert s.status()==mf.Error.NoError;before=s.volume();faces=len(z['faces']);tol=.001;s=s.as_original().simplify(tol);assert s.status()==mf.Error.NoError;m=s.to_mesh64();np.savez(sp,vertices=m.vert_properties[:,:3],faces=m.tri_verts);event={'completedPoseCount':len(r['completed']),'toleranceMm':tol,'facesBefore':faces,'facesAfter':len(m.tri_verts),'volumeDeltaMm3':s.volume()-before,'workerSha256':c.sha(Path(__file__))};r.setdefault('explicitSimplifications',[]).append(event);r['accumulatedSurfaceDeviationUpperBoundMm']=sum(x['toleranceMm'] for x in r['explicitSimplifications']);r['stateSha256']=c.sha(sp);c.save(rp,r);print(json.dumps(event))
