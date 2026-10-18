from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;P=D.parent;O=P.parents[1]/'roof-wiring-stage/motor-wires';old=json.loads((O/'manifest.json').read_text());current=json.loads((P/'leg-local-manifest.json').read_text());routes=json.loads((O/'routes.json').read_text())['routes'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def solid(p):
 assert sha(Path(p['file']))==p['sha256'];m=trimesh.load_mesh(p['file']);assert m.is_volume;v=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(v.status())=='Error.NoError';return v
rows=[]
for rid,newid in [('ttl-03-02','ttl-03-02'),('ttl-07-08','ttl-08-07')]:
 route=next(r for r in routes if r['id']==rid);receipt=json.loads((O/f'{rid}-static.json').read_text());hits=[];count=0
 for p in old['parts']:
  if p.get('routeId')!=rid or p.get('kind')!='wire':continue
  a=solid(p);bb=np.array(p['expectedFinalBoundsMm'])
  for q in current['parts']:
   cb=np.array(q['expectedFinalBoundsMm'])
   if np.any(bb[1]<cb[0])or np.any(cb[1]<bb[0]):continue
   b=solid(q);c=a^b;count+=1;v=c.volume()
   if v>1e-7:hits.append({'oldShortWire':p['key'],'currentPart':q['key'],'volumeMm3':v,'bounds':list(c.bounding_box())})
 out={'id':newid,'legacyRoute':rid,'oldRouteFileSha256':sha(O/'routes.json'),'oldStaticReceiptSha256':sha(O/f'{rid}-static.json'),'oldNeutralReportZero':all(r['overlapMm3']<1e-7 for r in receipt['rows']),'modeledCenterlineLengthMm':route['centerlineLengthMm'],'nominalStockMm':180,'spareLengthModeled':route['spareLengthModeled'],'minimumSampledRadiusMm':route['minimumSampledCenterlineBendRadiusMm'],'oldNonWatertightMotorEvidence':any(not r.get('obstacleEvidence',{}).get('trimeshWatertight',True)for r in receipt['rows']),'exactPairsAgainstCurrentSixRoutes':count,'intersectionsWithCurrentSixRoutes':hits,'accepted':False};rows.append(out);print(newid,hits,flush=True)
(D/'existing-short-link-review.json').write_text(json.dumps({'sourceMasterSha256':sha(P/'leg-local-manifest.json'),'routes':rows,'scope':'Finite neutral delta screen; proves old short paths cannot be silently inherited as complete full-length cable acceptance. No frozen route changed.'},indent=2))
