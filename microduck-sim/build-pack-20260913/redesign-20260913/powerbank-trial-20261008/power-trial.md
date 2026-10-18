# PB1033MI removable onboard power trial

Problem P0/P5: try the owned power bank without moving the existing regulator or changing the robot's 5 V distribution. Authorized by the user on 2026-10-08. Physical power, thermal and walking tests have not been performed.

The tested rear carrier failed at poses where the original robot was clear, including a normal +30° hip pitch. Finite rear/up adjustments retained new collisions. It is excluded from the released V1.4 print package. The electrical procedure below describes an uncommissioned trial; it does not qualify this mounting design.

## Source and available power

The user photo IMG_6952 confirms Xiaomi PB1033MI, 36.5 Wh. [Xiaomi specifications](https://www.mi.com/global/product/xiaomi-33w-power-bank-10000-integrated-cable/specs/) give 80.9 × 65.9 × 26 mm and 20 V / 1.5 A on either the built-in USB-C cable or separate USB-C port. Those ports provide at most 30 W at 20 V; 33 W is a different charging mode. Use one output only: simultaneous ports reduce the combined output to 5 V / 3 A.

The existing 45 W output allocation is a design budget, not measured robot consumption. With an assumed 85% conversion efficiency, a 30 W source would provide about 25.5 W at 5 V. This makes a staged trial reasonable; it does not qualify unrestricted operation.

## Required change to the existing power instructions

The Adafruit 5991 uses HUSB238. Its current request matters as well as its voltage switch. [Adafruit pinouts](https://learn.adafruit.com/adafruit-usb-type-c-power-delivery-switchable-breakout/pinouts) specify ISET closed = 1.25 A, open = 3.25 A. The [HUSB238 datasheet, page 9](https://cdn-learn.adafruit.com/assets/assets/000/125/150/original/husb238_datasheet_full.pdf?1697209172=) selects a source voltage profile only when that profile supports the requested current. Leaving the wall-source 3.25 A request unchanged therefore cannot be assumed to select this bank's 20 V / 1.5 A profile.

- Power-bank trial: only the 20 V voltage switch ON; ISET closed, requesting 1.25 A. This permits a 25 W input contract. An initial 5 V load screen of at most 4 A leaves some conversion margin under the 85% assumption.
- Wall-source full-budget configuration: only 20 V ON; ISET open, requesting 3.25 A, as in the existing design. Verify that the exact charger/cable actually negotiates this profile.
- ISET requests power; it is not a programmable 4 A output current limiter. Measured load and source behavior still determine acceptance.
- Change modes with all sources disconnected. The bank and wall charger are alternative sources at the same 5991 USB-C socket; never parallel their outputs.

A reversible ISET connection can use insulated leads and a removable jumper across the two pads after the original connection state has been checked. Keep it accessible and label BANK / WALL. Availability and assembly of that jumper are unverified. A 4.53 kΩ resistor could request 1.5 A according to the datasheet, but that additional part is not selected or assumed present.

## Mechanical arrangement and connectors

The bank is too large for the original bay, which currently contains DFR1202. The removable rear tray retains that converter location. See mechanical acceptance and the assembly view in `mechanical/` for the final geometry and exact mounting state.

The user's photo and [Xiaomi's product images](https://www.mi.com/global/product/xiaomi-33w-power-bank-10000-integrated-cable/) establish the built-in cable/parking socket at one end, with the independent USB-C and USB-A ports at the opposite end. Both end faces must stay broadly open. Use edge supports and retention around the body; no narrow connector-sized aperture, strap over a cable root, or floor blocking the lower ports. Keep the indicator and button usable.

Place the 5991 near the built-in cable outlet with its USB-C socket facing the accessible cable approach. Leave adjustment space rather than making print geometry depend on an unpublished exact free cable length. The independent lower USB-C port remains available for an ordinary C-to-C cable if needed. Cable reach is to be checked on the physical assembly, without force or pulling on either socket. The bank's integrated cable is never a structural retaining strap.

Bank USB-C → 5991 output → existing fused input/XT30 → DFR1202 → existing 5 V distribution. The bank must not connect directly to the 5 V rail through a 20 V output. Existing servo power bypass and common-ground arrangements remain in force.

## Staged physical acceptance

1. With the robot disconnected, select BANK, plug in the source, and measure the 5991 output. Require the selected 20 V profile before attaching the downstream converter.
2. Check polarity, then verify approximately 5 V at the converter output before connecting electronics. Keep the robot supported so a reset cannot cause a fall.
3. Start with logic/camera and motor torque disabled. Record source voltage/current, 5 V voltage at the load, restarts and temperature. Then test small motor groups while staying inside the initial 4 A screen.
4. Stop and disconnect on voltage collapse, restart, bank shutdown, damaged wiring, or abnormal heating. Increase motion only after the prior condition is stable; record the measured usable load and runtime. This commissioning sequence does not yet authorize a claim of walking-power sufficiency.
5. Check tray retention, end-face insertion access, cable slack and contact throughout the actual motion range before an untethered trial. The added battery changes mass distribution and requires controller/standing checks.

Verified source date: 2026-10-08. AI assistance was used to draft.
