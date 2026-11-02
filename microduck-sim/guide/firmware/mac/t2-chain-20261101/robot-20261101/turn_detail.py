"""One spin at 10 Hz: command, turn fed to the policy, head joints, actions, foot yaw, gyro."""
import json, math, sys
a, b = float(sys.argv[2]), float(sys.argv[3])
last = None
for l in open(sys.argv[1]):
    if not l.startswith('{'): continue
    try: r = json.loads(l)
    except ValueError: continue
    if not a <= r['t'] <= b: continue
    k = int(r['t'] * 10)
    if k == last: continue
    last = k
    c = r.get('cmd') or {}
    q, act = r['q'], r.get('action') or [0]*14
    print(f"{r['t']-a:5.1f} vth {c.get('vtheta')} turn {r.get('turn')} trim {r.get('yaw_trim')} hcmd {r.get('head_cmd')} neck {q[11]:+.2f} headp {q[10]:+.2f} aN {act[5]:+.2f} aH {act[6]:+.2f} yawz {math.degrees(r['gyro_body'][2]):+6.0f} gb {r['gb'][0]:+.2f} {r['gb'][1]:+.2f} bat {r.get('battery')} tq {r.get('torque')} ms {r.get('loop_ms')}")
