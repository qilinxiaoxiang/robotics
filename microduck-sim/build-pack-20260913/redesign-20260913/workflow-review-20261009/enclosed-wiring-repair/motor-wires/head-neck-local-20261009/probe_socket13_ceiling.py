from check_local import *
plan=json.loads((D/'plan.json').read_text());o=next(x for x in plan['obstacles']if x['key']=='REFERENCE fixed head head_yaw_link');m=load(o);tri=m.triangles;rows=[]
# Exact triangle-plane barycentric intersections for vertical rays; no voxel model.
for port in ['motor-13-socket-13','motor-13-socket-14']:
 p=plan['ports'][port]
 for slot in [-1,0,1]:
  q=np.array(p['shoulder'])+slot*2.5*np.array(p['width']);a=tri[:,0,:2];u=tri[:,1,:2]-a;v=tri[:,2,:2]-a;w=q[:2]-a;den=u[:,0]*v[:,1]-u[:,1]*v[:,0];valid=abs(den)>1e-12
  aa=np.zeros(len(den));bb=np.zeros(len(den));aa[valid]=(w[valid,0]*v[valid,1]-w[valid,1]*v[valid,0])/den[valid];bb[valid]=(u[valid,0]*w[valid,1]-u[valid,1]*w[valid,0])/den[valid];mask=valid&(aa>=-1e-8)&(bb>=-1e-8)&(aa+bb<=1+1e-8)
  zz=tri[:,0,2]+aa*(tri[:,1,2]-tri[:,0,2])+bb*(tri[:,2,2]-tri[:,0,2]);hits=sorted(set(round(float(z),7)for z in zz[mask]if z>q[2]-.0001));rows.append({'port':port,'slot':slot,'shoulder':q.tolist(),'verticalMaterialCrossingsZ':hits,'nearestMaterialAboveShoulderMm':hits[0]-q[2]if hits else None})
report={'sourceHashes':{o['file']:o['sha256'],str(D/'plan.json'):sha(D/'plan.json')},'rows':rows,'sourceLinkBoundsMm':m.bounds.tolist(),'interpretation':'Vertical ray measures printed material overhead only. It does not certify every alternative flexible bend or prove a print change necessary.'}
(D/'socket13-ceiling.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
