from run_experiments import *
if __name__=='__main__':
    original=json.loads((FROZEN/'final-suite-summary.json').read_text())['cases']
    jobs=[]
    for r in original:
        c=copy.deepcopy(r['config']);c.update(delay_compensation='constant_velocity',prediction_fraction=1.,predict_heading=True)
        jobs.append(('repair-'+c['name'],c))
    run(jobs,'repaired-original45')
    jobs=[]
    for old in [0,60,120]:
        for delay in [0,1,2,3]:
            for seed in [0,9,42]:
                c=base(old);c.update(sensor_delay_ticks=delay,delay_compensation='constant_velocity',prediction_fraction=1.,predict_heading=True,seed=seed)
                if seed:c['joint_noise']=.03
                jobs.append((f'grid-old{old}-sensor{delay*20}-seed{seed}',c))
    run(jobs,'delay-seed-grid36')
    jobs=[]
    for old in [0,60,120]:
        c=base(old);c['predict_delayed_state']=True;jobs.append((f'legacy-predictor-old{old}',c))
    run(jobs,'legacy-predictor3')
