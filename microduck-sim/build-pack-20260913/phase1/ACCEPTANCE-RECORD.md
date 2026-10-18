# MicroDuck Phase 1 physical acceptance record

Status: **Not yet physically tested.** Fill this record at the bench. Keep the full handbook's limits; this sheet is a results record, not replacement instructions.

## Resources and build

- Test date and operator:
- Borrowed Pi model / OS / header / card:
- Actual printer, nozzle, plate and PLA:
- Printed jaw/support fit result:
- Actual installed M2.6 × 6 TAP screws and source:
- Finished robot mass, without external power bank, receiver and converter:
- Recorded fastener lengths / wire strain relief / cable clearance:
- Runtime ZIP version or SHA-256:

## A. Unpowered wiring

- Bank PB1033MI; receiver 5991; converter DFR1202; negotiated 12V and regulated 5V:
- Correct terminal/MicroB polarity; F0 10A and F1-F9 3A:
- Eight branches isolated individually, DATA-only connections verified:
- OpenRB USB alone leaves motor VDD unpowered:
- Both compact MicroB plugs pass continuity, insulation and envelope checks:
- IMU physical pins 1 / 6 / 3 / 5 and labels verified:
- Result, defects corrected and photo reference:

## B. Measured supply

- Distributed dummy loads at 1A, 3A and 5A; farthest connector voltage:
- Pi 30-minute input minimum/maximum (required 4.75–5.25V):
- Logic resets, USB disconnects or bank auto-off (required none):
- Startup, stopping and jaw transient voltage trace reference:
- Loaded servo endpoint minimum/maximum (required 4.0–5.5V during task):
- Actual input current (at most 2.5A at 12V) and combined 5V current (at most 5A, including logic):
- Sampled total / group / body-motor current maxima (5A / 2.25A / 1.3A screens):
- Hot connector, cable or protection event:
- Result and repairs:

## C. Individual motors, jaw and sensor

- IDs1–15 individually labeled; location, direction, zeros and small-motion tests:
- All eight supported branch tests:
- Sensor-only upright, forward, backward, left, right and return-to-upright checks:
- Stored IMU calibration file and log reference:
- Actual jaw open/closed endpoints and current settings:
- Foam sample mass (at most2g), gripping thickness (8mm) and width (about20mm):
- Five jaw cycles and five three-second grip trials:
- Result and repairs:

## D. Standing, walking and stopping

- Actual Pi loop timing and sensor age evidence:
- Thirty-second standing result, support not carrying the robot:
- Five 0.3m walk / three-second stop trials:
- Failure count and observed cause:
- Tether remained slack, clear of feet and did not help balance:
- Result and logs/video:

## E. Complete walk-up and pickup

For each trial record: approach, stop, lower, grip, lift at least10mm, hold at least3seconds, release; power/thermal faults; any human or cable assistance.

- Fixed target support height above floor:
- Trial1:
- Trial2:
- Trial3:
- Trial4:
- Trial5:
- Video and voltage/current log references:
- Five consecutive full passes achieved:

A failed attempt resets the consecutive-pass count. Do not claim floor pickup from an elevated-target trial. Camera perception, autonomous approach, arbitrary objects and walking while carrying remain Phase2 work.

- Simultaneous loaded Pi endpoint minimum/maximum:
- Receiver voltage under load; no PD restart:
- Converter case temperature after 30 minutes; stable final five minutes; at most 60°C:
- Emergency master disconnect and normal Pi shutdown demonstrated:
