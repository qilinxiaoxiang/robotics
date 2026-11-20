# Install the power V2 shutdown hook on the A7Z. From the Mac, in ~/code/robotics/microduck-sim:
#   scp -r guide/firmware/a7z/power-off-20261120 a7z:rt/microduck-sim/guide/firmware/a7z/
#   ssh a7z 'bash ~/rt/microduck-sim/guide/firmware/a7z/power-off-20261120/install.sh'
# Only after the backpack V2 is fitted and the header pin 22 wire is in (guide chapter 12, step bv2-power-up).
# Acceptance (PS-3): `ssh a7z sudo poweroff` ends with the button ring dark.
set -e
SRC=/home/radxa/rt/microduck-sim/guide/firmware/a7z/power-off-20261120
sudo apt-get install -y gpiod python3-libgpiod
sudo install -d /usr/local/lib/duck
sudo install -m 0755 "$SRC/duck_power_off.py" /usr/local/lib/duck/duck_power_off.py
sudo install -m 0755 "$SRC/duck-power-off" /usr/lib/systemd/system-shutdown/duck-power-off
sudo install -m 0644 "$SRC/duck-power-off-check.service" /etc/systemd/system/duck-power-off-check.service
sudo systemctl daemon-reload
sudo systemctl enable duck-power-off-check.service
sudo systemctl start duck-power-off-check.service || true
journalctl -u duck-power-off-check.service -n 3 --no-pager
/usr/bin/python3 /usr/local/lib/duck/duck_power_off.py --dry-run poweroff
/usr/bin/python3 /usr/local/lib/duck/duck_power_off.py --dry-run reboot
