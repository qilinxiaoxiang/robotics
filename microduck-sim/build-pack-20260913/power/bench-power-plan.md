# MicroDuck power: start with existing equipment

**Phase1nowuses the [current illustrated handbook](../phase1/START-HERE.html): complete15-servo tethered walking/pickup with Mean Well5V6A motor supply. Camera,audio,onboardbattery,regulatorsandcharger remainPhase2holds. The material below is earlier design/reference evidence and is not the current shopping instruction.**

Reviewed 2026-09-13. Advances P5 (affordable hardware) and P6 (first-power acceptance). The complete design still has **15 XL330-M288-T servos, including the jaw**. This plan changes the order of power procurement and testing.

## Current decision

Use the existing Mac and Xiaomi 5V/3A power bank for limited desktop bring-up. Defer the onboard LiPo battery, both Pololu regulators, dedicated battery charger/supply and their specialized wiring/protection purchases in the sourcing policy. The deferred quote is $195.13 before shipping/tax; the two regulators account for $77.90. This is deferred expenditure, not a claim that the final walking robot needs no power hardware. Raspberry Pi remains borrowing-first; RoboClub remains the source to check for print materials, fasteners and general consumables.

## What the power-bank label establishes

The supplied product name matches Xiaomi PB1033MI. Confirm the printed model when preparing the physical connection. Its manufacturer lists 5V/3A per relevant output and **5V/3A combined when using multiple ports**, 36.5Wh stored energy, at least 5600mAh delivered at 5V/3A, and dimensions 80.9 x 65.9 x 26mm. The 33W maximum applies to another voltage/current profile; the 5V rating is 15W. The pack stays beside the robot during bench work; it does not fit the existing 63 x 34 x 22mm battery envelope.

A power bank already contains storage, charging/protection and USB voltage conversion. Its regulated 5V output can supply compatible equipment without another 5V regulator, within source and wiring limits. The previous raw two-cell LiPo reaches 8.4V when full, above XL330's 6V operating maximum, so that battery would still require voltage conversion.

## First powered actuator

1. Keep the robot supported. Start with **one unloaded servo**, with no walking policy running and torque initially disabled. The Mac runs configuration/communications; a Raspberry Pi is not needed for this step.
2. Connect Mac USB-C to OpenRB USB-C with a data-capable cable. Motor power comes from the power bank through a proper 5V takeoff to OpenRB's external Terminal VIN, not through OpenRB's USB power path. With all power disconnected, select the **VIN(DXL)** jumper position shown in the ROBOTIS terminal-power diagram.
3. A concrete solder-free takeoff candidate is **Adafruit #5991 HUSB238 switchable USB PD board, $9.95 before shipping/tax**. It requests a USB output profile and brings it to a screw terminal; it does not regulate voltage. With USB disconnected, turn ON only the switch labeled 5V, leaving the others OFF. Do not leave every switch OFF: that requests the highest available voltage, potentially 20V. Before connecting the servo, measure output voltage and polarity. Connect output V+ to OpenRB Terminal VIN positive and GND to negative. Secure/insulate the board and use short suitably rated wire; use club stock first. Do not assume this adapter is already owned or add it to a cart automatically.
4. XL330's listed stall current at 5V is 1.47A; that leaves nominal supply-rating margin for one actuator and OpenRB on a 3A source. This is a specification screen, not a measured transient result. Stop on supply shutdown, unexpected motion, communication resets or endpoint-voltage failure. Do not intentionally stall the actuator.
5. Disconnect power before rewiring. Avoid tying separate positive supply outputs together. OpenRB's USB path has a 500mA fuse, and all its DYNAMIXEL supply ports together are rated 3A; a larger host adapter does not change these downstream limits.

The takeoff board's 5A capability does not turn this Xiaomi bank into a 5V/5A source. A generic USB-C connector breakout without verified current capability is not automatically interchangeable. A power bank's low-load auto-off behavior and the exact cable still need bench observation.

## Full robot and camera stage

Borrow a current-limited laboratory supply with a documented 5V output capability for supported full-robot bring-up. Actual availability is not established. Increase the number of enabled actuators gradually, recording source current, minimum/maximum voltage at servo endpoints and the computer input, startup/deceleration behavior and supply trips. Stay within OpenRB's combined 3A path rating; use separately rated external servo power distribution before testing above it. The existing high-current harness is a future candidate, not required for the one-servo bench.

If a Pi Zero 2 W is borrowed, the Xiaomi pack is also a suitable source candidate for its 5V computer/camera/audio branch using the correct Pi power-input cable. Do not assume the 3A budget is independently available on each bank port. Use only one USB host for OpenRB at a time. The physical Pi endpoint voltage must remain within its permitted range; a long thin cable can lose voltage under load. Move the power source close to the robot and keep the longer cable for data when possible.

A long cable from a Mac does not establish adequate whole-robot power. The Mac's charging wattage is an input specification, and the OpenRB USB bottleneck remains. A USB PD trigger can request a higher profile from a suitable source, but then a converter is again required before 5V loads. Do not connect 9V/12V directly to XL330 or Pi power inputs.

## Where 5.2A came from

The existing `walking_design` scenario in [power_inputs.json](power_inputs.json) is:

- Fourteen body servos: **3.5A assumed aggregate** (equivalent to an assumed average of 0.25A each).
- Jaw servo: **0.3A assumed**.
- Pi, camera, OpenRB communication logic, IMU and audio together: **1.4A allocated**, not a measured component sum.
- Total at 5V: **3.5 + 0.3 + 1.4 = 5.2A**, or **26W**.

These allocations and the 8.5A servo startup scenario were engineering assumptions. They do not establish that every gait needs that current, that 3A necessarily fails, or that the $59.95 board is the cheapest adequate solution. Keep the scenarios as sensitivity cases; use measured operation to set the final supply requirement. A typical idle measurement, slow current display or simulation torque proxy alone cannot settle peaks. No physical measurements were performed in this review.

## Community evidence

AI-FanGe's current README routes a ready-made nominal 6V battery to OpenRB/servos and a 5V regulator or USB source to the Pi. The tutorial frame at 02:12 shows a pack labeled **6.4V, 1800mAh, output 0-3A**, 19 x 37 x 66mm. This supports questioning an assumed 5.2A minimum; it is not a current measurement or approval to apply 6.4V to XL330. The actual voltage discrepancy remains relevant because ROBOTIS specifies a 6V maximum. Keep voltage-error protection enabled; do not copy the README's instruction to remove that shutdown trigger.

SaberOnGo/open-microduck is a useful source-linked hardware reconstruction, not a verified ready-to-purchase clone. Related Rhoban Microban hardware uses an open-source Pollen RPI Robot HAT, with motor interfaces, sensing/audio and power functions combined. Its BOM quotes the custom board at roughly $30, explicitly requiring fabrication; this is not a current single-unit delivered quote or a drop-in replacement for our wiring. These projects show integration alternatives, without proving that custom fabrication is the cheapest first step for this build.

## Sources checked

- [Xiaomi PB1033MI specifications](https://www.mi.com/ph/product/xiaomi-33w-power-bank-10000-integrated-cable/specs/).
- [ROBOTIS OpenRB-150 power paths and terminal jumper](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/#terminal-vin).
- [XL330 specifications](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#specifications).
- [Adafruit #5991](https://www.adafruit.com/product/5991) and [selection/wiring guide](https://learn.adafruit.com/adafruit-usb-type-c-power-delivery-switchable-breakout/pinouts).
- [FanGe repository](https://github.com/AI-FanGe/Microduck-build-tutorial) and [video at 02:12](https://www.youtube.com/watch?v=Vep8AjoCnEM&t=132s).
- [Open Microduck hardware research](https://github.com/SaberOnGo/open-microduck/blob/main/docs/en/hardware/electronics-and-buses.md).
- [Microban BOM](https://github.com/Rhoban/microban/blob/main/docs/bom.md) and [Pollen RPI Robot HAT](https://github.com/pollen-robotics/elec_RPI_Robot_HAT).

Sourcing policy holds apply immediately. Historical store-cart observations still contain deferred parts and block a purchasing handoff until reconciled; the generated reduced BOM is not evidence that those live carts were edited.
