from pathlib import Path
OUT=Path(__file__).resolve().parent;D=OUT.parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0].replace('D=Path(__file__).resolve().parent;R=', 'D=Path(__file__).resolve().parent.parent;R='))
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
rf=OUT/'report.json';base=json.loads(rf.read_text());delta=np.array(base['currentOpenRBWorldToCandidate']);delta[0,3]-=.5;T=np.array(base['nativeOpenRBToWorld']);T[0,3]-=.5
fixed={k:source(k)for k in ['torso_base','shell_left','shell_right']};p=H/'curved-head/openrb-curved-layout-world.stl';m=tm.load(p,force='mesh');v=m.vertices;f=m.faces;rv=f[:,[0,1,2]].ravel();cv=f[:,[1,2,0]].ravel();g=coo_matrix((np.ones(len(rv),np.int8),(rv,cv)),shape=(len(v),len(v))).tocsr();count,labels=connected_components(g,directed=False);fl=labels[f[:,0]];del g,rv,cv;records=[];checks=[]
for i in range(count):
 sub=m.submesh([np.where(fl==i)[0]],append=True);s=mf.Manifold(mf.Mesh64(np.asarray(sub.vertices,np.float64),np.asarray(sub.faces,np.uint64)));r={'component':i,'sourceFaces':len(sub.faces),'watertight':bool(sub.is_watertight),'volumePositive':bool(sub.is_volume),'status':str(s.status())};records.append(r)
 if s.status()!=mf.Error.NoError or not sub.is_volume:
  r['unresolvedExact']=True
  hullManifest=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';hr=json.loads(hullManifest.read_text())['components'][i];hs=load(hr['mesh']).transform(delta[:3]);r['conservativeCoverageSource']=str(hullManifest);r['fallbackChecks']=[]
  for fk,fo in fixed.items():
   fq=hs^fo;r['fallbackChecks'].append({'fixed':fk,'volumeMm3':max(0,fq.volume())})
  r['conservativeCoverageClear']=all(x['volumeMm3']<=1e-6 for x in r['fallbackChecks']);continue
 s=s.transform(delta[:3]);a=np.array(s.bounding_box()).reshape(2,3)
 for k,ob in fixed.items():
  b=np.array(ob.bounding_box()).reshape(2,3)
  if np.any(a[1]<b[0])or np.any(b[1]<a[0]):checks.append({'component':i,'fixed':k,'volumeMm3':0,'method':'aabb-separated'});continue
  q=s^ob;checks.append({'component':i,'fixed':k,'volumeMm3':max(0,q.volume()),'method':'exact-source-component-intersection','intersectionBounds':list(q.bounding_box())if q.volume()>1e-6 else None})
 del sub,s
# Void corridor is a query volume only; no subtraction from any print file.
box=mf.Manifold.cube([9,14,7]).translate([-30.77,-7,37]);corridor=[]
for k,ob in fixed.items():
 q=box^ob;r={'fixed':k,'materialInCorridorMm3':max(0,q.volume()),'bounds':list(q.bounding_box())if q.volume()>1e-6 else None};corridor.append(r)
plugchecks=[]
for row in base['meshes']:
 s=load(row['file']).translate([-.5,0,0])
 for k,ob in fixed.items():
  q=s^ob;plugchecks.append({'plug':row['key'],'fixed':k,'volumeMm3':max(0,q.volume()),'bounds':list(q.bounding_box())if q.volume()>1e-6 else None})
# 3 cross-sections through the local top corridor, no mesh changes.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="390" viewBox="0 0 1050 390">','<rect width="1050" height="390" fill="white"/>']
for n,z in enumerate([37,40,43]):
 xoff=350*n
 svg.append(f'<text x="{xoff+12}" y="22" font-family="sans-serif" font-size="16">Body XY section at Z={z} mm</text>')
 for k,color in [('shell_left','#83b4cc'),('shell_right','#aaa3ce')]:
  polys=fixed[k].slice(z).to_polygons()
  for poly in polys:
   pts=' '.join(f'{xoff+(float(x)+60)*2.5:.3f},{205-float(y)*2.5:.3f}'for x,y in poly);svg.append(f'<polygon points="{pts}" fill="{color}" fill-opacity=".42" stroke="{color}"/>')
 x=xoff+(-30.77+60)*2.5;y=205-7*2.5;svg.append(f'<rect x="{x}" y="{y}" width="22.5" height="35" fill="none" stroke="red" stroke-width="2"/><text x="{xoff+12}" y="362" font-family="sans-serif" font-size="12">Red: proposed query only; no shell cut</text>')
svg.append('</svg>');(OUT/'usb-corridor-sections.svg').write_text(''.join(svg))
out={'status':'SINGLE_POSE_DIAGNOSIS_NO_CUT','integrationReady':False,'nativeOpenRBToWorld':T.tolist(),'source':str(p),'sourceSha256':sha(p),'baseReportSha256':sha(rf),'sourceHashes':hashes,'componentCount':count,'exactComponents':records,'checks':checks,'hits':[q for q in checks if q['volumeMm3']>1e-6],'unresolvedExact':[q for q in records if q.get('unresolvedExact')],'corridorBounds':[[-30.77,-7,37],[-21.77,7,44]],'corridorMaterial':corridor,'shiftedPlugChecks':plugchecks,'noPrintFilesModified':True};(OUT/'shift-minus05-exact.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'hits':out['hits'],'unresolved':out['unresolvedExact'],'corridor':corridor,'plugHits':[x for x in plugchecks if x['volumeMm3']>1e-6]},indent=2))
