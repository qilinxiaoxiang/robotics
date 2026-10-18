from pathlib import Path
p=Path(__file__).with_name('build_jaw_access.py');ns={'__file__':str(p)};exec(p.read_text().split('fixed={k:solid(k)')[0],ns)
for k in ['main','arm']:
 s=ns[k]; print(k,[(a.volume(),a.bounding_box()) for a in s.decompose()])
for label,a,b in [('support-shell',ns['S'],ns['H']),('support-ring',ns['S'],ns['solid']('head_roll_ring_a'))]:
 print(label)
 for c in (a^b).decompose(): print(c.volume(),c.bounding_box())
for z in [1.25,1,.75,.5,.25,0]:
 it=ns['S'].translate([0,0,z])^ns['solid']('head_roll_ring_a');print('ring',z,it.volume(),it.bounding_box())
