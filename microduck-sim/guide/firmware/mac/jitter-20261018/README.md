# Jitter sim-ID study (2026-10-18, continued 2026-10-30)

## 2026-10-30 targets

Goal: one sim setting, the same for all three policies, under which the as-built CPU sim reproduces the robot's
action jumps and peak tilt of 2026-10-30 within a factor of 2, including the ordering (walk61 and t2b with the
default head calm; T1, and t2b with a neck command, shaking). Sim and Mac only; nothing on the robot, no training.

Sim: `jitter_sim.py` over `../brain_sim_check.py` (as-built model, plugged manifest
`microduck_rl-grasp/cmu/model/manifests/plugged.json`), real-condition flags from `../robot_state_check.py
--print-sim-args` = `--volt 7.0 --drop 0.04` (microduck-sim/CURRENT-STATE.json: servo_rail_v 7.0, servo_read_drop_fraction
0.04, imu_rate_hz 50, imu_added_delay_ms 0; KP_RL 200 is the Brain's default). Each row: stand 1 s, stand61 to 4 s,
then vx 0.25 for the robot's walk length (3 s; 2 s for the neck hold), seeds 0/1/2, head command as on the robot
(`--neck-pitch`). Metrics: `jitter_metrics.py`, the `compare_walks.py` definitions used for the robot rows (a jump is any
action changing by more than 0.5 rad between consecutive walk-policy ticks, rate per walking second; tilt over every
row of the walking window). `sweep_20261030.py` runs the grid and scores it; `mechanism_20261030.py` compares the
joint-level oscillation; results in `results-20261030/` (one JSON per setting, `summary.json`, `mechanism-*.json`,
`long10s-*.json`), robot rows in `targets-20261030.json` (`make_targets.py`).

### The six robot rows (0.25 m/s, `../robot-runs-20261030-t1/`)

    row              jumps/s        peak tilt      mean tilt  trunk gyro rms xyz      note
    walk61 default   2.06 (1.4-2.7) 7.8 (7.4-8.6)  3.8        0.72 0.46 0.63          5 walks
    T1 default       21.8           29.3           7.2        0.82 0.80 1.17          fell
    T1 neck -0.4     17.1           17.6           6.6        1.04 0.93 1.16
    t2b default      1.67           8.7            4.3        0.73 0.45 0.76
    t2b neck -0.4    14.0           16.4           5.9        1.01 0.83 1.35
    t2b neck -0.8    13.6 (2 s)     10.8           4.7        0.82 0.77 0.96

### Every sim setting tried (jumps/s / peak tilt deg per row, mean of 3 seeds; F = a seed fell; pass = both within 2x)

Columns: walk61 default, T1 default, T1 neck -0.4, t2b default, t2b neck -0.4, t2b neck -0.8. "order" = every calm row
below every shaking row. Sorted by the worst row's log2 error.

    ROBOT              2.06/7.8     21.8/29.3    17.1/17.6    1.67/8.7     14.0/16.4    13.6/10.8
    gndq0.25+fric1.4   2.68/7.5     17.2/20.2F   15.7/19.7F   8.05/11.4    11.4/18.3F   13.3/19.1F   pass 5/6 order y   <- best
    gndq0.25+fric1.25  2.69/7.5     16.9/19.0F   17.5/20.9F   4.81/7.0     5.82/8.0     7.58/10.2    pass 4/6 order y
    gndq0.25+stic2.0   3.02/9.3     17.6/18.4F   19.1/19.4F   4.92/7.7     5.26/8.9     7.07/10.0    pass 4/6 order y
    gndq0.25+fric1.25+stic1.5 1.79/6.1 16.9/13.3 18.6/25.4F   9.28/12.5    11.4/19.9F   15.0/17.7F   pass 4/6 order y
    gndq0.2+fric1.5    2.68/6.5     13.4/21.3F   12.8/29.4F   9.4/17.1F    14.9/26.6F   19.3/36.9F   pass 4/6 order y
    gndq0.3+fric1.4    3.8/8.5      21.4/21.8F   18.7/20.8F   12.9/24.9F   13.6/18.9F   14.7/13.8F   pass 5/6 order y
    gndq0.4            8.39/9.0     31.6/24.4F   33.4/22.7F   11.1/7.2     14.5/8.3     14.7/9.4     pass 4/6 order y
    gn0.2+grn0.05      6.15/12.1    11.2/15.0    12.3/13.0    6.15/12.2    9.28/13.6    10.3/13.4    pass 4/6 order y
    gn0.3+fric1.4      2.91/8.3     8.05/10.0    10.1/19.4F   4.48/8.7     5.14/10.5    8.76/12.3    pass 3/6 order y
    gn0.6              12.5/9.6     19.2/10.9    18.5/17.9F   12.1/8.6     14.9/9.5     13.8/10.4    pass 3/6 order y
    gndq0.25           2.68/7.1     18.5/10.3    17.6/11.6    5.15/6.5     5.37/6.2     5.05/6.8     pass 2/6 order n
    gn0.3+kp160        4.03/7.7     7.27/9.0     7.49/8.2     4.48/6.3     5.26/7.7     7.24/9.2     pass 2/6 order y
    gn0.3              2.02/7.1     6.49/7.4     4.92/6.5     3.02/5.9     3.92/6.6     5.05/8.5     pass 2/6 order y
    soft0.05           1.9/6.1      4.36/7.1     5.15/9.3     2.8/7.0      2.91/6.6     3.03/9.0     pass 2/6 order y
    imu38              2.01/6.2     4.59/7.2     4.59/6.4     1.9/6.0      1.79/8.2     2.86/7.3     pass 2/6 order n
    kp160              1.12/5.7     1.56/8.9     2.91/7.4     1.23/8.5     1.45/6.7     4.55/7.6     pass 2/6 order y
    gn0.3+grn0.03      4.59/10.0    11.3/12.6    8.5/9.2      4.47/9.9     5.48/10.3    6.23/11.0    pass 0/6 order y
    grn0.05            3.58/12.1    8.28/12.2    8.05/12.4    4.81/11.4    5.26/10.5    6.74/12.4    pass 1/6 order y
    gn0.3+fric1.25     2.24/7.6     7.27/8.8     8.2/18.6F    4.25/6.3     4.92/8.3     5.05/7.6     pass 1/6 order y
    gn0.3+stic2.0      2.46/7.7     7.27/8.7     6.82/8.4     3.47/6.5     3.91/7.3     4.04/8.3     pass 1/6 order y
    gn0.4              4.59/8.3     11.5/7.6     9.28/6.9     6.04/6.2     6.49/7.3     7.58/8.3     pass 1/6 order y
    gn0.45             5.81/9.4     12.8/8.0     11.1/7.6     8.28/7.5     7.5/7.3      8.75/9.3     pass 1/6 order n
    gndq0.15           1.01/6.1     9.84/7.6     7.5/6.7      2.01/5.8     2.24/5.8     2.86/6.1     pass 1/6 order y
    fric1.4            0.67/5.5     2.12/9.3     3.02/7.9     5.04/10.2    3.24/9.9     6.4/9.6      pass 0/6 order n
    fric1.25           0.9/6.1      2.46/8.5     2.01/7.1     1.12/8.7     0.9/6.1      1.52/6.1     pass 1/6 order n
    fric1.5            0.0/4.5      2.01/9.4     5.26/9.8     7.83/11.1    15.1/34.7F   14.0/32.3F   pass 0/6 order n   (walk61 stops stepping)
    fric1.25+kp160     0.0/4.4      3.36/9.0     4.59/10.6    4.81/9.6     -            -            (walk61 stops; t2b neck rows not run)
    stic1.5            0.45/5.8     1.46/7.6     1.79/6.7     0.9/7.7      0.34/5.7     0.85/6.6     pass 1/6 order n
    stic2.0            0.67/5.8     2.68/8.2     2.12/8.2     0.9/8.4      0.78/6.4     1.52/6.6     pass 1/6 order n
    kp300              0.11/5.5     1.12/6.1     1.23/4.8     0.67/4.0     0.34/4.2     0.0/6.3      pass 0/6 order n
    db0.02             0.56/5.7     1.68/7.4     1.68/6.3     1.01/6.0     0.45/5.5     0.84/6.2     pass 1/6 order n
    db0.03             0.67/6.3     1.23/7.6     1.57/6.6     0.56/5.8     0.56/5.5     1.01/6.2     pass 0/6 order n
    db0.04             0.0/3.5      2.12/7.6     1.45/6.6     0.78/6.5     0.89/5.7     1.18/6.1     pass 0/6 order y   (walk61 stops stepping)
    db0.04h            0.0/4.3      1.45/7.8     1.45/7.1     0.56/5.5     1.01/5.7     1.01/6.5     pass 0/6 order y   (walk61 stops)
    db0.05             0.0/3.6      2.35/8.3     1.68/7.3     0.67/5.7     1.23/6.0     1.18/7.0     pass 0/6 order y   (walk61 stops)
    db0.06             0.0/3.8      2.46/8.5     1.79/7.5     0.67/5.8     1.01/6.5     1.69/7.3     pass 0/6 order y   (walk61 stops)
    drop0.052          0.45/5.8     1.45/7.2     1.56/6.1     1.12/7.0     0.34/5.6     1.18/6.3     pass 1/6 order n
    head+20g           0.67/5.5     0.78/7.4     2.01/6.0     0.67/6.1     0.45/5.6     1.01/5.9     pass 0/6 order n
    head+50g           0.34/6.7     1.18/8.4     2.52/6.2     1.51/6.1     1.01/5.8     4.04/6.4     pass 1/6 order n   (no forward progress)
    ascale0.9          0.34/5.1     1.34/8.1     2.57/6.8     1.23/6.6     1.12/5.8     1.85/5.8     pass 1/6 order n
    lp0.7              0.67/7.4     1.01/9.0     1.34/7.5     0.78/6.6     0.34/6.3     0.34/7.5     pass 0/6 order n
    gn0.1              0.78/5.9     1.9/7.1      1.79/6.1     0.67/6.1     0.45/5.5     0.68/6.1     pass 0/6 order n
    gn1.0              29.3/22.5F   32.8/27.7F   33.3/25.4F   27.4/14.0F   31.1/26.9F   33.4/29.2F   pass 2/6 order y   (everything falls)
    grn0.02            0.56/7.8     1.9/8.0      1.68/7.1     0.78/7.2     0.34/7.0     0.68/7.4     pass 0/6 order n
    an0.02             0.78/6.0     1.23/7.0     1.34/6.0     0.78/5.9     0.34/5.6     0.68/6.2     pass 0/6 order n
    an0.05             0.45/5.8     1.23/6.6     1.12/6.1     0.67/6.4     0.23/5.7     1.01/6.1     pass 0/6 order n
    fp2                0.56/5.7     0.9/7.2      1.34/6.1     0.45/5.7     0.34/5.8     0.51/5.9     pass 0/6 order n
    fp4                0.56/5.7     1.45/7.2     1.56/6.1     0.45/5.5     0.34/5.8     0.51/5.9     pass 0/6 order n
    fp2roll            0.56/5.9     2.91/7.4     2.24/7.0     0.78/6.0     0.34/5.3     1.01/5.9     pass 0/6 order n
    hard0.01           0.45/5.8     1.01/7.2     1.45/6.2     0.67/6.2     0.45/5.9     0.51/6.2     pass 0/6 order n
    mu0.7              0.56/6.1     1.34/7.1     1.57/6.5     1.12/6.5     0.34/5.7     0.51/6.0     pass 1/6 order n
    mu1.3              0.56/5.5     1.56/7.1     1.57/6.1     0.9/5.7      0.45/5.5     0.51/6.0     pass 1/6 order n
    adel2              0.67/8.4     4.45/21.1F   9.75/38.2F   8.9/29.0F    1.12/11.8F   0.68/9.0F    pass 0/6 order n   (falls at random)
    sdel2, sdel3, obsdel1, obsdel2   stand61 falls at 2.16 s in every seed and policy, before the walk: no row
    base               0.56/5.6     1.12/7.1     1.23/6.1     0.78/6.5     0.34/5.6     0.68/6.0     pass 0/6 order n

Switch names: `db` = `--deadband` rad on the legs (`h`: head too); `stic` = `--stiction-scale` (BAM Stribeck terms only);
`fric` = `--bam-friction-scale` (all BAM friction); `kp` = `--kp-rl`; `drop`/`imu` = `--drop`/`--imu-hz` at the measured
range edges (3.3-5.2 %, 38-51/s); `sdel`/`adel`/`obsdel` = `--sensor-delay`/`--action-delay`/`--obs-delay` ticks;
`head+Ng` = `--head-mass-g`; `lp0.7` = robotd low-pass 0.7/0.5, `ascale0.9` = robotd action scale (the runtime has
neither); `gn` = `--gyro-noise` rad/s white noise on the gyro the Brain sees; `grn` = `--grav-noise` rad on the IMU
quaternion; `an` = `--act-noise` rad on the goals; `gndq K` = `--gyro-noise-dq`, gyro noise rms = K x rms leg joint
speed that tick (motion-driven vibration); `fp` = `--foot-play` deg (ankle axis; `roll`: forward axis); `soft`/`hard` =
`--sole-solref` 0.05/0.01; `mu` = `--floor-mu`. Base = real-condition flags alone.

### Best setting and its distance from each row

`--gyro-noise-dq 0.25 --bam-friction-scale 1.4` (five of six rows within 2x, ordering kept):

- walk61 default: 2.68/s, 7.5 deg (robot 2.06, 7.8): ratios 1.30 and 0.96. Walks 0.12 m in 3 s (base 0.23; the
  robot about 0.45).
- T1 default: 17.2/s, 20.2 deg, one seed fell (robot 21.8, 29.3, fell): 0.79 and 0.69.
- T1 neck -0.4: 15.7/s, 19.7 deg, one seed fell (robot 17.1, 17.6, no fall): 0.92 and 1.12.
- t2b default: 8.05/s, 11.4 deg (robot 1.67, 8.7): **4.8x too many jumps**, tilt 1.31. The failing row.
- t2b neck -0.4: 11.4/s, 18.3 deg, one seed fell (robot 14.0, 16.4): 0.81 and 1.11; seeds spread 5.0-21.7/s.
- t2b neck -0.8: 13.3/s, 19.1 deg, one seed fell (robot 13.6, 10.8): 0.98 and 1.77.

With friction 1.25 instead of 1.4 (`gndq0.25+fric1.25`) the calm rows are right (walk61 2.69/7.5, t2b default 4.81/7.0)
and T1 is right (16.9 and 17.5/s), but the t2b neck rows stay at 5.8 and 7.6/s against 14.0 and 13.6. No setting in the
grid gets t2b default and t2b neck -0.4 right together: on the robot they differ 8.4x in jumps, in the sim at most
1.4x (fric1.4) under any switch that keeps walk61 stepping. A 10 s version of the t2b rows under `gndq0.25+fric1.25`
(`long10s-gndq0.25+fric1.25.json`) shows the neck -0.4 walk holding 5-6 jumps/s for the whole 10 s with no growth
(default 4-5/s), while neck -0.8 grows in 2 of 3 seeds (13-18/s, falls at 6.6 and 14.2 s): the sim's t2b neck -0.4
oscillation is steady and damped where the robot's grew from 4-6 to 22-24 jumps/s between 1.5 and 2.5 s.

### What single switches do

- A leg deadband (0.02-0.06 rad) changes nothing in the shaking rows and from 0.04 stops walk61 stepping, as the
  10/17 friction result did. Stiction x1.5-2 alone: at most 2.7/s anywhere.
- BAM friction x1.5 makes exactly the t2b neck rows shake like the robot (15.1 and 14.0/s, falls) and leaves T1 at
  2-5/s, but stops walk61 (0 jumps, 0.00 m) and lifts t2b default to 7.8/s. Friction x1.25-1.4 alone: 1-6/s.
- kp-rl 160 raises every row 2-4x and keeps the ordering; 300 calms everything. The real gain is 200 (base).
- Dropped reads at the measured maximum (5.2 %) change nothing; IMU at 38/s doubles every row without ordering.
- Any extra tick of IMU delay (sensor, action or IMU-only) topples stand61 at 2.16 s in every seed, before the
  walk. The robot's IMU path has no extra delay (CURRENT-STATE imu_added_delay_ms 0), so delay is refuted twice.
- Extra head mass (+20/+50 g beyond the plugged manifest) does not raise jumps; +50 g stops forward progress.
- robotd's low-pass and action scale lower the sim's jumps slightly; the runtime has neither.
- Ankle play (2-4 deg, pitch or roll), sole softness and floor friction 0.7-1.3 change nothing.
- White gyro noise lifts every row together: 0.3 rad/s puts the calm rows at the robot's level (2.0 and 3.0/s) but
  the shaking rows only at 4-6.5/s; 0.6 puts the shaking rows right (14-19/s) and the calm rows 6x too high. A
  constant floor cannot make the spread. Gravity-vector noise behaves the same.
- Motion-driven gyro noise (`gndq`, rms = 0.25 x rms leg speed) is the only switch that separates T1 from t2b the
  way the robot does (17-18/s against 5/s) while keeping walk61 at 2.7/s; it does not separate t2b neck from t2b
  default (5.4 against 5.2/s).

### Where the gap is (per policy, `mechanism-*.json`, `compare.py`-style numbers over the walking window)

Base sim against the robot: the leg joints realise about the same share of the commanded oscillation (median leg
q_rms / action_rms: robot 0.32-0.37, sim 0.18-0.32; the knees realise more in the sim, 0.11-0.15 against 0.05-0.07,
hips about the same), the action amplitudes of the shaking rows are 1.3-2x smaller in the sim (hip pitch 0.31-0.54
against 0.66-0.76 rad rms, knee 0.50-0.61 against 0.64-0.81), and the trunk gyro rms is 2-3x smaller (shaking rows
0.3-0.5 against 0.9-1.4 rad/s; calm rows 0.56/0.24/0.28 against 0.72/0.46/0.63 xyz). Split by band, the robot's
extra gyro power sits above 5 Hz (0.6-0.9 rad/s rms in the shaking rows against 0.12-0.3 in the sim; 0.35-0.4 in
the calm rows) and grows with the shaking; the 0.5-5 Hz gait band differs only 1.3-2x. Under the best setting the
trunk gyro rms matches in the shaking rows (sim 1.07/0.82/0.98 against 1.01/0.85/1.38 for t2b neck -0.4) and sits
1.2x high in t2b default (0.84/0.56/0.87 against 0.73/0.45/0.77).

Mechanistic check, t2b neck -0.4: on the robot the large alternating actions are hip pitch and knee of both legs,
left and right in phase (action correlation hip pitch +0.85, knee +0.74; hip roll -0.48), at 1.77 Hz, i.e. a
trunk-pitch bounce at the stride frequency, not a stride and not a tick-rate chatter (of the 12-19 jumps per joint,
3-8 are consecutive sign flips). The base sim shows the same joints, the same phase pattern (+0.77 / +0.82 / -0.48) and
the same frequency (1.72 Hz) at half the amplitude (hip pitch 0.31-0.33 against 0.66-0.71 rad rms; knee 0.50-0.53
against 0.64-0.76), so it is the same loop, damped, not a different mechanism. Under `gndq0.25+fric1.4` the sim's
amplitudes match the robot's (hip pitch 0.61, knee 0.79-0.81, correlation +0.78/+0.80) for that row, but t2b default
comes along to 0.38/0.65-0.69 rad rms (robot 0.26-0.28/0.51-0.57).

### Conclusion

The sim's jitter gap is not in the joints: the robot's legs move about as much as the sim's for the same policy and
the shaking is the same hip-pitch/knee bounce at the gait frequency. The gap is in how much the trunk shakes per unit
of leg motion (2-3x, above 5 Hz) and in a loop gain that lets that shaking grow in the fine-tuned policies. Two added
mechanisms reproduce five of the six rows with one setting: trunk gyro vibration proportional to leg speed (0.25 x
leg rms speed) and BAM friction x1.4. What the sim still cannot do is keep t2b's default-head walk calm while its
neck walks shake (robot 1.67 against 14.0/s; sim 8.05 against 11.4): the anchor's protective effect on the robot has
no sim counterpart, so a t2b-style gate would pass with 4.8x the robot's jumps on the anchored walk or miss the
unanchored shaking. For judging a fine-tune before a robot run, `gndq0.25+fric1.4` ranks T1 above t2b above walk61
as the robot does and makes T1 fall as it did; the t2b-default row is the known false alarm. The next discriminating
measurement is on the robot side, not the sim: a trunk-mounted gyro sample at 200+ Hz during a calm and a shaking
walk, to say whether the >5 Hz power is trunk motion (play, impacts) or IMU-mount vibration, which decides whether
the fix is mechanical or a filtered observation.

## 2026-10-18 scripts

`jitter_sim.py` (hypothesis switches over brain_sim_check), `compare.py`, `osc_metrics.py`, `band.py`, `summ.sh`:
the 10/17-18 sim-ID (memory notes microduck-jitter-sim-id, microduck-servo-deadband, microduck-official-robotd-gaps).
