from pathlib import Path
exec((Path(__file__).resolve().parent/'source_width_repack_probe.py').read_text().split('rows=[]')[0])
rows=[]
for dy in [0,-1,-2]:
 moving={k:baselineObs[k].translate([0,dy,0]) for k in ['pi','zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails']}
 hits={}
 for k,o in moving.items():
  for f,solid in baselineObs.items():
   if f in moving:continue
   q=o^solid;v=max(0,q.volume())
   if v>1e-5:hits[f'{k}--{f}']={'volume':v,'bounds':list(q.bounding_box())}
 rows.append({'translationYmm':dy,'collisions':hits});print(json.dumps(rows[-1]),flush=True)
(D/'pi-repack-static-probe.json').write_text(json.dumps({'rows':rows,'assemblyAcceptance':False,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*c.files.values(),c.G/'full-build-data.json',D/'pi_repack_static_probe.py',D/'source_width_repack_probe.py']},'mountNote':'Pi support pillars andattachment paths require redesign if board shifts; thisis candidate collisioncheck only.'},indent=2))
