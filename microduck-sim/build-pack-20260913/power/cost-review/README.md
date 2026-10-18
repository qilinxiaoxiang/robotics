# Battery and regulator decision

**Phase1nowuses the [current illustrated handbook](../../phase1/START-HERE.html): complete15-servo tethered walking/pickup with Mean Well5V6A motor supply. Camera,audio,onboardbattery,regulatorsandcharger remainPhase2holds. The material below is earlier design/reference evidence and is not the current shopping instruction.**

Verified 2026-09-13. Problems advanced: P5, affordable serviceable hardware; P6, controlled first power-up.

**Earlier onboard candidate: Gens ace7.4V850mAh, PololuD42V110F5 and S13V30F5. All are deferred forPhase2review.** This saves $20 without changing the nominal mounting pattern or the existing 8.5A servo-rail screening point. These regulators were removed from the Phase1cart; no order was placed.

The decision is complete for the specified supervised prototype. It does not certify powered operation before the components have been assembled and measured. [Reproducible selection checks](selection-check.json) distinguish these scopes.

## Selected parts and costs

- **Battery — Gens ace GEA8502S60E2:** $17.99 in the existing procurement quote; nominal 7.4V, full 8.4V, 850mAh, EC2, 57g nominal. The published tolerance envelope is 63×34×22mm. The exact battery and its printed carrier remain selected. [Manufacturer](https://www.genstattu.com/gens-ace-850mah-2s-60c-7-4v-lipo-battery-ec2-plug-car-classic-non-g-tech/)
- **Servo regulator — Pololu #5671 D42V110F5:** $59.95, one unit; 181 units shown in stock at review. It supplies all 15 servos, including the jaw. Nominal size is 43.2×31.8×9mm and mass is 15g. [Manufacturer](https://www.pololu.com/product/5671)
- **Logic regulator — Pololu #4082 S13V30F5:** $17.95, one unit; retained for Pi, camera, USB-powered OpenRB and audio. The Pi sourcing decision remains borrow-first. [Manufacturer](https://www.pololu.com/product/4082)

Battery plus these two boards: **$95.89**, previously $115.89. This subtotal excludes the charger, fuses, connectors, wiring, shipping and tax. The revised Pololu cart is $88.76: $80.27 belongs to this build and $8.49 is a preexisting unrelated switch. Other-store prices remain their earlier dated cart observations, not fresh quotes from this review.

## Why a ready-made 5V battery pack was not selected

A regulated 5V battery pack is a valid architecture: it puts voltage conversion inside the pack. Eliminating a separate board can reduce cost. The deciding requirements are the pack's 5V output current, physical size, protection behavior and availability.

Our existing design walking assumption is 3.8A for the 15 servos plus 1.4A for logic, camera and audio: **5.2A at 5V, or 26W**. The separate 8.5A servo startup point is a candidate-screening load, with pulse duration still to be measured. These are design assumptions, not readings from the duck.

- **Anker Nano A1259:** its USB-C 5V setting is limited to 3A. Higher advertised power uses higher voltages. At 104×52.3×26mm and 215g it also exceeds the current 63×34×22mm battery allowance in every axis-aligned orientation. It fails both output and unchanged-body fit screens. [Official specifications](https://www.anker.com/nz/products/a1259-built-in-cable-power-bank-10000mah)
- **DFRobot DFR0865 UPS HAT:** specifies a higher-current 5.1V/8A architecture using 18650 cells, but the manufacturer's live page is discontinued. It is not a currently purchasable alternative from that source. [Manufacturer](https://www.dfrobot.com/product-2342.html)

These findings reject the checked candidates. They do not establish that every possible 5V pack is unsuitable. A currently available pack that meets the envelope and load criteria at a lower delivered total would change this decision.

The selected raw 2S battery cannot directly power these loads: its fully charged 8.4V exceeds the XL330's 6V operating maximum. XL330 accepts 3.7–6V; 5V is the manufacturer's recommended point, not its only usable voltage. [ROBOTIS specifications](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#specifications)

## Why this cheaper regulator passes the selection screen

The replacement's advertised 11A value is at **42V input**. Its 5V curve is approximately **15A at our 6.6–8.4V input range**. Use 14A as a conservative graph-reading allowance, above the existing 8.5A screening point. Pololu measured the curve at room temperature in still air without an added heat sink; it is not a hot-enclosure rating. [Current graph](https://a.pololu-files.com/picture/0J13892.1200.png?db87d79dd10f6a5b92796be53c6a21cb)

The dropout curve is below about 0.3V through 10A. Against a 5V output, a 6.6V input leaves approximately 1.3V after this allowance, before battery and wiring sag. The existing conservative efficiency budget is retained; the new board's tighter output tolerance is included in the endpoint calculations. [Dropout graph](https://a.pololu-files.com/picture/0J13895.1200.jpg?dd068caf1f54693b08ffeb8602d6343e)

Additional cheaper candidates were checked:

- **Pololu D24V90F5 #2866, $36.82:** its nominal 9A label overstates the applicable low-input curve. Around 2S voltage, the curve is roughly 6.7–7A, below the existing 8.5A screen. It could supply the assumed light walking load, but selecting it would require changing and validating the startup current envelope. [Product and graph](https://www.pololu.com/product/2866)
- **Pololu D42V55F5 #5571:** its low-input curve is approximately 8A, also below the same screen. [Product and graph](https://www.pololu.com/product/5571)
- **Hobbywing UBEC 10A-Car, $24.99:** offers 6/7.4/8.4V, with no 5V setting. Its 6V setting sits at the servo's upper operating limit without an established tolerance margin; it is not a 5V replacement. [Manufacturer](https://www.hobbywingdirect.com/products/ubec-10a)
- **Castle CC BEC 010-0004-00:** its 10A figure is a peak. The 2S–3S continuous figure is 7A and specifies 5mph airflow at 25°C. That does not satisfy our unchanged screening/cooling assumptions. [Manufacturer](https://www.castlecreations.com/en/cc-bec-010-0004-00)

This is a finite comparison of inspected candidates, not a claim of the lowest possible worldwide price.

## Mounting and wiring changes

Both Pololu boards have four M2 holes spaced 38.862×25.4mm, the pattern already used by the printed shelf and fuse carrier. Their published edge and hole-location tolerances are the same. The new dimensioned profile sums to 9.47mm, below the old 11mm reserved height. It is nominally 4g lighter. No print file or Bambu slice is changed for this replacement. [New dimension drawing](sources/5671-dimensions.pdf), [old drawing](sources/2881-dimensions.pdf)

**Underside clearance is tight:** both drawings show 1.8mm of components below the PCB. Existing spacers are 2mm, leaving 0.2mm nominal above the shelf. The old box model does not model individual underside parts. The mounting comparison therefore does not replace checking actual components, solder and spacer edges before tightening. Trim solder tails and stop if the PCB rests on a component. Keep cooling surfaces exposed.

The switch must connect **ENA to GND** to disable the servo supply. Leave **ENB, PFM and PG open**. ENB controls a secondary conversion phase; it is not the shutdown pin. The new board's pad positions differ: use its printed VIN/VOUT/GND labels. Solder the existing 16AWG leads directly into the power holes; no tall terminal blocks are added. [Current wiring](../WIRING.md)

Keep the two regulated 5V outputs separate, with common ground. The motor switch leaves the logic supply running. Unplug EC2 and the balance alarm for complete battery disconnection.

## What is verified and what happens at first power-up

Published voltage/current compatibility, the finite cost choice, nominal mounting geometry and the cart replacement are checked. Reproduce the calculation with `check_selection.py` using the existing CAD Python environment. Source PDFs, curve images and hashes are included.

The 850mAh battery gives roughly **8–11 minutes at the assumed design walking load**; this is a calculated estimate. Runtime, startup voltage dips, braking voltage rise and temperatures require the actual assembled robot. The [first-power procedure](../FIRST-POWER-TEST.md) already specifies current-limited startup, all 15 servo endpoints, Pi voltage, per-cell voltage, temperatures and stop tests. Actual measurement fields remain empty. The heavy-load and all-servos-stalled cases are not accepted continuous operating modes.

RoboClub supplies printing materials, fasteners and general consumables first. No new purchases of those items or the Raspberry Pi are introduced by this revision.
