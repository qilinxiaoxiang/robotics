"""Sim only: the learned stand61 policy (walk mode at zero command) takes over 1.0 s into the stand entry, extra head mass at PI_POS."""
import json, sys
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac/stand-pose-study-20261020')
import stand_sim as S
for head_g in (0, 20, 30, 50, 60):
    for seed in (0, 1):
        r = S.run_case(dict(S.STAND_OBJ), head_g=head_g, T=22.0, walk_at=1.0, walk_s=20.0, seed=seed)
        print(json.dumps(dict(head_g=head_g, seed=seed, fell_at=r.get('fell_at'), max_tilt=r.get('max_tilt'), max_tilt_after_5s=r.get('max_tilt_after_5s'),
                              end_tilt=r.get('end_tilt'), end_pitch=r.get('end_pitch'), trunk_dx_mm=r.get('trunk_dx_mm'), foot_slip_mm=r.get('foot_slip_mm'),
                              walk=r.get('walk'))), flush=True)
