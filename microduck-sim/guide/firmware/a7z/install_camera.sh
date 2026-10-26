#!/usr/bin/env bash
# Start the head camera at every A7Z boot, from the Mac:  bash install_camera.sh   (A7Z_HOST=a7z by default)
#
# Copies mac/a7z_cam.py to ~/rt/microduck-sim/guide/firmware/mac/ and pi/systemd/duck-camera.service to
# /etc/systemd/system/, enables and (re)starts it, then checks: the installed copies match the Mac (sha256), the
# service is active and a frame younger than 1 s is in /dev/shm/a7z_cam.bgr.
# Undo: sudo systemctl disable --now duck-camera; sudo rm /etc/systemd/system/duck-camera.service
set -euo pipefail

HOST=${A7Z_HOST:-a7z}
HERE=$(cd "$(dirname "$0")" && pwd)
quiet() { grep -v -E "quantum|store now|upgraded" || true; }   # OpenSSH post-quantum notice on every connection
CAM="$HERE/../mac/a7z_cam.py" UNIT="$HERE/../pi/systemd/duck-camera.service"
SUMS="$(shasum -a 256 "$CAM" | cut -d' ' -f1) $(shasum -a 256 "$UNIT" | cut -d' ' -f1)"

scp -q "$CAM" "$HOST:rt/microduck-sim/guide/firmware/mac/a7z_cam.py" 2>&1 | quiet
scp -q "$UNIT" "$HOST:/tmp/duck-camera.service" 2>&1 | quiet
ssh "$HOST" "SUMS='$SUMS' bash -s" <<'EOF' 2>&1 | quiet
set -u
fail=0
bad() { echo "FAIL: $*"; fail=1; }
sudo -n install -m 644 /tmp/duck-camera.service /etc/systemd/system/duck-camera.service || bad "install unit"
got="$(sha256sum ~/rt/microduck-sim/guide/firmware/mac/a7z_cam.py | cut -d' ' -f1) $(sha256sum /etc/systemd/system/duck-camera.service | cut -d' ' -f1)"
[ "$got" = "$SUMS" ] && echo "files: installed copies match the Mac" || bad "installed files differ from the Mac copies"
~/.venvs/duck-policy/bin/python ~/rt/microduck-sim/guide/firmware/mac/a7z_cam.py --stop >/dev/null || true
sudo -n systemctl daemon-reload
sudo -n systemctl enable duck-camera.service >/dev/null 2>&1 || bad "enable"
sudo -n systemctl restart duck-camera.service || bad "start"
for i in $(seq 15); do
  age=$(python3 -c "import struct,time;h=open('/dev/shm/a7z_cam.bgr','rb').read(16);print(round(time.time()-struct.unpack('<Qd',h)[1],2))" 2>/dev/null) && break
  sleep 1
done
systemctl is-active --quiet duck-camera.service && echo "service: active, enabled at boot: $(systemctl is-enabled duck-camera.service)" || bad "service not active"
[ -n "${age:-}" ] && python3 -c "import sys;sys.exit(0 if float('$age')<1.0 else 1)" && echo "frame: $age s old" || bad "no fresh frame (age ${age:-none})"
exit $fail
EOF
