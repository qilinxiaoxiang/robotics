#!/usr/bin/env python3
"""V1.9 candidate for the runtime jaw pose-cap table, and what it would clamp in the simulated policy rows.

Inputs: guide/firmware/pi/jaw_pose_caps.json (V1.8 parts) and the per-node first contacts of the V1.9 additions from
jaw_cap_v19.py (bracket and torso groups: clips, raised screw heads, bundle fixed on the bracket and on the torso) and
jaw_span_v19.py (free spans), saved as $EXT19_SCRATCH/jaw-cap-v19-<group>-comb.npy; the V1.8 screw heads (reference
category v18heads in ../checks/jaw-cap-v19.json), which the V1.8 table does not model.
Candidates (first contact per node = the smaller of the V1.8 table and the listed contacts):
  v19Additions             V1.9 clips, raised heads and wires;
  v19AdditionsScrewHeads   the same plus the V1.8 horn screw heads on the bracket and torso.
Each is written in the jaw_pose_caps.json schema to ../checks/jaw-pose-caps-<name>-candidate.json (not installed:
guide/firmware is owned by the integrator), and evaluated on the simulated policy rows and the three jaw-limit
release acceptances with extension-20261012-neck-audio/jaw-neck-check/scripts/policy_pose_caps.py, its table array
replaced by the candidate (its lookup self-check against the installed table is skipped for candidates; rows off the
grid fall back to the installed table, as reported in rowsOffGrid). The installed table is evaluated the same way
for comparison.
Usage: jaw_overlay_v19.py   Writes ../checks/jaw-overlay-v19.json and the two candidate tables.
"""
from __future__ import annotations

import copy
import json
import sys

import numpy as np

import ext_lib as E

sys.path.insert(0, str(E.EXT / 'jaw-neck-check' / 'scripts'))
import policy_pose_caps as PPC  # noqa: E402

TABLE = E.GUIDE / 'firmware' / 'pi' / 'jaw_pose_caps.json'
HI = 27.0


def nodes_index(axes):
    return {j: {round(float(v), 3): i for i, v in enumerate(a)} for j, a in axes.items()}


def main():
    d = json.loads(TABLE.read_text())
    J = d['joints']
    axes = {j: np.array([a0 + i * st for i in range(n)]) for j, (a0, st, n) in d['axes_deg'].items()}
    t = np.array([[[[HI if v is None else v for v in r] for r in y] for y in p] for p in d['first_contact_deg']], float)
    combs = {}
    for g in ('bracket', 'torso', 'spans'):
        p = E.SCRATCH / f'jaw-cap-v19-{g}-comb.npy'
        if not p.exists():
            raise SystemExit(f'missing {p}: run jaw_cap_v19.py / jaw_span_v19.py first')
        combs[g] = np.load(p)
    jc = json.loads((E.OUT / 'checks' / 'jaw-cap-v19.json').read_text())
    ix = nodes_index(axes)
    heads = np.full(t.shape, np.inf)
    for r in jc['bracket']['categories']['v18heads']['newContacts']:
        heads[:, :, ix['head_yaw'][r['head_yaw']], ix['head_roll'][r['head_roll']]] = np.minimum(
            heads[:, :, ix['head_yaw'][r['head_yaw']], ix['head_roll'][r['head_roll']]], r['firstContactDeg'])
    for r in jc['torso']['categories']['v18heads']['newContacts']:
        k = tuple(ix[j][r[j]] for j in J)
        heads[k] = min(heads[k], r['firstContactDeg'])
    add = np.minimum.reduce(list(combs.values()))
    cands = {'v19Additions': np.minimum(t, add), 'v19AdditionsScrewHeads': np.minimum(np.minimum(t, add), heads)}
    out = {'_method': __doc__.strip(), 'installedTable': str(TABLE), 'installedSha256': E.sha(TABLE),
           'jawCapCheckSha256': E.sha(E.OUT / 'checks' / 'jaw-cap-v19.json'), 'candidates': {}}
    flat0 = PPC.FLAT.copy()
    PPC_self_check = PPC.self_check
    out['installed'] = {'postures': PPC.postures(),
                        'acceptances': [PPC.acceptance(n) for n in ('limited-nominal-learned.json',
                                                                     'limited-household-pen.json',
                                                                     'limited-household-sock.json')]}
    PPC.self_check = lambda *a, **k: 0
    for name, c in cands.items():
        lowered = c < t - 1e-9
        cap = np.minimum(25.0, c - 2.0)
        cap0 = np.minimum(25.0, t - 2.0)
        rec = {'nodesLowered': int(lowered.sum()), 'minNewContactDeg': float(c[lowered].min()) if lowered.any() else None,
               'nodesCapBelow18_33': {'installed': int((cap0 < 18.33).sum()), 'candidate': int((cap < 18.33).sum())},
               'nodesHeldClosed': {'installed': int((cap0 < 5.0).sum()), 'candidate': int((cap < 5.0).sum())},
               'nodesFullCap25': {'installed': int((cap0 >= 25.0).sum()), 'candidate': int((cap >= 25.0).sum())}}
        PPC.FLAT = np.minimum(c, HI)               # null = clear_to_deg, as jaw_limits._load_pose_table
        assert PPC.FLAT.shape == flat0.shape
        rec['postures'] = PPC.postures()
        rec['acceptances'] = [PPC.acceptance(n) for n in ('limited-nominal-learned.json', 'limited-household-pen.json',
                                                          'limited-household-sock.json')]
        tab = copy.deepcopy(d)
        tab['description'] = (d['description'] + ' CANDIDATE for V1.9 (not installed): the smaller of the installed '
                              'table and the V1.9 contacts from guide/print/ext-v19/scripts/jaw_cap_v19.py and '
                              'jaw_span_v19.py' + (' plus the V1.8 horn screw heads' if 'ScrewHeads' in name else '') + '.')
        tab['sources'] = dict(d['sources'], **{'installed jaw_pose_caps.json': E.sha(TABLE),
                                               'ext-v19 checks/jaw-cap-v19.json': out['jawCapCheckSha256']})
        tab['first_contact_deg'] = [[[[None if v >= HI else round(float(v), 2) for v in r] for r in y] for y in p]
                                    for p in c]
        tab['summary'] = {'nodes': int(c.size), 'nodes_with_contact_below_clear': int((c < HI).sum()),
                          'min_contact_deg': float(c.min()), 'contact_below_7_deg_nodes': int((c < 7.0).sum())}
        path = E.OUT / 'checks' / f'jaw-pose-caps-{name}-candidate.json'
        path.write_text(json.dumps(tab, separators=(',', ':')))
        rec['path'] = str(path)
        rec['sha256'] = E.sha(path)
        out['candidates'][name] = rec
        p = rec['postures']
        print(name, {k: rec[k] for k in ('nodesLowered', 'minNewContactDeg', 'nodesCapBelow18_33', 'nodesHeldClosed')},
              'rows clamped', p['rowsClamped'], 'accepted', p['rowsClampedAccepted'], 'new', p['new']['rows'],
              [(a['file'], a['rowsClamped'], a['minMarginDeg']) for a in rec['acceptances']], flush=True)
    PPC.FLAT, PPC.self_check = flat0, PPC_self_check
    p = out['installed']['postures']
    print('installed rows clamped', p['rowsClamped'], 'accepted', p['rowsClampedAccepted'], 'new', p['new']['rows'],
          [(a['file'], a['rowsClamped'], a['minMarginDeg']) for a in out['installed']['acceptances']], flush=True)
    E.jdump(out, E.OUT / 'checks' / 'jaw-overlay-v19.json')


if __name__ == '__main__':
    main()
