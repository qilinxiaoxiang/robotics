#!/bin/bash
# (Re)start the onboard MicroDuck brain in the background (monitor mode, torque untouched); logs persist in ~/duck-logs.
# Installed to ~/duck-run.sh on the A7Z by install_teleop.sh; the app's duck-command.py runs it as ~/duck-run.sh app<MMDD-HHMMSS>
# when no brain runs. At boot duck-brain.service starts the same ~/duck-brain.sh.
suf=${1:?suffix}
# a running brain is stopped first; the 1 s wait (its servo bus and log closing) only when there was one
pkill -f "^/home/radxa/.venvs/duck-policy/bin/python walk_wired.py" && sleep 1
setsid nohup ~/duck-brain.sh "$suf" > /dev/null 2>&1 < /dev/null &
