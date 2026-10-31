#!/bin/zsh
# Deploy the 2026-10-31 servo-bus fixes from git HEAD to the A7Z and read them back (run on the Mac from anywhere):
# walk_wired.py (reply parser checks length and CRC, touch reader backs off on a jammed bus), ~/duck-run.sh (battery
# guard on: --supply auto), and the console loglevel 1 sysctl. A brain already running keeps the old code until its
# next start. Prints the sha256 of each file on both sides and the live console loglevel.
set -e
REPO=/Users/xiangzheng/code/robotics
STAGE=$(mktemp -d /tmp/duck-deploy.XXXXXX)
for f in microduck-sim/guide/firmware/mac/walk_wired.py microduck-sim/guide/firmware/a7z/duck-run.sh \
         microduck-sim/guide/firmware/a7z/90-duck-console-quiet.conf microduck-sim/guide/firmware/a7z/install_console_quiet.sh; do
  git -C $REPO show HEAD:$f > $STAGE/${f:t}
done
RT=/home/radxa/rt/microduck-sim/guide/firmware
scp -q $STAGE/walk_wired.py a7z:$RT/mac/walk_wired.py
scp -q $STAGE/duck-run.sh a7z:/home/radxa/duck-run.sh
ssh a7z "mkdir -p $RT/a7z"
scp -q $STAGE/90-duck-console-quiet.conf $STAGE/install_console_quiet.sh a7z:$RT/a7z/
ssh a7z "chmod +x /home/radxa/duck-run.sh $RT/a7z/install_console_quiet.sh && $RT/a7z/install_console_quiet.sh"
echo "sha256 Mac (git HEAD):"
shasum -a 256 $STAGE/walk_wired.py $STAGE/duck-run.sh $STAGE/90-duck-console-quiet.conf | cut -c1-16
echo "sha256 A7Z:"
ssh a7z "sha256sum $RT/mac/walk_wired.py /home/radxa/duck-run.sh /etc/sysctl.d/90-duck-console-quiet.conf | cut -c1-16"
ssh a7z "grep -c 'supply bench' /home/radxa/duck-run.sh || true; ps -eo pid,etime,args | grep '[w]alk_wired.py' || echo 'no brain running'"
