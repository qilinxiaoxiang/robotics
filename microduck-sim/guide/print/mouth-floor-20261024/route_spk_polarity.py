"""Speaker leads by the real pad and terminal polarity (Shawn 2026-10-25: "那你顺手都改了吧").

route_mouth_floor.py put the speaker + pad at x 62.5 and the - pad at x 65.5; that order was carried from the D-025 box routes,
where it was chosen without a source, so the two leads ran parallel. The real parts, seen from above in the mouth floor
(speaker grille down, pad end towards +y; amplifier components up, terminal towards -y):
- speaker CMS-30204-18SP: the Same Sky drawing of the back (magnet side, pad tab at the bottom) marks + left, - right, so with
  the pads towards +y the + pad is at +x (65.5) and the - pad at -x (62.5)
  (build-pack-20260913/redesign-20260913/head-redesign-20261008/curved-head/sources/cms-30204-18x.pdf, page 2);
- amplifier Adafruit 3006: the silkscreen beside the terminal reads - left, + right seen from the header row, so with the
  terminal towards -y the + screw is at -x (62.25) and the - screw at +x (65.75) (bringup/parts/photos/max98357a_3006_top.jpg).
So + to + and - to - cross once in the 4 mm gap. The + lead crosses high (z 119.0), the - lead low (z 117.4), 1.6 mm apart.
The terminal ends are unchanged. Rewrites audio_spk_plus/minus in content/routes.json; the parallel versions move to retired as
*_v133par. Run once.
    python3 route_spk_polarity.py"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RJ = HERE.parents[1] / 'content/routes.json'
d = json.loads(RJ.read_text()); R = d['routes']
assert 'audio_spk_plus_v133par' not in d['retired'], 'already applied'
plus, minus = R['audio_spk_plus'], R['audio_spk_minus']
assert plus[0][0] < minus[0][0] and plus[-1][0] < minus[-1][0], 'expected the parallel V1.33 routes'
pad_lo, pad_hi = plus[0], minus[0]                     # x 62.5 and 65.5 at the speaker pad end
t_plus, t_minus = plus[-1], minus[-1]                  # terminal + at x 62.25, - at x 65.75 (entry ends, unchanged)
y_turn, z_entry = plus[-2][1], plus[-2][2]             # 13.1, 118.38: where the old routes turned into the terminal


def lead(pad, end, z_cross):
    return [pad, [pad[0], pad[1], z_cross], [end[0], y_turn, z_cross], [end[0], y_turn, z_entry], end]


new = {'audio_spk_plus': lead(pad_hi, t_plus, 119.0), 'audio_spk_minus': lead(pad_lo, t_minus, 117.4)}
for k, v in new.items():
    d['retired'][f'{k}_v133par'] = R[k]; R[k] = v
d['_doc'] += (' 2026-10-25 speaker polarity (print/mouth-floor-20261024/route_spk_polarity.py): the speaker + pad is at x 65.5'
              ' (Same Sky drawing) and the amplifier + screw at x 62.25 (Adafruit silkscreen), so audio_spk_plus/minus cross once'
              ' in the 4 mm gap, + high and - low; the parallel versions are in retired as *_v133par.')
d['retired']['_doc'] += ' 2026-10-25: *_v133par are the parallel V1.33 speaker leads, + and - pads swapped against the datasheet.'
RJ.write_text(json.dumps(d, indent=1) + '\n')
print(json.dumps(new))
