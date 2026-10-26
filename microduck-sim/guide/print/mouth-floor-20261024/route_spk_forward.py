"""Speaker leads after the speaker moved forward (Shawn 2026-10-25: "发声孔移到贴住前面板的位置", "把功放的限位去掉").

build_mouth_floor.py now puts the speaker SPK_FWD = 4.5 mm ahead of the amplifier line (centre x 68.5, the amplifier stays on
x 64), so both speaker pads move 4.5 mm in +x: + pad x 70.0, - pad x 67.0 (route_spk_polarity.py keeps the datasheet sides).
The pad points follow the speaker top (checks-floor.json speaker.topZ + 0.3, the floor tilt included); the crossing levels
(+ at z 119.0, - at z 117.4) and the terminal ends are unchanged, so the + lead now runs 7.75 mm across the gap and the - lead
1.25 mm. Rewrites audio_spk_plus/minus in content/routes.json; the previous versions move to retired as *_v133cross. Run once.
    python3 route_spk_forward.py"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RJ = HERE.parents[1] / 'content/routes.json'
ck = json.loads((HERE / 'checks-floor.json').read_text())
fwd = ck['params']['SPK_FWD']; z_pad = round(ck['speaker']['topZ'] + 0.3, 2)
d = json.loads(RJ.read_text()); R = d['routes']
assert 'audio_spk_plus_v133cross' not in d['retired'], 'already applied'
new = {}
for k in ('audio_spk_plus', 'audio_spk_minus'):
    r = R[k]; assert r[0][:2] == r[1][:2], r                     # vertical rise off the pad, then the crossing run
    new[k] = [[round(r[0][0] + fwd, 2), r[0][1], z_pad], [round(r[1][0] + fwd, 2), r[1][1], r[1][2]]] + r[2:]
    d['retired'][f'{k}_v133cross'] = r; R[k] = new[k]
d['_doc'] += (f' 2026-10-25 speaker forward (print/mouth-floor-20261024/route_spk_forward.py): the speaker sits {fwd} mm ahead of'
              ' the amplifier line, so both pad ends move with it; the crossing levels and terminal ends are unchanged; the previous'
              ' versions are in retired as *_v133cross.')
d['retired']['_doc'] += ' 2026-10-25: *_v133cross are the crossing speaker leads with the speaker on the amplifier line (x 64).'
RJ.write_text(json.dumps(d, indent=1) + '\n')
print(json.dumps(new))
