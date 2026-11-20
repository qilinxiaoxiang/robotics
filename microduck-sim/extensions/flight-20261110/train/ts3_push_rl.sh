#!/bin/zsh
# Round 3, 2026-11-20: one Kaggle kernel after the weekly quota reset (2026-11-21 00:00 UTC = 11-20 19:00 EST), two
# arms, both PPO on the distilled student s3AB_140 with the imitation term kept (distill_worker --rl-w), env
# universal5 (the teacher's rewards, unchanged), teacher t3h_750, student inputs as run AB (gain flag in column 59):
#   GPU 0  ts3rl-f   imitation 0.5 + PPO 0.5, fixed                          -> ckpt/s3RLf_<iter>
#   GPU 1  ts3rl-a   imitation 0.5 -> 0.1 over the run + PPO 0.5             -> ckpt/s3RLa_<iter>
# VARIANT=fixed pushes ts3rl-f twice with seeds 1 and 2 instead (the annealed arm is dropped when the smoke shows
# zero-command stepping growing only there): GPU 1 = ts3rl-f2 -> ckpt/s3RLf2_<iter>.
# Each arm: 160 iterations from 140 (to 300), save every 20, lr 1e-4, clip 0.1, 5 critic-only iterations first.
# The worker stops itself on the task metric (falls and low-command speed against the teacher), never on reward.
#   python3 train/detach.py train/logs/ts3_push_rl.out zsh train/ts3_push_rl.sh          (MacBook, parent pid 1)
# Not before 19:00 EST, and only when the Kaggle CLI itself shows the quota reset (GPU hours used under 5). Checks
# every 5 minutes; while the quota is not reset it writes one heartbeat line per check and spends nothing on Modal.
# A closed lid suspends this script: the push then happens at the next wake and the heartbeat line of that check
# says how late it is. caffeinate keeps the MacBook from idle sleep only.
# Heartbeat: train/logs/ts3_push_rl_heartbeat.txt (last line DONE or FAILED); the kernel's follow-up (fetch, staging,
# gate scoring on Modal under the gate lock and its 60-container cap, no batch at metered 50.00 or more):
# train/logs/ts3_rl_k_heartbeat.txt. Scoring worst case 16 saves x 0.07 = 1.12 USD.
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
H=$T/logs/ts3_push_rl_heartbeat.txt
GO=${GO_EPOCH:-$(date -j -f "%Y-%m-%d %H:%M:%S" "2026-11-20 19:00:00" +%s)}
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $H }
echo "$(date +%Y-%m-%dT%H:%M:%S) START pid $$ variant ${VARIANT:-both}; push not before $(date -r $GO +%Y-%m-%dT%H:%M:%S)" > $H
caffeinate -i -w $$ &
cd $RL
C="--distill --delta universal5 --teacher-onnx /root/assets/init/ts3t_t3h_750.onnx --manifest /root/assets/manifests/flightpack-none.json --resume-pt /root/assets/init/s3AB_140.pt --max-iters 300 --max-hours 3.2 --save-interval 20 --warmup-iters 0 --beta-iters 1 --bptt-steps 100 --epochs 2 --mb-envs 256 --stop-after 100 --drop-max 0.08 --core mamba --anchor-onnx /root/assets/init/walk61.onnx --anchor-w 1.0 --anchor-head all --case-share 0.25 --stop-share 0.25 --gain-flag-col 59 --lr 0.0001 --lr-final 0.0001 --rl-w 0.5 --rl-clip 0.1 --rl-std 0.1 --rl-critic-warmup 5"
A="$C --seed 1 --bc-w 0.5"
if [ "${VARIANT:-both}" = fixed ]; then
  B="$C --seed 2 --bc-w 0.5"; BRUN=ts3rl-f2; BTAG=s3RLf2
else
  B="$C --seed 1 --bc-w 0.5 --bc-w-final 0.1"; BRUN=ts3rl-a; BTAG=s3RLa
fi
while [ $(date +%s) -lt $GO ]; do sleep 60; done
LATE=$(( ($(date +%s) - GO) / 60 ))
[ $LATE -gt 3 ] && hb "woke $LATE min after the planned time (the MacBook was asleep or the script started late)"
for i in $(seq 1 60); do
  Q=$(python3 cmu/finetune/flight/kaggle_flight.py quota 2>&1 | grep GPU | tr -s ' ')
  USED=$(echo "$Q" | sed -E 's/^GPU ([0-9.]+)h.*/\1/')
  if [ -z "$USED" ] || ! echo "$USED" | grep -qE '^[0-9.]+$'; then
    hb "quota unread (check $i): $Q"
  elif [ $(echo "$USED < 5.0" | bc) -eq 1 ]; then
    hb "quota reset confirmed by the CLI: $Q"
    OUT=$(python3 cmu/finetune/flight/kaggle_flight.py push run --run-name ts3rl-f --pair-run-name $BRUN -- ${=A} -- ${=B} 2>&1)
    echo "$OUT" > $T/logs/launch_ts3rl-f.log
    if echo "$OUT" | grep -q "successfully pushed"; then
      hb "pushed kernel microduck-ts3rl-f (GPU 0 ts3rl-f -> s3RLf_*, GPU 1 $BRUN -> ${BTAG}_*)"
      PID=$(python3 $T/detach.py $T/logs/ts3_rl_k.out python3 $T/ts3_after_pair.py ts3rl-f none none ts3rl-f s3RLf ts3_rl_k student2=$BRUN:$BTAG hours=5)
      hb "follow-up pid $PID, heartbeat logs/ts3_rl_k_heartbeat.txt"
      hb "DONE"
      exit 0
    fi
    hb "push refused (check $i): $(echo "$OUT" | grep -i "error\|gate\|refus\|maximum\|exit\|asset" | head -1 | cut -c1-240)"
  else
    hb "quota NOT reset (check $i): $Q; nothing pushed, nothing spent on Modal; next check in 5 min"
  fi
  sleep 300
done
hb "FAILED no push after 5 h of checks"
exit 1
