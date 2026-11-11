#!/bin/zsh
# The flight-pack build and check chain, run on the Mac mini mirror under the bounded CAD runner (each job clamped to
# 10 minutes or less; the contract is checked after the build; one run report per job in checks/runs/). From the MacBook:
#   zsh cad/mini_sync.sh push && zsh cad/mini_sync.sh run 'zsh cad/mini_chain.sh' && zsh cad/mini_sync.sh pull
# Expects $PY and $RUN from mini_sync.sh run. Stops at the first failing job.
set -e
setopt pipefail
cd cad
mkdir -p checks/runs
eval "$RUN --status" | head -1
job() {   # job <name> <max MiB> <seconds> <command...>
  local name=$1 mib=$2 sec=$3; shift 3
  eval "$RUN --max-mib $mib --seconds $sec --report checks/runs/$name.json $*"
}
job build 3000 300 --contract-dir . -- $PY build_pack.py | grep -E "nacelle_|clamp:|Error|Trace|FAIL|PASS|contract"
job check_parts 11000 600 -- $PY check_parts.py | tail -40   # peak 9.2 GB RSS; 11000 + the 2 GB reserve fits the mini's 13.4 GB free
job lead_lengths 1500 120 -- $PY lead_lengths.py | tail -8
job update_layout 1500 120 -- $PY update_layout.py | cut -c1-160
job leg_load 1500 120 -- "sh -c 'cd .. && $PY leg_load.py'" | grep -E "v7|hip_roll" | head -4
job contract 1500 120 -- $PY ../../../guide/print/design_contract.py . | grep -oE "PASS|FAIL.*"
job fit_check 1500 120 -- $PY ../../../../cad-practice/fit_check.py FITS.json | grep -vE "^OK " | tail -6
job access 3000 300 -- $PY make_access_spec.py | grep -E "blocked|^\{" | tail -6
job root_rod 1500 120 -- $PY variant_root_rod.py | tail -1
