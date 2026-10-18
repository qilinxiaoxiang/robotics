from pathlib import Path
exec((Path(__file__).parent/'check_mouth_ring.py').read_text().split("report={'accepted'")[0])
report={'routes':{}};exec('def scan('+(D/'check_mouth_ring.py').read_text().split('def scan(')[1].split("scan('ring_over")[0])
R=ring(10.4,14.4,2.6,-39.65);p=np.array([26.1,0,118.6146]);rot=lambda s:s.translate(-p).rotate([0,30,0]).translate(p)
fixed={'bottom':V,'motor14':source('motor14'),'yaw':source('head_yaw_link'),'ring_a':source('head_roll_ring_a'),'ring_b':source('head_roll_ring_b')}
for v in [[0,32,0],[0,-32,0],[0,0,-32]]:scan('open_jaw_ring_'+str(v),{'jaw':rot(J),'ring':rot(R)},fixed,v)
scan('motor_side_after_open_jaw',{'motor':M},{**fixed,'jaw':rot(J),'ring':rot(R)},[0,32,0])
scan('original_support_from_top',{'support':S},{**fixed,'jaw':rot(J),'ring':rot(R),'motor':M},[0,0,30])
c.save(D/'open-jaw-sequence.json',report);print(json.dumps(report))
