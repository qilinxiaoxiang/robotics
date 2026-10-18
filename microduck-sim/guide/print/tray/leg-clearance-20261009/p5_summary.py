import json, collections
G = json.load(open('p5-grid.json')); C = G['cols']; ix = {c: i for i, c in enumerate(C)}
W = json.load(open('walk-stats-adopted.json'))['stats']
def walk_ok(r):
    s = r[0]; return W[f'{s}_hip_yaw']['min'] - 1e-3 <= r[ix['yaw']] <= W[f'{s}_hip_yaw']['max'] + 1e-3 and W[f'{s}_hip_roll']['min'] - 1e-3 <= r[ix['roll']] <= W[f'{s}_hip_roll']['max'] + 1e-3
inst = ['power_support', 'shell_torso_base', 'other_torso']; orig = inst + ['upstream_battery_bay']
out = {}
for (side, knee) in sorted({(r[0], r[1]) for r in G['rows']}):
    R = [r for r in G['rows'] if r[0] == side and r[1] == knee]
    for scope, sel in (('walkYawRoll', [r for r in R if walk_ok(r)]), ('mjcfYawRoll', R)):
        tb = [r for r in sel if min(r[ix['tray']], r[ix['board']]) < 2.0]
        newI = [r for r in tb if min(r[ix[k]] for k in inst) >= 2.0]
        newO = [r for r in tb if min(r[ix[k]] for k in orig) >= 2.0]
        def first(L):
            if not L: return None
            r = min(L, key=lambda r: (r[ix['pitchBackwardAbs']], -abs(r[ix['yaw']])))
            return dict(pitch=r[ix['pitchBackwardAbs']], yaw=r[ix['yaw']], roll=r[ix['roll']], tray=r[ix['tray']], board=r[ix['board']], trayPart=r[ix['trayPart']], boardPart=r[ix['boardPart']],
                        installedMin=min(r[ix[k]] for k in inst), upstreamBay=r[ix['upstream_battery_bay']])
        # per-yaw first tray/board pitch, and first installed-part pitch (pose-wise), roll worst
        per = collections.defaultdict(lambda: [None, None])
        for r in sel:
            k = r[ix['yaw']]
            if min(r[ix['tray']], r[ix['board']]) < 2 and (per[k][0] is None or r[ix['pitchBackwardAbs']] < per[k][0]): per[k][0] = r[ix['pitchBackwardAbs']]
            if min(r[ix[q]] for q in inst) < 2 and (per[k][1] is None or r[ix['pitchBackwardAbs']] < per[k][1]): per[k][1] = r[ix['pitchBackwardAbs']]
        out[f'{side}/{knee}/{scope}'] = dict(poses=len(sel), firstTrayOrBoard=first(tb), firstNewVsInstalled=first(newI), firstNewVsOriginalDesign=first(newO),
                                            nNewVsInstalled=len(newI), perYawFirstTrayBoard_firstInstalled={str(k): v for k, v in sorted(per.items())})
for k, v in out.items():
    print(k, 'poses', v['poses'], '\n  firstTB', v['firstTrayOrBoard'], '\n  firstNEW(installed)', v['firstNewVsInstalled'], 'n', v['nNewVsInstalled'], '\n  firstNEW(orig design)', v['firstNewVsOriginalDesign'], '\n  perYaw', v['perYawFirstTrayBoard_firstInstalled'])
json.dump(out, open('p5-summary.json', 'w'), indent=1)
