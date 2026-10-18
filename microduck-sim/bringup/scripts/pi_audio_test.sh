#!/usr/bin/env bash
# MicroDuck audio: check the sound card, set the volume and play the test voices. Run from the Mac after pi_audio_setup.sh.
# Usage: bringup/scripts/pi_audio_test.sh [user@host] [percent]   (default duck@microduck.local 50)
# Expected: `aplay -l` lists card MAX98357A; 50% reads -28.40 dB and 100% reads -3.00 dB (softvol -54..-3 over 256 steps, measured on the Pi);
# the speaker says "Front Left", "Front Right", then "Front Center". Programs must use the default device, never hw:MAX98357A.
set -euo pipefail
PI="${1:-duck@microduck.local}"; PCT="${2:-50}"
ssh -o ConnectTimeout=15 "$PI" "set -e
aplay -l | grep -i max98357a || { echo 'NO MAX98357A card: check dtoverlay (pi_audio_setup.sh) and reboot'; exit 2; }
aplay -q -t raw -f cd -d 1 /dev/zero
amixer -c MAX98357A sset PCM ${PCT}% | grep -E 'Front (Left|Right)'
speaker-test -c 2 -t wav -l 1 >/dev/null
aplay -q /usr/share/sounds/alsa/Front_Center.wav
amixer -c MAX98357A sset PCM 100% | grep -E 'Front Left'
amixer -c MAX98357A sset PCM 100% >/dev/null
sudo alsactl store
echo 'audio test done: 100% (= -3.00 dB ceiling) stored as daily level'"
