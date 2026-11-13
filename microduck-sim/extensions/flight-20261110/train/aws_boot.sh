#!/bin/bash
# MicroDuck AWS training boot wrapper, sent as EC2 user-data by aws_train.py (the double-at placeholders are filled there).
# It holds no credentials: the instance has no IAM role and reaches nothing in the account. Code and resume state
# are pushed in over SSH by aws_pull.py on the Mac mini, which also pulls everything under /opt/mdt/out every minute.
#
# Two independent stop paths, both armed before anything else runs:
#   1. the job wrapper below powers off when the command ends (success or failure), after the final pull or a grace;
#   2. a systemd timer powers off at WALL_S seconds after boot even if the job hangs, plus a sleep backstop 60 s later.
# InstanceInitiatedShutdownBehavior=terminate turns either power-off into termination; the root volume has
# DeleteOnTermination=true, so nothing is left.
set -u
RUN='@@RUN@@'
WALL_S=@@WALL_S@@
GRACE_S=@@GRACE_S@@
RATE='@@RATE@@'
CMD_B64='@@CMD_B64@@'
B=/opt/mdt
OUT=$B/out
CTL=$B/ctl
mkdir -p $B/in $B/src $OUT $CTL /root/assets
chown -R ubuntu:ubuntu $B

# stop path 2: wall-clock timer from boot (no nologin window, unlike `shutdown -h +N`), then a hard backstop
systemd-run --unit mdt-wall-timer --on-active=${WALL_S}s /bin/sh -c "echo \"\$(date -u +%FT%TZ) wall timer ${WALL_S}s\" >> $OUT/events.log; /bin/systemctl poweroff"
nohup /bin/sh -c "sleep $((WALL_S + 60)); echo \"\$(date -u +%FT%TZ) backstop\" >> $OUT/events.log; /sbin/poweroff -f" >/dev/null 2>&1 &

T0=$(date +%s)
ev() { echo "$(date -u +%FT%TZ) $*" >> $OUT/events.log; }
st() {  # status.json: phase plus timings, pulled by the Mac mini every minute
  cat > $OUT/status.json.tmp <<EOF
{"run": "$RUN", "phase": "$1", "detail": "${2:-}", "t": "$(date -u +%FT%TZ)", "uptime_s": $(( $(date +%s) - T0 )),
 "wall_s": $WALL_S, "setup_s": ${SETUP_S:-null}, "uv_sync_s": ${UVSYNC_S:-null}, "exit": ${RC:-null}}
EOF
  mv $OUT/status.json.tmp $OUT/status.json
}
finish() {  # stop path 1: wait for the puller's final-pull acknowledgement (or the grace), then power off
  echo "${RC:-1}" > $OUT/DONE
  ev "done rc=${RC:-1} reason=$1; waiting up to ${GRACE_S}s for the final pull"
  st done "$1"
  for _ in $(seq 1 $((GRACE_S / 5))); do [ -f $CTL/ack ] && break; sleep 5; done
  ev "power off (ack: $([ -f $CTL/ack ] && echo yes || echo no))"
  sync
  /sbin/shutdown -h now
  exit 0
}
ev "boot run=$RUN wall_s=$WALL_S rate=$RATE"
st waiting_code

# spot interruption notice (2 min warning) -> marker for the puller, which then pulls immediately
(
  while true; do
    TOK=$(curl -s -m 2 -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 300')
    if A=$(curl -s -f -m 2 -H "X-aws-ec2-metadata-token: $TOK" http://169.254.169.254/latest/meta-data/spot/instance-action); then
      [ -f $OUT/INTERRUPTED ] || { echo "$A" > $OUT/INTERRUPTED; ev "spot interruption notice $A"; }
    fi
    sleep 5
  done
) &

# code and assets arrive over SSH from the puller; give up after 20 min
for _ in $(seq 1 240); do [ -f $CTL/ready ] && break; sleep 5; done
[ -f $CTL/ready ] || { RC=2; finish "no code within 20 min"; }
ev "code ready"

st setup
S0=$(date +%s)
(
  set -ex -o pipefail
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
  MISSING=""
  for p in libgl1 libegl1 libglib2.0-0 libxrender1 libxext6 rsync git curl; do dpkg -s $p >/dev/null 2>&1 || MISSING="$MISSING $p"; done
  if [ -n "$MISSING" ]; then
    apt-get -o DPkg::Lock::Timeout=600 update -q && apt-get -o DPkg::Lock::Timeout=600 install -y -q $MISSING
  fi
  # uv 0.8.22: the same pin flight_modal.py and kernel_entry.py install
  curl -LsSf https://astral.sh/uv/0.8.22/install.sh | env UV_INSTALL_DIR=/opt/uv UV_NO_MODIFY_PATH=1 sh
  /opt/uv/uv --version
  tar -xzf $B/in/src.tgz -C $B/src
  tar -xzf $B/in/assets.tgz -C /root/assets
  find /root/assets -type f
) > $OUT/setup.log 2>&1 || { RC=3; finish "setup failed"; }
export UV_PROJECT_ENVIRONMENT=$B/venv UV_HTTP_TIMEOUT=600 UV_PYTHON_INSTALL_DIR=/opt/uvpy UV_CACHE_DIR=/opt/uvcache MUJOCO_GL=egl PYTHONUNBUFFERED=1
st setup uv_sync
U0=$(date +%s)
(cd $B/src && /opt/uv/uv sync --frozen --no-dev) >> $OUT/setup.log 2>&1 || { RC=4; finish "uv sync failed"; }
UVSYNC_S=$(( $(date +%s) - U0 ))
# the same import check as cmu/finetune/kaggle/kernel_entry.py
(cd $B/src && $B/venv/bin/python -c "import torch, mjlab, mujoco, warp, mjlab_microduck.tasks; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0), 'mujoco', mujoco.__version__, 'warp', warp.__version__)") >> $OUT/setup.log 2>&1 || { RC=5; finish "import check failed"; }
SETUP_S=$(( $(date +%s) - S0 ))
ev "setup done in ${SETUP_S}s (uv sync ${UVSYNC_S}s)"

st running
GPU_NAME=aws-$(curl -s -m 2 -H "X-aws-ec2-metadata-token: $(curl -s -m 2 -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')" http://169.254.169.254/latest/meta-data/instance-type)
CMD=$(echo "$CMD_B64" | base64 -d)
echo "=== $(date -u +%FT%TZ) attempt on $GPU_NAME: $CMD" >> $OUT/job.log
(cd $B/src && env OUT=$OUT RUN="$RUN" RATE_PER_HOUR="$RATE" GPU_NAME="$GPU_NAME" PATH=$B/venv/bin:$PATH bash -c "$CMD") >> $OUT/job.log 2>&1
RC=$?
finish "command exited"
