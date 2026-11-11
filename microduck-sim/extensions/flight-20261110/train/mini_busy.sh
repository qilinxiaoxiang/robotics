#!/bin/zsh
# Run ON the Mac mini (mini.sh run calls it first): list simulation processes that are not this train mirror's,
# so one sim runs at a time when another agent (flight-sim) shares the machine. Exit 1 when any is found.
found=0
for pid in $(pgrep -f "venvs/flight-sim/bin/python|\.venv/bin/python|mujoco|brain_sim_check|flight_audit|style_eval|flight_eval"); do
  cwd=$(lsof -a -d cwd -p $pid -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)
  case "$cwd" in
    *flight-train-mirror*) ;;
    *) found=1; echo "busy: pid $pid cwd $cwd $(ps -o etime=,command= -p $pid | cut -c1-140)" ;;
  esac
done
exit $found
