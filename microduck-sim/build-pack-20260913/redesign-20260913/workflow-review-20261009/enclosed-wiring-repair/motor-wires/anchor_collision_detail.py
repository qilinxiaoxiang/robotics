exec(__import__('pathlib').Path(__file__).with_name('check_retention_motion.py').read_text().split('rows=[]')[0])
P,_=fk({'right_knee':np.deg2rad(-90)});rows=[]
for src in ['motor3-case-tie','motor3-case-lock','motor3','right_thigh']:
 if src in ['motor3','right_thigh']:
  o=json.loads((O/(src+'.json')).read_text());m=trimesh.load_mesh(o['file']);m.apply_translation(o.get('importTranslationMm',[0,0,0]))
 else:m=trimesh.load_mesh(D/(src+'.stl'))
 a=solid(m)
 for key in ['right_ankle','right_foot']:
  o=json.loads((O/(key+'.json')).read_text());m=trimesh.load_mesh(o['file']);m.apply_translation(o.get('importTranslationMm',[0,0,0]));bb=body[key];m.apply_transform(P[bb]@np.linalg.inv(B[bb]));cut=a^solid(m);v=cut.volume();rows.append({'source':src,'obstacle':key,'overlapMm3':v,'bounds':list(cut.bounding_box()) if v>1e-7 else None})
print(json.dumps(rows,indent=2));(D/'anchor-collision-detail.json').write_text(json.dumps(rows,indent=2))
