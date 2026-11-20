# XIAO SAMD21 low-voltage cutoff (MicroDuck power V2, PS-2 / PV-2)

The XIAO sits after the Pololu 2813 switch (5 V from the DFR1202), so it runs only while the robot is on. It switches
the robot off by driving D6 high into the Pololu OFF pin (through a 1N4148) when:

- the pack (A0, Pololu VOUT) stays under 6.3 V for 3 s, or
- either cell stays under 3.1 V for 3 s (A1 = middle tap of the XH balance lead = cell 1; cell 2 = pack minus cell 1),
- the button is held 2 s or longer while the robot is on and then let go (shutdown request; the cut fires on release so
  the Pololu never sees ON and OFF together; the press that switched the robot on is not counted).

No cut in the first 3 s after power-on. A balance lead that is unplugged (middle tap near 0 V) pauses the cell check;
the pack check stays. A2 (charge contacts) only sets the `chg` flag. The rules are in `xiao_cutoff/cutoff_logic.h`.

## Files

- `xiao_cutoff/xiao_cutoff.ino`: the sketch; calibration constants at the top (`VREF`, divider ratios, `*_TRIM`).
- `xiao_cutoff/cutoff_logic.h`: the decision logic, no Arduino dependency.
- `test/run_tests.sh`: builds and runs `test/test_cutoff_logic.cpp` with g++ (healthy, slow sag, weak cell bottom and
  top, dips under 3 s, hysteresis band, charging on the dock, flat pack at power-on, button, balance lead unplugged, latch).
- `compile-log.txt`: the arduino-cli compile for the Seeeduino XIAO; `test/test-output.txt`: the last host test run.

## Flash (on the Mac, the XIAO on its own USB-C cable, before it is soldered into the harness)

```sh
arduino-cli core update-index --additional-urls https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json
arduino-cli core install Seeeduino:samd --additional-urls https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json
cd ~/code/robotics/microduck-sim/guide/firmware/xiao-cutoff-20261120
arduino-cli compile --fqbn Seeeduino:samd:seeed_XIAO_m0 --output-dir build xiao_cutoff
arduino-cli board list                      # the XIAO shows as /dev/cu.usbmodemXXXX
arduino-cli upload --fqbn Seeeduino:samd:seeed_XIAO_m0 -p /dev/cu.usbmodemXXXX --input-dir build
arduino-cli monitor -p /dev/cu.usbmodemXXXX -c baudrate=115200
```

Arduino IDE instead: Preferences, Additional boards manager URLs = the Seeed URL above; Boards Manager, install
"Seeed SAMD Boards"; Tools, Board = "Seeeduino XIAO"; open `xiao_cutoff/xiao_cutoff.ino`; Upload; Serial Monitor at
115200. If the port does not appear, short the two RST pads twice quickly (bootloader mode) and upload again.

On USB alone every input reads near 0 V, so the status line shows `pack=0.00`. After 3 s the cutoff fires
(`cut=1 reason=pack_low`) and the orange LED stays on: that is the correct result with no battery.

## Live feedback

- Orange user LED (pin 13): one short blink a second = watching, all fine; a second short blink = dock voltage on the
  contacts; fast blink (5 Hz) = undervoltage being timed, or the button held long enough (let go to switch off);
  steady on = cutting.
- Serial, 115200 baud, every 0.5 s: `t=… pack=7.92 c1=3.96 c2=3.96 dock=0.00 on=0.00 xh=1 chg=0 btn=0 held=0 grace=0
  low_ms=0 cut=0 reason=- raw=…` (raw = averaged 12-bit counts of A0..A3, for calibration).

USB caveat once the XIAO is in the harness: its 5V pad is the USB VBUS (Seeed wiki pin table) and it is wired to the
DFR1202 5 V output, which also feeds the button ring and plug 4 (the A7Z). A USB cable from the Mac then back-feeds
that rail: the ring lights from USB with the robot switched off, and with plug 4 connected the Mac port would try to
power the A7Z. Read the serial line in the harness only with plug 4 unplugged, and trust the ring only with USB out.

## Calibrate

With the battery on and the robot switched on, measure the pack at the XT30 and the middle cell at the XH plug with a
meter; set `PACK_TRIM = meter / printed pack` and `MID_TRIM = meter / printed c1` and flash again. A 1 % resistor
error moves the 6.3 V trip about 0.06 V; the PS-2 acceptance is a trip at 6.3 V +- 0.1 V on a bench supply ramp.
