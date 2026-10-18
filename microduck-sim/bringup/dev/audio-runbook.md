# Audio bring-up runbook (Claude-side, not shown on the page)

Shawn's instruction 2026-10-14: the BRINGUP page shows no terminal commands for the audio step; Claude runs the Pi side
over ssh and only the hands-on work and the listening check stay on the page.

## Sequence

1. Shawn: five wires soldered into the amplifier, speaker leads in the terminal, five plugs on Pi pins 4, 12, 34, 35, 40,
   Pi powered (PWR IN). He says so in chat.
2. Claude: `bringup/scripts/pi_audio_setup.sh duck@microduck.local` (or `ssh duck` over Tailscale, `ssh healthpi` over
   USB; see memory `microduck-pi-card`). It edits `/boot/firmware/config.txt` (comment `dtparam=audio=on`, append
   `dtoverlay=max98357a,no-sdmode` under the final `[all]`), installs alsa-utils, writes `/etc/asound.conf` with softvol
   `max_dB -3.0`, deletes `/var/lib/alsa/asound.state`, reboots if config.txt changed. Wait about 60 s.
3. Claude: `bringup/scripts/pi_audio_test.sh duck@microduck.local 50`. Expected output: `card N: MAX98357A`,
   `Front Left: 128 [50%] [-28.40dB]`, the speaker says Front Left / Front Right / Front Center, then
   `Front Left: 255 [100%] [-3.00dB]`, daily level stored at 100 %. Measured on 2026-10-15 by routing a full-scale sine
   through the same softvol into a `type file` sink: 100 % applies -3.00 dB.
5. Duck quack: real recordings from Wikimedia Commons (mallard XC62258, CC BY-SA 3.0) or the Pollen microduck-simulator
   voices, high-passed at 500 Hz, +10 to +14 dB into a -1 dBFS limiter, played with plain `aplay` (default device).
   `scripts/make_quack.py` is a synthetic fallback; Shawn found it unlike a duck.
4. Ask Shawn: clear voice, no distortion, no hum. Record in the page's step-13 checkbox.

## If it fails

- No MAX98357A card: `grep -n -E '^\[|audio|max98357a' /boot/firmware/config.txt`; the dtoverlay line must sit under the
  last `[all]`, not under `[cm4]`/`[cm5]`. Move it with nano, reboot.
- `Unable to find simple control 'PCM'`: play one second of silence first (`aplay -q -t raw -f cd -d 1 /dev/zero`).
- `Device or resource busy`: a command used `-D hw:...`; use the default device.
- 100 % not reading -3.00 dB: `sudo rm /var/lib/alsa/asound.state && sudo reboot`, rerun the test script.
- No sound with the card present: meter the amplifier Vin to GND (about 5 V DC); check plugs 12/35/40 and the speaker
  terminal screws.
- Loud or distorted: stop, confirm `max_dB -3.0` in `/etc/asound.conf`; GAIN is unconnected (9 dB), so bypassing the
  ceiling puts about 1.6 W into the 1 W speaker.
- Restore: `sudo cp /boot/firmware/config.txt.bak /boot/firmware/config.txt`.

## Numbers

Output level (dBV) = input (dBFS) + 2.1 dB + gain; 9 dB gain and -3 dB ceiling: 8.1 dBV = 2.5 Vrms = 0.8 W into 8 ohm (speaker rated 1.0 W, max 1.2 W).
The ceiling was -6 dB (0.4 W) until 2026-10-15; Shawn raised it for loudness. Do not go above -3 dB.
Softvol 256 steps over -54..-3 dB: step 128 = -54 + 128/255 x 51 = -28.40 dB.
