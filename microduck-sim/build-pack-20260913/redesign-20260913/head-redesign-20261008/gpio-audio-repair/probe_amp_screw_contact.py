import json
from pathlib import Path
import unify_amp_cap as u
u.core.guarded_import();c=u.core;af=u.D/'amp16z2-placement-world.stl';sf=u.OUT/'amp-new-two-screws-world.stl';amp=u.load(af);screws=u.load(sf);pieces=screws.decompose();rows=[]
for i,s in enumerate(pieces):
 contact=s^amp;rows.append({'index':i,'screwBoundsMm':list(s.bounding_box()),'intersection':u.describe_solid(contact)})
report={'rows':rows,'inputHashes':u.inputs([Path(__file__),af,sf]),'integrationReady':False};c.atomic_json(u.OUT/'screw-pcb-contact.json',report);print(json.dumps(rows))
