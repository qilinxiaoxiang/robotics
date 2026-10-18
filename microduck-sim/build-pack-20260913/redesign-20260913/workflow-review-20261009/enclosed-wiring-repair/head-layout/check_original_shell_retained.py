"""Check closed original shell material remains; watertightness alone misses designed openings."""
import os,json,hashlib,argparse
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('candidate');ap.add_argument('--output',default='shell-retention-check.json');a=ap.parse_args()
def load(p):
 m=tm.load(p,force='mesh');s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)))
 assert s.status()==mf.Error.NoError,(str(p),s.status())
 return s
source=D/'native-cap-registered-world.stl';candidate=Path(a.candidate);base=load(source);part=load(candidate);missing=base-part
# Source STEP/STL export precision can leave negligible boundary slivers.
missing_volume=max(0,missing.volume());tolerance=.002
report={'passed':missing_volume<=tolerance,'scope':'Original crown and rear shell material retention, not complete populated closure','originalShell':str(source),'candidate':str(candidate),'originalVolumeMm3':base.volume(),'candidateVolumeMm3':part.volume(),'missingOriginalMaterialMm3':missing_volume,'numericalVolumeToleranceMm3':tolerance,'addedInternalMaterialMm3':max(0,(part-base).volume()),'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,candidate,Path(__file__)]},'physicalFitVerified':False}
(D/a.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
