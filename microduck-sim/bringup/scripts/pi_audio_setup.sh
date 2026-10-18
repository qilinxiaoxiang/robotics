#!/usr/bin/env bash
# MicroDuck audio: configure the Pi Zero W for the MAX98357A I2S amplifier and install the -3 dB volume ceiling.
# Run from the Mac:  bringup/scripts/pi_audio_setup.sh [user@host]     (default duck@microduck.local)
# Claude runs this over ssh during BRINGUP step 13; the page itself shows no commands (Shawn, 2026-10-14).
# Idempotent: safe to rerun. Reboots the Pi once if config.txt changed. Then: pi_audio_test.sh.
set -euo pipefail
PI="${1:-duck@microduck.local}"
ssh -o ConnectTimeout=15 "$PI" 'bash -s' <<'REMOTE'
set -euo pipefail
CFG=/boot/firmware/config.txt
[ -f "$CFG" ] || CFG=/boot/config.txt
changed=0
sudo cp -n "$CFG" "$CFG.bak" 2>/dev/null || true
if grep -q '^dtparam=audio=on' "$CFG"; then sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' "$CFG"; changed=1; fi
if ! grep -q '^dtoverlay=max98357a,no-sdmode' "$CFG"; then echo 'dtoverlay=max98357a,no-sdmode' | sudo tee -a "$CFG" >/dev/null; changed=1; fi
echo "config: $(grep -n -E '^#?dtparam=audio|max98357a' "$CFG" | tr '\n' ' ')"
if grep -s -n -E 'snd_bcm2835|blacklist' /etc/modules /etc/modprobe.d/raspi-blacklist.conf 2>/dev/null | grep -q .; then echo "WARN: blacklist entries present"; fi
dpkg -s alsa-utils >/dev/null 2>&1 || sudo apt-get install -y alsa-utils
# Ceiling: 9 dB amplifier gain (GAIN unconnected) with max_dB -3.0 gives 0.8 W at 0 dBFS into the 8 ohm 1 W speaker
# (raised from -6.0 on 2026-10-15 at Shawn's request; never above -3.0, 0 dB would be 1.6 W).
sudo tee /etc/asound.conf >/dev/null <<'EOT'
pcm.speakerbonnet { type hw card MAX98357A }
pcm.dmixer {
  type dmix
  ipc_key 1024
  ipc_perm 0666
  slave { pcm "speakerbonnet" period_time 0 period_size 1024 buffer_size 8192 rate 44100 channels 2 }
}
ctl.dmixer { type hw card MAX98357A }
pcm.softvol {
  type softvol
  slave.pcm "dmixer"
  control.name "PCM"
  control.card MAX98357A
  min_dB -54.0
  max_dB -3.0
}
ctl.softvol { type hw card MAX98357A }
pcm.!default { type plug slave.pcm "softvol" }
EOT
sudo rm -f /var/lib/alsa/asound.state
echo "asound.conf written (max_dB -3.0)"
if [ "$changed" = 1 ]; then echo "rebooting"; sudo systemctl reboot; fi
REMOTE
