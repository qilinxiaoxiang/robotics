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
        st.update(gateExit=rc, gateReceipt=dict(path=str(rec), sha256=sha(rec)) if rec.exists() else None,
                  status='RELEASED' if rc == 0 else 'GATE_FAILED')
    (REL / 'STATUS.json').write_text(json.dumps(st, indent=1))
    print(json.dumps(st, indent=1))


if __name__ == '__main__':
    main()
