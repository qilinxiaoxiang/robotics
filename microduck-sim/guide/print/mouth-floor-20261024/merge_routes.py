"""Merge routes_mouth_floor.json into content/routes.json: the V1.32 versions of the regenerated routes move to retired as
*_v132, the new ones replace them, and the _doc gains the 2026-10-24 paragraph. Run once after route_mouth_floor.py."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RJ = HERE.parents[1] / 'content/routes.json'
d = json.loads(RJ.read_text()); new = json.loads((HERE / 'routes_mouth_floor.json').read_text())['routes']
assert not any(f'{k}_v132' in d['retired'] for k in new), 'already merged'
for k, v in new.items():
    d['retired'][f'{k}_v132'] = d['routes'][k]; d['routes'][k] = v
d['_doc'] += (' 2026-10-24 mouth floor (Shawn, version 3; print/mouth-floor-20261024/route_mouth_floor.py, A* at 1.6 mm clearance):'
              ' the speaker lies face down in a pocket in the yellow floor and the amplifier stands between two rails on the floor'
              ' to its left (+y), on the same line x 64, terminal towards the speaker; the XIAO moved to the middle of the cap roof.'
              ' audio_spk_plus/minus run straight up from the speaker pads and across the 4 mm gap into the terminal; audio_amp_*'
              ' run from the input row up to the gather point and keep their D-025 tails; touch_pad_* end on the XIAO at the roof'
              ' centre; touch_a7z_* start there and keep their tails from the gather point. The old start and end points on the moved'
              ' boards are carried by the boards\' own rigid transforms. The V1.32 versions are in retired as *_v132.')
d['retired']['_doc'] += ' 2026-10-24: *_v132 are the V1.32 amplifier, speaker-lead and XIAO routes replaced by the mouth floor.'
RJ.write_text(json.dumps(d, indent=1) + '\n')
print('merged', len(new))
