from pathlib import Path
import json,hashlib,sys,struct,io,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
side,i,j=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]);report=D/f'hip-{side}-shared-spline.json';r=json.loads(report.read_text());assert r['passedStatic'];p=r['rows'][0];assert sha(p['file'])==p['sha256'];data=Path(p['file']).read_bytes();n=struct.unpack('<I',data[80:84])[0];assert n%3==0 and len(data)==84+n*50;n//=3
solids=[]
for k in [i,j]:
 b=data[:80]+struct.pack('<I',n)+data[84+k*n*50:84+(k+1)*n*50];m=trimesh.load_mesh(io.BytesIO(b),file_type='stl',process=True);assert m.is_volume
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert a.status()==mf.Error.NoError;solids.append(a)
c=solids[0]^solids[1];v=c.volume();out={'passed':v<1e-7,'side':side,'strandA':i,'strandB':j,'overlapMm3':v,'bounds':list(c.bounding_box())if v>1e-7 else None,'sourceHashes':{str(report):sha(report),p['file']:p['sha256'],str(Path(__file__)):sha(__file__)}};(D/f'shared-pair-{side}-{i}-{j}.json').write_text(json.dumps(out,indent=2));print(out);assert out['passed']
