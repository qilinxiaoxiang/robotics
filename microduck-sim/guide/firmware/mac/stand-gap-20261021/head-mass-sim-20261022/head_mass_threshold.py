"""Sim only: open-loop stand entry (NEUTRAL -> STAND ramp, hold 12 s) with extra head mass at PI_POS, to find where it falls."""
import json, sys
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac/stand-pose-study-20261020')
import stand_sim as S
for head_g in (0, 10, 20, 30, 40):
    r = S.run_case(dict(S.STAND_OBJ), head_g=head_g, T=12.0, seed=0)
    print(json.dumps(dict(head_g=head_g, fell_at=r.get('fell_at'), max_tilt=r.get('max_tilt'), end_tilt=r.get('end_tilt'), end_pitch=r.get('end_pitch'),
                          trunk_dx_mm=r.get('trunk_dx_mm'), start_pitch_deg=r.get('start_pitch_deg'), total_mass=r.get('total_mass_kg', r.get('total_mass')))), flush=True)
