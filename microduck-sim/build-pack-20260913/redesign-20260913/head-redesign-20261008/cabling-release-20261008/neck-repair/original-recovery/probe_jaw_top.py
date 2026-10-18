from pathlib import Path
exec((Path(__file__).parent/'check_mouth_ring.py').read_text().split("report={'accepted'")[0])
report={'routes':{}};exec('def scan('+(D/'check_mouth_ring.py').read_text().split('def scan(')[1].split("scan('ring_over")[0])
R=ring(10.4,14.4,2.6,-39.65);p=np.array([26.1,0,118.6146]);rot=lambda s,a:s.translate(-p).rotate([0,a,0]).translate(p)
fixed={'bottom':V,'motor14':source('motor14'),'yaw':source('head_yaw_link'),'ring_a':source('head_roll_ring_a'),'ring_b':source('head_roll_ring_b')}
for a in [60,90]:
 scan('jaw_at_'+str(a)+'_from_top',{'jaw':rot(J,a),'ring':R},fixed,[0,0,50])
 hits={}
 for a in np.linspace(90,0,181):
  for k,s in fixed.items():
   v=(rot(J,a)^s).volume()
   if v>1e-7:hits[k]=max(hits.get(k,0),v)
 report['swing_90_to_0']=hits
for x in [0,1]:scan('motor_from_top_offsetX_'+str(x),{'motor':M.translate([x,0,0])},{**fixed,'jaw':rot(J,90),'ring':R},[0,0,30])
c.save(D/'jaw-top-sequence.json',report);print(json.dumps(report))
