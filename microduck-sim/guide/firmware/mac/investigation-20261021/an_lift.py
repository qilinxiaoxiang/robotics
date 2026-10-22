"""10/19 A7Z logs: find the robot being righted/lifted (gb z rising from side-lying toward -1) and show acc, gb,
leg position error (pos_tick - goal_tick) before/during/after. Rows have acc, pos_tick, goal_tick (1019 README)."""
import gzip, json, math, statistics as st, sys, glob
IDS = list(range(1, 15))
LEG = [1,2,3,4,5,6,7,8,9,10]; HEAD = [11,12,13,14]
for f in sorted(glob.glob('/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac/robot-runs-20261019-a7z/duck_wired_log_1019[cde].jsonl.gz')):
    rows = [json.loads(l) for l in gzip.open(f, 'rt')]
    t0 = rows[0]['t']
    print('====', f.split('/')[-1], len(rows), 'rows', round(rows[-1]['t']-t0,1), 's; keys acc', 'acc' in rows[0], 'goal_tick', 'goal_tick' in rows[0])
    # per 0.5 s bins
    bins = {}
    for r in rows:
        s = int((r['t'] - t0) * 2) / 2
        b = bins.setdefault(s, dict(acc=[], gbz=[], gby=[], gbx=[], leg_err=[], head_err=[], mode=set(), torque=set(), kp=set()))
        if r.get('acc'):
            b['acc'].append(math.sqrt(sum(a*a for a in r['acc'])))
        b['gbz'].append(r['gb'][2]); b['gby'].append(r['gb'][1]); b['gbx'].append(r['gb'][0])
        b['mode'].add(r['mode']); b['torque'].add(r.get('torque')); b['kp'].add(json.dumps(r.get('kp'), sort_keys=True) if isinstance(r.get('kp'), dict) else r.get('kp'))  # per-joint hold gains log as a dict
        gt = r.get('goal_tick')
        if gt and r.get('pos_tick'):
            M2I = {'right_hip_yaw':5,'right_hip_roll':4,'right_hip_pitch':3,'right_knee':2,'right_ankle':1,'left_hip_yaw':10,'left_hip_roll':9,'left_hip_pitch':8,'left_knee':7,'left_ankle':6,'neck_pitch':12,'head_pitch':11,'head_yaw':13,'head_roll':14}
            gt = {(int(k) if k.isdigit() else M2I[k]): v for k, v in gt.items()}
            errs = [abs(r['pos_tick'][IDS.index(i)] - gt[i]) for i in LEG if i in gt]
            herr = [abs(r['pos_tick'][IDS.index(i)] - gt[i]) for i in HEAD if i in gt]
            if errs: b['leg_err'].append(st.mean(errs))
            if herr: b['head_err'].append(st.mean(herr))
    last = None
    for s in sorted(bins):
        b = bins[s]
        line = (f"{s:6.1f}s mode={'/'.join(sorted(b['mode']))} tq={b['torque']} kp={b['kp']} gb=({st.mean(b['gbx']):+.2f},{st.mean(b['gby']):+.2f},{st.mean(b['gbz']):+.2f}) "
                f"|acc| mean={st.mean(b['acc']) if b['acc'] else float('nan'):.2f} max={max(b['acc']) if b['acc'] else float('nan'):.2f} "
                f"leg_err_ticks={st.mean(b['leg_err']) if b['leg_err'] else float('nan'):.0f} head_err={st.mean(b['head_err']) if b['head_err'] else float('nan'):.0f}")
        # print only where gravity changes or torque modes change (compress)
        key = (round(st.mean(b['gbz']), 1), '/'.join(sorted(b['mode'])))
        if key != last or (b['acc'] and max(b['acc']) > 12):
            print(line)
        last = key
