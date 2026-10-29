#!/bin/zsh
# make_variant.sh NAME COMMIT FILE...: on the Mac mini, a bisect copy ~/sims/bvh-refit-20261029/var-NAME of the snapshot
# (guide/ copied, the model trees linked) with FILE... (paths under microduck-sim/guide/firmware/) taken from COMMIT.
# Run on this MacBook; prints the md5 of each swapped file in the copy.
set -eu
name=$1; commit=$2; shift 2
REPO=/Users/xiangzheng/code/robotics
STAGE=$(mktemp -d /private/tmp/claude-501/bvhvar.XXXXXX)
for f in "$@"; do
  mkdir -p $STAGE/${f:h}
  git -C $REPO show $commit:microduck-sim/guide/firmware/$f > $STAGE/$f
done
ssh mac-mini "set -e; V=~/sims/bvh-refit-20261029/var-$name; S=~/sims/bvh-refit-20261029/rt; test -d \$V || { mkdir -p \$V/microduck-sim && cp -a \$S/microduck-sim/guide \$V/microduck-sim/ && ln -s \$S/microduck-sim/hardware-design-20260912 \$S/microduck-sim/microduck_rl \$S/microduck-sim/CURRENT-STATE.json \$V/microduck-sim/ && ln -s \$S/pet \$V/pet; }"
rsync -a $STAGE/ mac-mini:sims/bvh-refit-20261029/var-$name/microduck-sim/guide/firmware/
for f in "$@"; do print "$f $(ssh mac-mini md5 -q sims/bvh-refit-20261029/var-$name/microduck-sim/guide/firmware/$f)"; done
