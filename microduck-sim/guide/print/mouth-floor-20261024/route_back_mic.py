"""Routes for the optional third microphone on the back wall of the cap (2026-10-24, build_cap_xiao.py back seat).

- mic_b_harness: the back board's five wires (SCK, WS, SD, VDD, GND) as one bundle from the pads on its back face, out of the
  top of its horseshoe, along the inside of the cap to the head gather point over the exit (11.5, 19.5, 132), where SCK, WS,
  VDD and GND are joined into the existing microphone joints and SD goes on alone.
- mic_sd3_pin10: the back board's SD from the gather point down the neck on the amplifier BCLK tail (pin 12), ending beside
  A7Z header pin 10 (I2S0 DIN3, UART0 RX until the DIN3 overlay is tested; the plug stays off the pin, taped beside the header).
Same occupancy grid and A* as route_mouth_floor.py (executed from that file up to its routing loop, with the back board and
its foam ring added to the solids).
    /tmp/microduck-cad-venv/bin/python route_back_mic.py      (writes routes_back_mic.json)
"""
import json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
src = (HERE / 'route_mouth_floor.py').read_text().split('\nroutes = {}')[0]
tail_new = "'touch_xiao_tape': HERE / 'touch_xiao_tape_centre-world.stl'}"
assert tail_new in src
src = src.replace(tail_new, "'touch_xiao_tape': HERE / 'touch_xiao_tape_centre-world.stl', 'mic_back': HERE / 'mic_back-world.stl', "
                            "'mic_foam_back': HERE / 'mic_foam_back-world.stl'}")
a, b = src.index('amp_T, amp_res = fit('), src.index('meshes = {}')
src = src[:a] + src[b:]                      # the old-to-new board transforms are not needed here (world/ already holds the new boards)
g = {'__file__': str(HERE / 'route_mouth_floor.py'), '__name__': 'route_mouth_floor_prelude'}
exec(compile(src, 'route_mouth_floor.py (prelude)', 'exec'), g)

chk = json.loads((HERE / 'checks-cap.json').read_text())['backMic']
inner, ax = np.array(chk['innerHit']), np.array(chk['axisIntoCavity'])
up = np.array([0, 0, 1.0]) - ax * ax[2]; up /= np.linalg.norm(up)              # robot up in the board plane (the ring's open side)
pad = inner + ax * (chk['boardFaceAlongAxisMm'] + 1.0 + 0.6) + up * 3.4         # on the back face, above the chip, towards the top
lift = pad + up * 6.0 + ax * 1.0                                                 # out through the open top of the horseshoe
mid = g['astar'](lift, g['GATHER'])
harness = np.vstack([pad, lift, mid[1:-1], g['GATHER']])
R0 = g['R0']
bclk = np.array(R0['audio_amp_bclk_pin12'], float)
i = int(np.argmin(np.linalg.norm(bclk - g['GATHER'], axis=1))); assert np.linalg.norm(bclk[i] - g['GATHER']) < 1e-6
sd = bclk[i:].copy()
pin12_y = bclk[-1, 1]; assert abs(pin12_y + 11.43) < 1e-6                         # pin 12; pin 10 is the next even pin, 2.54 mm towards -y
sd[-3:, 1] = pin12_y - 2.54
out = {'mic_b_harness': np.round(harness, 2).tolist(), 'mic_sd3_pin10': np.round(sd, 2).tolist()}
L = {k: round(float(np.linalg.norm(np.diff(np.array(v), axis=0), axis=1).sum()), 1) for k, v in out.items()}
(HERE / 'routes_back_mic.json').write_text(json.dumps({'_doc': __doc__.strip().splitlines()[0], 'clearMm': g['CLEAR'], 'lengthsMm': L, 'routes': out}, indent=1))
print(L, out['mic_b_harness'][:3], out['mic_sd3_pin10'][-3:])
