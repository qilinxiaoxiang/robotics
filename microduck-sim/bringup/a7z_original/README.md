# A7Z-PINS-ORIGINAL

The pin page from before the microphones (f069cd7, 2026-10-21): amp and touch board plug straight into the A7Z, no gather point or breadboard. Amp leads in their as-built colours (Vin blue, BCLK white, LRC purple, GND black, DIN orange; Shawn 2026-10-26).

Build: copy `../a7z/img` and `../a7z/sources` here, then `~/.venvs/microduck-cad/bin/python build_a7z_pages.py` writes `../A7Z-PINS-ORIGINAL.html`; `node probe_orig.mjs` checks 1280 and 390 px. Deploy: copy into leg-guide-20261006, rsync to mac-mini:code/microduck-guide/, compare sha256 with the live page.
