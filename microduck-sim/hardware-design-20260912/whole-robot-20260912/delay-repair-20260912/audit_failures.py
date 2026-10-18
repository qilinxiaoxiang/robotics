from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;F=P.parent/'dynamics'
names=['left_hip_yaw','left_hip_roll','left_hip_pitch','left_knee','left_ankle','neck_pitch','head_pitch','head_yaw','head_roll','right_hip_yaw','right_hip_roll','right_hip_pitch','right_knee','right_ankle']
report={'local_date':'2026-09-12','timezone':'America/New_York EDT','delay_semantics':'40 ms delays all 34 values (gyro3, gravity3, q14, dq14) and heading. Last policy action and command are current. A separate 20 ms FIFO delays the generated actuator target.','cases':[]}
fig,axes=plt.subplots(4,1,figsize=(11,12),sharex=True)
for old,color in [(0,'#c34a36'),(60,'#24896b'),(120,'#805cc5')]:
    r=json.loads((P/f'replay-old{old}-sensor40.json').read_text());original=json.loads((F/f'final-perturb-batteryremove{old}-sensor40.json').read_text());rows=r['rows']
    assert len(rows)==len(original['rows'])
    assert all(np.array_equal(row['qpos'],prev['qpos']) for row,prev in zip(rows,original['rows']))
    t=np.array([x['observation_time_s'] for x in rows]);truth=np.array([x['truth_34'] for x in rows]);recv=np.array([x['received_34'] for x in rows]);act=np.array([x['policy_action'] for x in rows]);tilt=np.array([x['tilt_deg'] for x in rows]);yaw=np.degrees(np.array([x['yaw_rad'] for x in rows]))
    assert np.array_equal(recv,truth[np.maximum(np.arange(len(t))-2,0)])
    assert all(row['received_heading']==rows[max(0,i-2)]['truth_heading'] for i,row in enumerate(rows))
    for i in range(1,len(rows)):np.testing.assert_allclose(rows[i]['target_angles'],rows[i-1]['pending_target'],atol=1e-12)
    active=t>=2;err=truth-recv;events={}
    for threshold in [10,15,20,30,45,60]:
        ids=np.flatnonzero(tilt>threshold);events[f'first_any_phase_tilt_gt_{threshold}_deg_s']=float(t[ids[0]]+.02) if len(ids) else None
    for threshold in [15,20,30,60]:
        ids=np.flatnonzero(active&(tilt>threshold));events[f'first_tilt_gt_{threshold}_deg_s']=float(t[ids[0]]+.02) if len(ids) else None
    ids=np.flatnonzero(active&(np.abs(yaw)>30));events['first_abs_yaw_gt_30_deg_s']=float(t[ids[0]]+.02) if len(ids) else None
    torques=np.array([x['torques_nm'] for x in rows]);limit=.5380398404280705
    ids=np.flatnonzero(active&(np.max(abs(torques),axis=1)>.99*limit));events['first_99pct_torque_limit_s']=float(t[ids[0]]+.02) if len(ids) else None
    idx=np.unravel_index(np.argmax(abs(err[:,6:20])),err[:,6:20].shape)
    case={'removed_old_battery_g':old,'total_mass_kg':r['mass_kg'],'replay_qpos_bitwise_identical':True,'delayed_fields_exact_2_tick_replay':True,'action_targets_exact_1_tick_delay':True,
          'fall_time_s':r['fall_time_s'],'completed_s':r['duration_completed_s'],'events':events,
          'signals':{'max_gyro_norm_rad_s':float(np.linalg.norm(truth[:,:3],axis=1).max()),'max_received_gyro_error_norm_rad_s':float(np.linalg.norm(err[:,:3],axis=1).max()),
          'max_joint_velocity_abs_rad_s':float(np.max(abs(truth[:,20:34]))),'max_stale_q_error_rad':float(np.max(abs(err[:,6:20]))),'max_stale_q_error_joint':names[idx[1]],'max_stale_q_error_time_s':float(t[idx[0]]),
          'max_stale_q_error_before_30deg_tilt_rad':float(np.max(abs(err[tilt<30,6:20]))),'max_policy_action_abs_rad':float(np.max(abs(act))),
          'max_policy_action_step_rad':float(np.max(abs(np.diff(act,axis=0))))},'source':str(P/f'replay-old{old}-sensor40.json')}
    report['cases'].append(case)
    label=f'Old battery removal {old} g'
    axes[0].plot(t+.02,tilt,c=color,label=label);axes[1].plot(t+.02,yaw,c=color)
    axes[2].plot(t,np.max(abs(err[:,6:20]),axis=1),c=color)
    axes[3].plot(t[1:],np.max(abs(np.diff(act,axis=0)),axis=1),c=color)
for ax in axes:
    ax.axvline(2,color='#888888',ls=':',lw=1);ax.grid(alpha=.25);ax.set_xlim(0,6)
axes[0].axhline(30,color='black',ls='--',lw=.8);axes[0].legend();axes[0].set_ylabel('Body tilt / deg')
axes[1].set_ylabel('Yaw / deg');axes[2].set_ylabel('Largest stale q error / rad');axes[3].set_ylabel('Largest action jump / rad');axes[3].set_xlabel('Simulation time / s (forward command starts at 2 s)')
fig.suptitle('Exact replay: all proprioception delayed 40 ms + actuator target delayed 20 ms')
fig.tight_layout();fig.savefig(P/'failure-timing.png',dpi=170);fig.savefig(P/'failure-timing.svg')
(P/'failure-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
