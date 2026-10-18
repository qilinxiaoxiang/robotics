from pathlib import Path
exec((Path(__file__).parent/'check_mouth_ring.py').read_text().split("report={'accepted'")[0])
R=ring(10.4,14.4,3.2,-39.6)+ring(12.4,16.4,.3,-39.9)+ring(10.4,16.4,.3,-36.4)
report={'accepted':False,'dimensionsMm':{'sleeveID':10.4,'sleeveOD':14.4,'sleeveThickness':3.2,'sleeveStartY':-39.6,'flangeOD':16.4,'flangeThickness':.3,'backFlangeID':12.4,'backFlangeStartY':-39.9,'frontFlangeStartY':-36.4},'static':{},'routes':{}}
fixed={'support':S,'jaw':J,'pad':P,'motor15':M,'V1_bottom':V}
for k,s in fixed.items():
 it=R^s;m=it.to_mesh64();v=np.asarray(m.vert_properties)[:,:3];report['static'][k]={'intersection':it.volume(),'gap':R.min_gap(s,1),'bounds':None if not len(v) else [v.min(0).tolist(),v.max(0).tolist()]}
exec('def scan('+(D/'check_mouth_ring.py').read_text().split('def scan(')[1].split("scan('ring_over")[0])
scan('ring_on_loose_jaw',{'ring':R},{'jaw':J},[0,30,0])
scan('support_down_onto_ring_jaw',{'support':S},{'jaw':J,'ring':R,'motor15':M,'V1_bottom':V},[0,0,30])
report['retention']={}
for sign in [-1,1]:
 hits=[]
 for d in np.linspace(0,.8,17):
  vols={k:(R.translate([0,sign*d,0])^s).volume() for k,s in fixed.items()};v={k:q for k,q in vols.items() if q>1e-7}
  if v:hits.append({'d':float(sign*d),'contacts':v})
 report['retention'][str(sign)]=hits[:2]
report['sourceHashes']={str(p.resolve()):c.sha(p) for p in inputs};c.save(D/'retained-ring-probe.json',report);print(json.dumps(report))
m=R.to_mesh64();t=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert t.is_watertight and t.is_volume; p=D/'retained-ring-candidate-world.stl';p.write_text(trimesh.exchange.stl.export_stl_ascii(t))
