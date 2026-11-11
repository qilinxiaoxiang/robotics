"""Print-gate status of FlightPack-D1 (robotics/AGENTS.md: release only after run_gate.py passes on guide data that includes
the flight pack). Reads the guide tree only; never edits it. When guide/data/guide-data.json names every flight-pack part and
guide/print/world holds an STL for each, runs guide/content/interference-audit/run_gate.py (its four jobs run under the bounded
runner) and records the receipt; otherwise records exactly what is missing. Writes STATUS.json next to the manifest.

    /tmp/microduck-cad-venv/bin/python scripts/gate_status.py [--no-run]
"""
import hashlib, json, subprocess, sys, datetime
from pathlib import Path

REL = Path(__file__).resolve().parents[1]
CAD = REL.parents[1]
SIM = CAD.parents[2]
GUIDE = SIM / 'guide'
GATE = GUIDE / 'content/interference-audit'
PY = '/tmp/microduck-cad-venv/bin/python'
PARTS = ['wing_plate', 'tray_L', 'tray_R', 'fc_bracket', 'nacelle_inner_L', 'nacelle_outer_L', 'nacelle_inner_R', 'nacelle_outer_R']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ACCEPTED = CAD / 'checks/accepted.json'


def exception_covers(rec: Path):
    """Shawn's exception A-GATE-BPHATCH (cad/checks/accepted.json, 2026-11-11 '记为例外放行'): the gate may fail only on the
    steps stage, and only with exactly the recorded step collisions (same step, moving part and obstacle, volume no more
    than recorded + tolerance), nothing drawn before it is present. Anything else, or any other failing stage, fails."""
    acc = next(a for a in json.loads(ACCEPTED.read_text())['accepted'] if a['id'] == 'A-GATE-BPHATCH')
    ex = acc['gate_exception']
    if ex['release'] != 'FlightPack-D1' or not rec.exists():
        return False, dict(id=acc['id'], covered=False, why='exception is for another release or no receipt')
    r = json.loads(rec.read_text())
    bad_stages = [k for k, v in r['checks'].items() if not v.get('passed') and k != 'steps']
    steps = json.loads((GATE / 'steps-raw.json').read_text())['steps']
    found = [dict(step=s['step'], moving=c.get('moving'), obstacle=c['obstacle'], maxExcessVolumeMm3=c['maxExcessVolumeMm3'])
             for s in steps for c in (s.get('pathCollisions') or [])]
    premature = sum(len(s.get('drawnButNotPresent') or []) for s in steps)
    want = {(c['step'], c['moving'], c['obstacle']): c['maxExcessVolumeMm3'] for c in ex['step_collisions']}
    got = {(c['step'], c['moving'], c['obstacle']): c['maxExcessVolumeMm3'] for c in found}
    unexpected = [c for c in found if (c['step'], c['moving'], c['obstacle']) not in want
                  or c['maxExcessVolumeMm3'] > want[(c['step'], c['moving'], c['obstacle'])] + ex['volume_tolerance_mm3']]
    covered = (not bad_stages and not premature and not unexpected and len(found) == len(got) and set(got) == set(want)
               and r['checks']['steps']['pathCollisions'] == len(want))
    return covered, dict(id=acc['id'], source=acc['source'], covered=covered, failingStages=bad_stages,
                         drawnBeforePresent=premature, found=found, unexpected=unexpected,
                         missingFromRun=[list(k) for k in set(want) - set(got)])


def main():
    data = GUIDE / 'data/guide-data.json'
    text = data.read_text(errors='replace')
    missing_data = [k for k in PARTS if f'"{k}"' not in text]
    missing_world = [k for k in PARTS if not (GUIDE / 'print/world' / f'{k}.stl').exists()]
    # geometry: the printed STLs the gate audits, by hash (the commit holding them may not exist yet when the gate runs)
    world = {k: sha(GUIDE / 'print/world' / f'{k}.stl')[:12] for k in PARTS if (GUIDE / 'print/world' / f'{k}.stl').exists()}
    st = dict(version='FlightPack-D1', geometry=world, checked=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
              guideData=dict(path=str(data), sha256=sha(data)), missingInGuideData=missing_data, missingWorldStl=missing_world)
    if missing_data or missing_world:
        st.update(status='PREPARED_GATE_PENDING',
                  waitingFor=('the assembly-guide chapter for the flight pack: guide/data/guide-data.json must name these parts '
                              f'{missing_data} and guide/print/world must hold {[k + ".stl" for k in missing_world]}; then '
                              'run_gate.py runs on that guide data'))
    elif '--no-run' in sys.argv:
        st.update(status='PREPARED_GATE_PENDING', waitingFor='gate run (guide data complete; run without --no-run)')
    else:
        rc = subprocess.run([PY, 'run_gate.py'], cwd=GATE).returncode
        rec = GATE / 'gate-receipt.json'
        st.update(gateExit=rc, gateReceipt=dict(path=str(rec), sha256=sha(rec)) if rec.exists() else None)
        if rc == 0:
            st.update(status='RELEASED')
        else:
            ok, why = exception_covers(rec)
            st.update(exception=why, status='RELEASED_WITH_EXCEPTION' if ok else 'GATE_FAILED')
    (REL / 'STATUS.json').write_text(json.dumps(st, indent=1))
    print(json.dumps(st, indent=1))


if __name__ == '__main__':
    main()
