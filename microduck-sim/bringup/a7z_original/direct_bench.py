"""Wiring view for A7Z-PINS-ORIGINAL.html: the current saddle wiring bench (../a7z/a7z_bench.py) without the microphones
and the breadboard, so the amplifier and touch board plug straight into the A7Z. Amplifier BCLK goes to pin 12, LRC to
pin 35 and the XIAO 3V3 to pin 17, each on its own lead. Wire colours are the as-built ones (Shawn, 2026-10-26)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / 'a7z'))
import a7z_bench as AB  # noqa: E402

DROP_MODULES = {'micl', 'micr', 'micb', 'bb'}
DROP_WIRES = {'gsck', 'gws', 'gvdd'}
DIRECT = {  # wire id: (to, label, note)
    'abclk': ('a7z.p12', '白：功放 BCLK → A7Z 12 号针', '小旗 12，一整根带母头的线，直接插 12 号针。'),
    'alrc': ('a7z.p35', '紫：功放 LRC → A7Z 35 号针', '小旗 35，一整根带母头的线，直接插 35 号针。'),
    't3v3': ('a7z.p17', '红：触摸板 3V3 → A7Z 17 号针（3.3 V）', '小旗 17，一整根带母头的线，直接插 17 号针。'),
}
ROLE = {12: 'I2S0 BCLK：功放 BCLK（白）', 17: '3.3 V：触摸板 3V3（红）', 35: 'I2S0 LRCK：功放 LRC（紫）',
        8: '调试串口 TX：空着', 10: '调试串口 RX：空着'}

_bench = AB.bench


def bench() -> dict:
    for n in (34, 38):
        AB.A7Z_ROLE.pop(n, None)
    AB.A7Z_ROLE.update(ROLE)
    b = _bench()
    b['modules'] = [m for m in b['modules'] if m['id'] not in DROP_MODULES]
    b['placements'] = [p for p in b['placements'] if p['module'] not in DROP_MODULES]
    b['groups'] = [g for g in b['groups'] if g['id'] not in ('mic', 'micb')]
    wires = []
    for w in b['wires']:
        if w['group'] in ('mic', 'micb') or w['id'] in DROP_WIRES:
            continue
        if w['id'] in DIRECT:
            w = dict(w, to=DIRECT[w['id']][0], label=DIRECT[w['id']][1], note=DIRECT[w['id']][2])
        wires.append(w)
    b['wires'] = wires
    return b


AB.bench = bench
AB.PICKS = [(m, t) for m, t in AB.PICKS if m not in DROP_MODULES]
html = AB.html

if __name__ == '__main__':
    b = bench()
    print([m['id'] for m in b['modules']], [(w['id'], w['to']) for w in b['wires']])
