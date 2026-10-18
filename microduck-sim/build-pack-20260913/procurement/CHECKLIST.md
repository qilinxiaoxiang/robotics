# Remaining procurement and required resources

Revision: microduck-charger-camera-r3. Remaining selected merchandise: **$114.61**, 15 lines at DigiKey. The original servo/controller order was refunded. Three OMX-AI kits were subsequently ordered: two provide 16 XL330-M288-T and 4 OpenRB-150 for the unchanged 15/1 requirement; the third remains intact. See the order mapping below.

All 15 DigiKey lines were verified after browser reload. Merchandise $114.61; estimated shipping $4.99; estimated tariff $10.28; displayed estimate $129.88. Sales tax is not shown in the cart. No order was placed. [Actual cart evidence](cart-status-r3.json).

## OMX-AI order

Order 2034348: 3 × [ROBOTIS OMX-AI](https://robotis.us/products/omx-ai-us), SKU 905-0049-000, $343.85 each / $1031.55 kit merchandise. Two kits supply 16 XL330-M288-T and 4 OpenRB-150 for MicroDuck; allocate 15 servos and one controller. The third kit stays intact for leader/follower experiments. One SMPS 12V 5A + SMPS2DXL + 3-wire cable set from a duck-allocated kit is the robot wall supply. Shipping protection $10.45; UPS 2nd Day Air $44.27; tax $0.00; total $1086.27. Payment is user-reported and merchant-confirmed. Received: the user photo of 2026-10-13 shows XL330 servos with ID 3 and ID 15 stickers assembled on the robot and an OpenRB-150 on the bench. No tracking record is needed; unit counts were not taken from the photo. [Merchant confirmation](order-2034348-confirmation.json). The earlier two-kit unpaid checkout remains a historical snapshot. The phone-reported stock count of ten is not independent inventory verification. Other sourcing holds remain unchanged.

## Smart servo — included

ROBOTIS DYNAMIXEL XL330-M288-T / 902-0163-000. Installed: 15 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Received with the OMX-AI kits (user photo 2026-10-13); allocated to the duck.

Allocated from two of the three OMX-AI kits of order 2034348, received (user photo of assembled servos, 2026-10-13). Do not purchase duplicate components. Engineering demand remains 15 servos and one controller; the third kit is reserved intact for separate leader/follower experiments. Sourcing note recorded with the decision: Allocated from two of three merchant-confirmed OMX-AI kits. Not yet received; do not purchase duplicate components. Engineering demand remains 15 servos and one controller; the third kit is reserved intact for separate leader/follower experiments.

[Selected or reference supplier](https://robotis.us/products/dynamixel-xl330-m288-t)

## Servo bus controller — included

ROBOTIS OpenRB-150 (included in OMX-AI). Installed: 1 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Received with the OMX-AI kits (user photo 2026-10-13); allocated to the duck.

Allocated from two of the three OMX-AI kits of order 2034348, received (user photo of assembled servos, 2026-10-13). Do not purchase duplicate components. Engineering demand remains 15 servos and one controller; the third kit is reserved intact for separate leader/follower experiments. Sourcing note recorded with the decision: Allocated from two of three merchant-confirmed OMX-AI kits. Not yet received; do not purchase duplicate components. Engineering demand remains 15 servos and one controller; the third kit is reserved intact for separate leader/follower experiments.

[Selected or reference supplier](https://robotis.us/products/openrb-150-starter-kit)

## Onboard computer — borrow_first

First-generation Raspberry Pi Zero W with soldered 40-pin header; alternative Pi 3 Model B V1.2. Installed: 1 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Pi and accessories remain borrow-first. User confirmed both board identities. Validate populated-board and connector fit, loaded power, camera streaming and USB operation before installation. Existing CAD only represents the Zero form factor; Pi 3 mounting and power are not validated. The retained supplier quote is historical only. Sourcing note recorded with the decision: Deferred; determine available board and accessories. An unpurchased kit supplies nothing.

[Selected or reference supplier](https://www.canakit.com/raspberry-pi-zero-2-w.html?cid=usd)

## Monocular camera — buy

Raspberry Pi SC1224 Camera Module 3 Wide, visible-light IR-filter IMX708. Installed: 1 each; external/bench: 0; remaining purchase packages: 1; merchandise: $35.00.

Required in current design.

Required for camera-guided pickup. SC1224 is the Wide visible-light/IR-filter version. Existing SC1892 and mount geometry describe the Zero-form-factor baseline only; confirm the selected Pi camera interface and cable before connecting.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/raspberry-pi/SC1224/17278644)

## Camera flexible flat cable — buy

Raspberry Pi SC1892 200mm camera FFC, 15-pin to 22-pin. Installed: 1 lead; external/bench: 0; remaining purchase packages: 1; merchandise: $1.00.

Required in current design.

Retain the existing 200 mm SC1892 15-to-22 cable. Use only after confirming the exact borrowed Pi connector; this is not a universal Pi 3/Zero cable requirement. Preserve a service loop through head motion; no soldering.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/raspberry-pi/SC1892/21658272)

## Body inertial measurement unit — buy

Adafruit BNO085 / 4754. Installed: 1 each; external/bench: 0; remaining purchase packages: 1; merchandise: $29.50.

Required in current design.

Board 25.6x22.7x4.6mm; reserved envelope 28x25x8mm. A moving head mount cannot substitute for a trunk measurement.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/adafruit-industries-llc/4754/13426653)

## IMU four-wire adapter — buy

Adafruit 4397 STEMMA QT/Qwiic JST-SH4 to female sockets, 150mm. Installed: 1 lead; external/bench: 0; remaining purchase packages: 1; merchandise: $0.95.

Required in current design.

Pi physical pins 1=3.3V, 9=GND, 3=SDA, 5=SCL. Physical pin 6 is now one of the two Pi power returns; do not double-occupy it. Validate actual I2C timing. Extend the selected 150mm cable to 250mm: retain approximately 100mm at the JST-SH end, remove its original Pi sockets, and splice four club-sourced approximately 150mm precrimp female tails, individually insulated. Measure finished length and motion clearance; do not claim the original 150mm cable reaches.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/adafruit-industries-llc/4397/10824270)

## Digital audio amplifier — buy

Adafruit 3006 MAX98357A I2S mono amplifier. Installed: 1 each; external/bench: 0; remaining purchase packages: 1; merchandise: $5.95.

Required in current design.

Reserved envelope 22x21x12mm. Included terminal/header require soldering. Do not substitute the newer stereo board.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/adafruit-industries-llc/3006/6058477)

## Speaker — buy

Same Sky CMS-30204-18SP, 8 ohm 1W oval speaker. Installed: 1 each; external/bench: 0; remaining purchase packages: 1; merchandise: $1.34.

Required in current design.

30x20x4.2mm maximum body, 8 ohm, 1W. Solder two speaker wires to its pads and clamp their other ends in the amplifier output terminal. Neither speaker output is ground. Gain resistor and software volume limit remain required.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/same-sky-formerly-cui-devices/CMS-30204-18SP/29778290)

## Onboard battery — review_hold

Gens ace GEA8502S60E2, 850mAh 2S 60C EC2. Installed: 1 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

Nominal 58x32x20mm; tolerance envelope 63x34x22mm. The frozen carrier fits this exact battery. Do not substitute a hard case, larger capacity or different connector. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.genstattu.com/gens-ace-850mah-2s-60c-7-4v-lipo-battery-ec2-plug-car-classic-non-g-tech/)

## Servo voltage regulator — review_hold

Pololu 5671 D42V110F5, fixed 5V. Installed: 1 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

43.2x31.8x9mm nominal; dimensioned profile sum 9.47mm. Same M2 spacing 38.862x25.4mm as the former board, unchanged 1.8mm underside projection. Use ENA-to-GND disable; leave ENB/PFM open. Approximately 15A on the manufacturer 2S-input curve is not an enclosure rating. See power/cost-review/README.md. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.pololu.com/product/5671)

## Logic voltage regulator — review_hold

Pololu 4082 S13V30F5, fixed 5V. Installed: 1 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

22.9x22.9x9.7mm; input fuse precedes VIN. Purchase one fitted prototype for loaded-voltage screening. Worst-case 4.85V source with the documented lead/contact assumptions reaches only 4.775V at the Pi; no guaranteed 4.8V margin. See power/PURCHASE-READINESS.md. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.pololu.com/product/4082)

## Servo-disable switch — review_hold

Pololu 1408 Mini Slide Switch 3-pin SPDT, 3-pack. Installed: 1 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

Rated 0.3A; never carry main current through it. Its saddle is integrated in the alarm carrier, secured by one tie no wider than 2.0mm and no thicker than 0.8mm. No extra print/screw. Complete disconnection requires EC2 removal followed by the alarm balance plug. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.pololu.com/product/1408)

## Main fuse — buy

Littelfuse 0251010.MXL, 10A axial / DigiKey F2320-ND. Installed: 1 each; external/bench: 0; remaining purchase packages: 1; merchandise: $1.24.

Not used: fuses were dropped from the whole robot and the tether (owner decision 2026-10-11/12; the live guide marks them not used). Received in DigiKey order 101587695 and kept as owned stock.

One installed, no purchased spare. Supplemental motor-feeder protection; a current-limited source may not open this fuse.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/littelfuse-inc/0251010-MXL/700757)

## Branch fuses — buy

Littelfuse 0251003.MXL, 3A axial / DigiKey F2315-ND. Installed: 9 each; external/bench: 0; remaining purchase packages: 9; merchandise: $9.22.

Not used: fuses were dropped from the whole robot and the tether (owner decision 2026-10-11/12; the live guide marks them not used). Received in DigiKey order 101587695 and kept as owned stock.

Nine installed, no purchased spare: eight motor groups covering all fifteen servos and one Pi branch. Nine at the five-piece price tier cost $9.22; ten cost $9.45 before tariff.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/littelfuse-inc/0251003-MXL/700737)

## Per-cell low-voltage alarm — review_hold

HobbyKing DL-Volt-Alarm 2S–4S. Installed: 1 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

38x25x11mm, 7g. Actual cart selects the Global warehouse, with 10g shipping weight. Freight and delivery date remain unknown. It is not a BMS and does not disconnect power; attended operation only. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://hobbyking.com/en_us/hobbykingtm-lipoly-low-voltage-alarm-2s-4s.html?___from_store=en_us)

## 2S balance extensions — review_hold

Buddy RC 8-inch 2S JST-XH, 3 pins, silicone wire. Installed: 1 lead; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

Buy two 3-pin JST-XH 2S leads, not a 4-pin 3S lead. Buddy explicitly specifies JST-XH; the one-cent-cheaper alternative had conflicting XT60/60A copy. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.buddyrc.com/products/8-2s-jst-xh-balance-extension-cable)

## Charging and onboard EC2 adapters — review_hold

Gens ace GEAX6F2E2M XT60 female → EC2 male. Installed: 1 lead; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

Buy two. Cut XT60 off the onboard one; retain EC2 male and at most 50mm original copper wire, soldered to the 16AWG main harness. Do not coil the full approx. 21g adapter inside the duck. Keep the charging adapter intact. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.genstattu.com/gens-ace-xt60-female-to-ec2-charging-cable/)

## Main power wire — club_supply

OutOfDarts 16AWG tinned-copper silicone wire, red+black pair by foot. Installed: 0.3 m per color; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Obtain at least 0.5m red and 0.5m black 16AWG copper from RoboClub for short converter-output and star pieces, including preparation allowance. Long run is separate 18AWG high-voltage tether; no wire purchase is released. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://outofdarts.com/products/silicone-stranded-hobby-wire-red-black-pair?variant=14314617634858)

## Branch power wire — club_supply

Pyrodrone 20AWG Silicone Wire, 1m red + 1m black/set. Installed: 2.0 m per color; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Obtain 2.5m red and 2.5m black 20AWG copper from RoboClub. Eight 250mm feeds use 2.0m per color; remaining 0.5m is cut/splice allowance. Each feed includes 20mm before its fuse and 230mm after. Retain original 90mm 21AWG servo tails as individual injections; source calculation conservatively screens them as 22AWG. F7/F8 Y positions follow the current full-motion harness reach result. No new wire purchase is released. The final digital motion check passes all eight250mm group feeds: worst routed feed185.331mm below the190mm allowance after20mm fuse-input and40mm service allocation; independent90mm tails have worst route51.773mm below their60mm allowance after30mm service allocation. This is geometry evidence, not physical routing acceptance. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://pyrodrone.com/products/1ft-silicone-wire-choose-color-and-gauge?variant=16927272861739)

## Signal and audio leads — club_supply

Eight compatible precrimp signal tails plus ordinary insulated 26AWG DATA extension wire. Installed: 8 precrimp lead; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Keep four audio signal leads: BCLK, LRCLK, DATA and signal GND; obtain preterminated female sockets compatible with the Pi header. Three I2S signals alone omit the reference ground. Motor DATA/GND reference tails are also needed; never use these fine wires as the motor power trunk. Include four approximately 150mm precrimp female IMU extension tails, final cable250mm after splice, in addition to the four audio signal tails. Add one finished 400mm DATA-only link from ID1 to ID6: reuse its original180mm cable and splice approximately220mm ordinary insulated26AWG signal wire. Allocate0.3m club wire and two small splice heat-shrink sleeves. Route up the right leg, across the trunk and down the left leg, clear of moving joints; do not span the gap between the feet. No motor power travels in this extension. Verify final400mm length after termination and end-to-end continuity. See ../redesign-20260913/motor-harness-reach.json. These are club resources; no purchase is released. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.adafruit.com/product/1950)

## Pi Micro-B connectors — optional

Adafruit 1826 USB DIY Slim MicroB plug. Installed: 0 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

Historical alternate only: selected design feeds Pi through GPIO and uses a finished OTG data adapter. No DIY Micro-B plug purchase is required. Sourcing note recorded with the decision: Superseded by GPIO power and a finished OTG data adapter. Do not purchase or modify USB fine-pitch pins for the selected route.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/adafruit-industries-llc/1826/5629443)

## USB host adapter — borrow_first

Raspberry Pi SC0727 Micro-B OTG male to USB-A female finished adapter. Installed: 1 lead; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Required installed data adapter, sourced from existing Pi accessories first. Micro-B male plugs into the Pi USB data socket; USB-A female accepts the intact 4472 USB-A male. Reference fallback price $1.54; hold remains until exact missing stock and a changed sourcing decision are recorded. Sourcing note recorded with the decision: Deferred; determine available board and accessories. An unpurchased kit supplies nothing.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/raspberry-pi/SC0727/15298144)

## OpenRB USB data cable — buy

Adafruit 4472 USB-A to USB-C data/sync cable, 6 inch. Installed: 1 lead; external/bench: 0; remaining purchase packages: 1; merchandise: $2.95.

Required in current design.

USB-A male plugs into SC0727 USB-A female; USB-C male plugs into OpenRB USB-C female. Do not cut either end. OpenRB logic is powered through USB while servo power bypasses the controller high-current path. Validate enumeration and sustained bus communication.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/adafruit-industries-llc/4472/11587359)

## System microSD card — borrow_first

32GB microSD; reuse or borrow a compatible card. Installed: 1 card; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

No kit has been purchased. Confirm the available board/accessory and physical compatibility before installation. The retained supplier quote is a historical reference only. Sourcing note recorded with the decision: Deferred; determine available board and accessories. An unpurchased kit supplies nothing.

[Selected or reference supplier](https://www.canakit.com/raspberry-pi-zero-2-w.html?cid=usd)

## LiPo balance charger — review_hold

HOTA T6. Installed: 0 each; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

Select LiPo, 2S and 0.8A, not LiHV. Current setting increments are 0.1A. It uses DC/USB-C PD input; the store title AC/DC does not mean a wall supply is included. A prior relocation notice leaves actual dispatch timing unconfirmed; HeliDirect has the same model at $44.90. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.racedayquads.com/products/hota-t6-pd-15a-1-6s-ac-dc-smart-charger?variant=41289248276593)

## Charger wall supply — review_hold

Raspberry Pi 45W USB-C US / SC1731 / Adafruit6320. Installed: 0 each; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

20V/2.25A, with a 1.5m USB-C lead; no extra C-to-C cable. Charging output is 2x4.2x0.8=6.72W. This is not a direct Raspberry Pi power supply. A compatible existing 20V PD supply can be reused. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.adafruit.com/product/6320)

## Pi bench supply — borrow_first

Compatible 5V MicroUSB bench supply; borrow or reuse. Installed: 0 each; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

No kit has been purchased. Confirm the available board/accessory and physical compatibility before installation. The retained supplier quote is a historical reference only. Sourcing note recorded with the decision: Deferred; determine available board and accessories. An unpurchased kit supplies nothing.

[Selected or reference supplier](https://www.canakit.com/raspberry-pi-zero-2-w.html?cid=usd)

## USB-C microSD reader — borrow_first

Adafruit5212 USB Type C microSD reader/writer. Installed: 0 each; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse a working reader or an SD adapter and computer slot. Existing ownership is not verified.

[Selected or reference supplier](https://www.adafruit.com/product/5212)

## Spare servo cables — optional

ROBOTIS X3P 180mm 10pcs / 903-0249-000. Installed: 0 lead; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

The supplied 15 cables already yield 30 JST ends. The verified retail package contains ten cables; two loose cables are not assumed available at a prorated price.

[Selected or reference supplier](https://robotis.us/products/robot-cable-x3p-180mm-10pcs)

## Included servo cables — included

ROBOTIS X3P180mm, JST EHR-3 / 21AWG. Installed: 15 lead; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

15 power-input ends + 14 DATA-output ends + 1 OpenRB end. Remove VDD/GND from servo outputs; remove VDD from OpenRB but retain GND to the star point. Never bypass a branch fuse.

## Included M2x6 tapping screws — included

ROBOTIS M2×6 TAP. Installed: 0 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical pack-content reference only; current installation counted in separate TAP rows.

Historical original individual-servo pack content only; original order was refunded. Current OMX-AI receipt and screw inventory are unverified. Current installed requirements are separate tap_m2_* rows; do not count this as available stock. Sourcing note recorded with the decision: Historical original individual-servo pack content only; original order was refunded. Current OMX-AI receipt and screw inventory are unverified. Current installed requirements are separate tap_m2_* rows; do not count this as available stock.

## Included M2x8 tapping screws — included

ROBOTIS M2×8 TAP. Installed: 0 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical pack-content reference only; current installation counted in separate TAP rows.

Historical original individual-servo pack content only; original order was refunded. Current OMX-AI receipt and screw inventory are unverified. Current installed requirements are separate tap_m2_* rows; do not count this as available stock. Sourcing note recorded with the decision: Historical original individual-servo pack content only; original order was refunded. Current OMX-AI receipt and screw inventory are unverified. Current installed requirements are separate tap_m2_* rows; do not count this as available stock.

## Audio branch fuse — buy

Littelfuse 0251.500MXL,0.5A axial / DigiKey F2311-ND. Installed: 1 each; external/bench: 0; remaining purchase packages: 1; merchandise: $1.37.

Not used: fuses were dropped from the whole robot and the tether (owner decision 2026-10-11/12; the live guide marks them not used). Received in DigiKey order 101587695 and kept as owned stock.

One installed, no purchased spare. Keep the 0.5A fuse before the direct 24AWG audio power pair; insulate all solder joints and provide strain relief.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/littelfuse-inc/0251-500MXL/700707)

## Detachable audio power connector — optional

Adafruit 1131 JST-PH compatible 2-pin extension, 500mm/26AWG. Installed: 0 pair; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Removed from the cost-minimal build: direct existing 24AWG wires replace this service connector.

Omit the JST-PH service connector. Use the already-required club-sourced 24AWG pair directly from fused 5V/common ground to amplifier VIN/GND; leave a service loop. Head removal requires disconnecting the direct audio supply joints. Sourcing note recorded with the decision: Omit the JST-PH service connector. Use the already-required club-sourced 24AWG pair directly from fused 5V/common ground to amplifier VIN/GND; leave a service loop. Head removal requires disconnecting the direct audio supply joints.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/adafruit-industries-llc/1131/5761282)

## Audio power wire — club_supply

Pyrodrone24AWG silicone wire,1m red+1m black. Installed: 0.25 m per color; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Club-sourced 24AWG copper: use up to250mm per power conductor directly from fused5V/common ground to amplifier VIN/GND. Retain a slack service loop, insulate and strain-relieve solder joints. Separate speaker-output pair; neither speaker output connects to GND. No JST-PH purchase or substitute purchase is required. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://pyrodrone.com/products/1ft-silicone-wire-choose-color-and-gauge?variant=16927242911787)

## Amplifier gain resistor — buy

YAGEO MFR-25FBF52-100K,100kΩ±1%,0.25W axial / DigiKey100KXBK-ND. Installed: 1 each; external/bench: 0; remaining purchase packages: 1; merchandise: $0.10.

Required in current design.

One fitted 100k resistor from GAIN to VIN for 3dB gain; no purchased spare. Keep the software volume ceiling for the 1W speaker.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/yageo/MFR-25FBF52-100K/13473)

## Pi face-panel tapping screws — club_supply

Harfington/Uxcell a16060200ux0367,M2.5×6mm stainless Phillips pan self-tapping,100pcs. Installed: 8 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Selected head diameter4mm, height1.5mm. Current 7x52x15mm GPIO housing-and-exit envelope leaves1mm nominal clearance. M2.5x6 TAP gives4.4mm pilot engagement; no nuts. Larger4.5mm heads collide with old54mm receiving envelope. Four additional S1–S4 support screws are now counted by current head-closure audit; total eight installed, receipt remains unverified. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.harfington.com/products/p-1033403?variant=42182571000057)

## M2x5 machine screws — club_supply

M2-0.4×5mm A2 Phillips pan, DIN7985A/ISO7045. Installed: 2 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Use the exact length and pan head. Ten head mounting locations passed the 4mm diameter / 1.72mm maximum DIN head envelope check; countersunk heads are not approved. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://monsterbolts.com/products/mach-phil-pan-a2-m2?variant=38436353164)

## M2x8 machine screws — club_supply

M2-0.4×8mm A2 Phillips pan, DIN7985A/ISO7045. Installed: 0 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Superseded: camera now M2x10 for full nut engagement; rear cover alone now M2x6.

Historical reference only. Current connection requirements are in ../redesign-20260913/assembly-fasteners.json. No current installation or purchase allocation. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://monsterbolts.com/products/mach-phil-pan-a2-m2?variant=38436354188)

## M2x12 machine screws — club_supply

M2-0.4×12mm A2 Phillips pan, DIN7985A/ISO7045. Installed: 0 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Unused old small-regulator cover; no small regulator in current design. Cover screws interfere with retained motors.

Historical reference only. Current connection requirements are in ../redesign-20260913/assembly-fasteners.json. No current installation or purchase allocation. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://monsterbolts.com/products/mach-phil-pan-a2-m2?variant=38436355020)

## M2x18 machine screws — club_supply

M2-0.4×18mm A2 Phillips pan, DIN7985A/ISO7045. Installed: 4 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Use the exact length and pan head. Ten head mounting locations passed the 4mm diameter / 1.72mm maximum DIN head envelope check; countersunk heads are not approved. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://monsterbolts.com/products/mach-phil-pan-a2-m2?variant=38436768844)

## M2x20 machine screws — club_supply

M2-0.4×20mm A2 Phillips pan, DIN7985A/ISO7045. Installed: 4 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Use the exact length and pan head. Ten head mounting locations passed the 4mm diameter / 1.72mm maximum DIN head envelope check; countersunk heads are not approved. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://monsterbolts.com/products/mach-phil-pan-a2-m2?variant=38436355596)

## M2x25 machine screws — club_supply

Uxcell a16110800ux1019 M2-0.4×25mm 304 Phillips pan,25 sets. Installed: 2 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Live quote $9.07 supersedes the stale $7.95 search value. Set includes 25 nuts, flat washers and spring washers; only use specified parts, without adding spring washers. Head diameter 4mm; total length 26mm, under-head length 25mm. Measure quality/tolerances. Origin/delivery unknown. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.harfington.com/products/p-1098147?variant=42122298130681)

## M2 hex nuts — club_supply

M2-0.4 A2 DIN934. Installed: 14 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Fourteen installed M2-0.4 nuts, nominal1.6mm thickness; club stock, no assumed screw-pack supply. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

## M3x10 button-head screws — club_supply

M3-0.5×10mm socket button head ISO7380. Installed: 2 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Use a 2mm hex key; not countersunk. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://monsterbolts.com/products/socket-button-b12-9-m3?variant=35216415564)

## M3x20 button-head screws — club_supply

M3-0.5×20mm socket button head ISO7380. Installed: 1 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Use a 2mm hex key; not countersunk. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://monsterbolts.com/products/socket-button-b12-9-m3?variant=35216416332)

## M3 hex nuts — club_supply

M3-0.5 A2 DIN934. Installed: 3 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

 Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://monsterbolts.com/products/nuts-din934-a2?variant=40341941715027)

## M3 flat washers — club_supply

M3 DIN125A, ID3.2×OD7×thickness0.5mm. Installed: 4 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Base washers must be 0.5mm thick; arbitrary thickness is not approved. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://monsterbolts.com/products/washers-din125a-a2?variant=31351045652563)

## Integral regulator spacers — included

4 integral printed standoffs,height2mm. Installed: 0 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

Historical Pololu-only integral standoffs. The new DFR1202 open insert needs no added spacers or board screws; do not install these as separate current parts.

## Narrow nylon ties — club_supply

Panduit PLT.6SM-C / 298-1016-ND, nominal 71×1.8×0.8mm. Installed: 12 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Club stock allocation: eight short ties for four audio rings, two ties at converter board edges clear of inductor and rear thermal pad, and two for USB/harness strain relief. Remove the old alarm/EN-switch use. Audio slots2.4x1.2mm and converter restraints require width<=2.4mm and thickness<=1.0mm; selected narrow1.8x0.8mm fits. Confirm actual routes before trimming. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/panduit-corp/PLT-6SM-C/280029)

## Battery ties — club_supply

Panduit PLT3S-C / 298-1033-ND, nominal 292×4.8×1.3mm. Installed: 2 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Club-sourced two straps, retaining the original top/bottom routes. These retain the converter insert in the current tethered build; a future battery needs its own removable carrier review. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/panduit-corp/PLT3S-C/280046)

## Insulating heat-shrink tubing — club_supply

Adafruit 4559 heat-shrink assortment. Installed: None set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Selected Adafruit 4559 at $9.95. Confirm actual sizes and temperature rating against WIRING before use; adding the kit to a cart is not material acceptance. Main joints also require strain relief. Include two additional small sleeves for the two solder splices in the ID1-to-ID6 DATA extension. Fit sleeve diameter to26AWG insulation and cover each joint independently; this adds no purchased kit. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.adafruit.com/product/4559)

## Insulating cushioning foam — club_supply

3M (TC) 4492W-0.5-5 / 1067-4492W-0.5-5-ND, 1/2 inch × 5 yards, 0.787mm nominal. Installed: None roll; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Retain the battery-facing release liner where specified, approximately 0.08mm allowance; measure total installed stack at most 1.0mm. Do not obstruct regulator cooling. Actual foam/adhesive compression is a first-fit check. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/3m-tc/4492W-0-5-5/2649500)

## Polyimide insulating tape — club_supply

Adafruit 3057 polyimide tape. Installed: None roll; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Selected Adafruit 3057 at $4.95. Verify total tape thickness at most 0.1mm on receipt. Cut to fit without blocking contact or moving surfaces. On the converter insert use only a thin edge liner; total liner thickness must fit the0.3mm side clearance. Leave the rear thermal pad and airflow unobstructed. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.adafruit.com/product/3057)

## Solder — club_supply

Adafruit145,60/40 no-clean rosin core0.3mm,100g. Installed: None roll; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

One 100g roll; reuse matching material if available. Actual use follows cut-to-fit harness fabrication. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.adafruit.com/product/145)

## Electronics flux — club_supply

Adafruit 3468 electronics flux. Installed: None each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Selected Adafruit 3468 at $7.95. Follow the actual flux cleaning/use instructions. This procurement selection does not prove solder quality. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.adafruit.com/product/3468)

## Desoldering braid — club_supply

Chip Quik SOLDERWICK1.5 / 315-SOLDERWICK1.5-ND, 1.5mm × 1.524m. Installed: None each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Selected 1.5mm braid; follow actual product use instructions. Procurement does not establish solder quality. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/chip-quik-inc/SOLDERWICK1-5/14636565)

## Wire labels — borrow_first

Colored heat-shrink plus fine permanent marker. Installed: None pack; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Use the selected colored heat-shrink and a fine permanent marker. No oversized blank label book is selected. Confirm a readable, durable marker is available; marker ownership is not assumed.

## LiPo charging bag — review_hold

OutOfDarts LiPo Charging Bag / Misprinted Logo variant44666207371306. Installed: None each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

The $4.99 Misprinted Logo variant is available. Not an onboard part. Published dimensions were absent; verify battery fit. The bag does not authorize unattended charging. Sourcing note recorded with the decision: Deferred onboard-power candidate. Not needed for initial Mac/OpenRB and single-unloaded-servo bench work. Reassess from measured current, endpoint voltage, transient behavior and required onboard fit; the 5.2A scenario is not a measured minimum. See ../power/bench-power-plan.md.

[Selected or reference supplier](https://outofdarts.com/products/lipo-charging-bag-fireproof-battery-safety-storage?variant=44666207371306)

## Computer — borrow_first

User computer with Wi-Fi,USB-C and SD reader path. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## 2.4GHz Wi-Fi network — borrow_first

2.4GHz Wi-Fi router/AP or compatible computer hotspot. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Borrowed 3D printer — borrow_first

RoboClub Bambu Lab X1 Carbon,0.4mm nozzle. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Digital caliper — borrow_first

0.1mm or better resolution. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Digital scale — borrow_first

0.1g resolution. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Small screwdrivers — borrow_first

Phillips #0/#1;2mm hex key;4mm M2 nut driver;5.5mm M3 nut driver. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Temperature-controlled soldering station — borrow_first

temperature-controlled iron+stand;fine/chisel tips. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Wire strippers and cutters — borrow_first

16–28AWG wire stripper,flush cutter,tweezers. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Heat tool — borrow_first

heat gun with temperature control. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Multimeter — borrow_first

continuity/DC volts,resistance. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Solder fume extraction — borrow_first

local solder fume extraction. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Current-limited bench supply — borrow_first

adjustable0–12V DC,≥10A,variable current limit. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Print finishing tools — borrow_first

deburring tool,small file,pliers;eye protection. Installed: 0 set; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Reuse or borrowing is an option, not verified user/RoboClub ownership or a reservation.

## Printing filament — club_supply

Bambu PLA Basic Jade White 10100, 1.75mm, 1kg WITH SPOOL. Installed: None g; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Actual Bambu cart verifies one 1kg spool at $22.99, not a refill or bulk price. Current print revision is 64 retained source instances + 11 current parts + 14 extra idler/cap stocking instances = 89; follow the latest assembly print queue and its actual slicer readback. Extra idler/cap stock is not a claim of installed count. No physical printing is claimed. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://us.store.bambulab.com/products/pla-basic-filament)

## M2.6x6 rear-center tapping screws — club_supply

M2.6x6 TAP; manufacturer-matched rear-center screw; ROBOTIS BHS rounded head profile, diameter5.5mm height1.565mm. Installed: 8 screw; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Exactly eight M2.6x6 TAP installed. Only two separately printed idler/cap pairs install at IDs11/12; twelve printed pairs remain spares. IDs1/6 instead use separate M2.6x8 entries. Historical FPX330-H101 pack is a source reference, not stock or a purchase requirement. Native head-profile check requires matching rounded BHS geometry; arbitrary same-diameter pan heads are not interchangeable in thigh recesses. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.robotis.us/fpx330-h101-4pcs-set/)

## Fuse-carrier ties — club_supply

Panduit PLT2M-C / 298-1028-ND, nominal 203×2.5×1.1mm. Installed: 4 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Current reference-only geometry check uses 2.5x1.1mm ties. Do not apply this wider/thicker size to the alarm/audio/EN routes. Actual lock position and printed-slot fit need first fit. Sourcing note recorded with the decision: Source from RoboClub; match the listed dimensions/rating before installation. Exact bin stock is not asserted.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/panduit-corp/PLT2M-C/280041)

## External motor power supply — review_hold

Mean Well GST60A05-P1J / DigiKey1866-2146-ND. Installed: 0 each; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

Enclosed5V6AACadapter, center-positive5.5x2.1mmDCplug. Borrow groundedIEC-C13mainscord; not included. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/mean-well-usa-inc/GST60A05-P1J/7703709)

## Prewired DC power socket — review_hold

Tensility10-06257 / DigiKey839-10-06257-ND. Installed: 0 each; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

5.5x2.1mmsocket,305mm18AWGred/blackleads. Verifycenter-positivecontinuity and polarity before motor connection. Sourcing note recorded with the decision: Historical architecture candidate, excluded from the active MDY-14-ED single-source route. A future single onboard power bank needs its own output, dimensions and mass acceptance; these legacy parts are not automatically released.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/tensility-international-corp/10-06257/27685456)

## Grounded adapter wall cord — optional

Intact US NEMA 5-15P to IEC C13 grounded AC cord. Installed: 0 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

No new mains adapter or AC cord is used in the active route. Sourcing note recorded with the decision: Legacy adapter cord is not required by the current route.

## Logic power donor cable — optional

USB-C to Micro-B cable with 20AWG power pair; prepared length at most 500mm. Installed: 0 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Historical reference or optional alternate, not required by the current MDY-14-ED route; retained sourcing holds still apply.

The current logic tether uses club 20AWG wire and the purchased compact Micro-B plug. Sourcing note recorded with the decision: No separate USB-C logic cable is required by the common 5V source.

## USB-C power receiver (bench only) — buy

Adafruit 5991 HUSB238 switchable USB PD receiver. Installed: 0 each; external/bench: 1; remaining purchase packages: 1; merchandise: $9.95.

Owned spare, received; retired from the robot 2026-10-13; day-1 5 V bench only.

Received in DigiKey order 101587695 (user-confirmed 2026-09-29). Retired from the robot power chain on 2026-10-13, when the ROBOTIS SMPS 12V 5A + SMPS2DXL wall end replaced the 20 V USB-PD chain; kept as an owned spare. Bench use: exactly the 5V DIP switch ON (all switches OFF requests up to 20 V); read 5 V at the terminals before connecting a load. The purchase row is the received r3 order line; no new purchase.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/adafruit-industries-llc/5991/24892287)

## Common 5V regulator — buy

DFRobot DFR1202, 6-24V input, 5V output. Installed: 1 each; external/bench: 0; remaining purchase packages: 1; merchandise: $12.90.

Required in current design.

Received in DigiKey order 101587695. 30x26x8mm board in the rear pack, input 6-24V (12 V since 2026-10-13), output 5V +/-1%, efficiency over 90% at 12 V in. Design budget 5A continuous / 7.4A short peak at 5V (3A sustained servo acceptance limit or 5.4A simulated 20 ms servo peaks, plus a 2A non-motor reserve); these are calculation allocations, not measured loads or a physical current limiter. Four power pads require soldering; leave heat-pad cooling space. Budget check: ../redesign-20260913/design-contract.json and verify_design.py.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/dfrobot/DFR1202/27526972)

## Input fuse (not used) — buy

Littelfuse 0251005.MXL 5A axial / DigiKey F2317-ND. Installed: 0 each; external/bench: 1; remaining purchase packages: 1; merchandise: $1.24.

Not used: fuses were dropped from the whole robot and the tether (owner decision 2026-10-11/12; the live guide marks them not used). Received in DigiKey order 101587695 and kept as owned stock.

Received in DigiKey order 101587695 and kept as owned stock. No fuse is fitted anywhere in the robot or the tether.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/littelfuse-inc/0251005-MXL/700749)

## 12 V power quick-disconnect — buy

DFRobot FIT0586 XT30 male+female pair / DigiKey 1738-1436-ND. Installed: 1 pair; external/bench: 0; remaining purchase packages: 1; merchandise: $1.90.

Required in current design.

Received in DigiKey order 101587695. One package contains one mating pair. The tether side uses the recessed female contacts; the robot side uses the male contacts. Four solder cups need 18 AWG wires and heat shrink. Mark 12V INPUT; never mate to a 5 V load. Read 11.5-12.5 V at the female before it meets the robot.

[Selected or reference supplier](https://www.digikey.com/en/products/detail/dfrobot/FIT0586/9559255)

## 12 V power tether — club_supply

18AWG flexible stranded copper, red+black, 2m operating run. Installed: 2 m per color; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Obtain 2.2 m each of red and black 18 AWG copper including termination allowance; use a 2 m operating tether. Splice the ROBOTIS cable's middle wire (+12 V) to red and its outer GND wire to black, cover both splices with heat shrink and tie the cable to the tether before and after them. Expected drop about 0.2 V at 2.7 A. Exact club stock remains unverified. Sourcing note recorded with the decision: Obtain 2.2m each red and black 18AWG copper including termination allowance; use a 2m operating tether. Keep mechanical strain away from the PD board and robot solder pads. Exact club stock remains unverified.

## Pi GPIO power harness — club_supply

Four precrimped female 2.54mm leads, 22AWG, 250mm, fixed insulated housing. Installed: 4 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Two red and two black 250mm 22AWG leads; terminals must explicitly accept 22AWG. each contact rating >=1.5A. Pi needs a pre-soldered male 40-pin header. Pin 9 remains IMU ground, pin 20 audio signal ground. Keep PWR IN empty and covered; strain-relieve the fixed housing. Do not substitute unrated loose jumpers. Populate the dedicated unified 2x20 housing item; do not stack four individual socket housings under a second full-width housing. Sourcing note recorded with the decision: Two red and two black 250mm 22AWG leads; terminals must explicitly accept 22AWG. each contact rating >=1.5A. Pi needs a pre-soldered male 40-pin header. Pin 9 remains IMU ground, pin 20 audio signal ground. Keep PWR IN empty and covered; strain-relieve the fixed housing. Do not substitute unrated loose jumpers.

## Existing 120W charger (no robot role) — owned

Xiaomi MDY-14-ED. Installed: 0 each; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

No robot role since 2026-10-13: the ROBOTIS SMPS 12V 5A + SMPS2DXL wall end replaced the MDY-14-ED 20 V PD chain. Owned; it may feed the Adafruit 5991 in the optional day-1 5 V bench step.

User supplied the exact charger label. No charger purchase. Its fixed 20V/3.25A PD mode was the r3 robot source until 2026-10-13. Sourcing note recorded with the decision: User supplied the exact charger label. Reuse it; no charger purchase. The design uses its standard fixed 20V/3.25A PD mode through the original cable, not a generic 120W assumption.

## Original Xiaomi charger cable — borrow_first

Xiaomi original modified USB-A male to USB-C male charger cable. Installed: 0 lead; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

No robot role since 2026-10-13 (12 V ROBOTIS wall end). Owned; not needed for the robot.

No purchase released. The 12 V wall end does not use it; the robot needs no availability check for it. Sourcing note recorded with the decision: Locate and verify the exact original Xiaomi cable supplied with the charger. Ordinary USB-A-to-C extensions are not a substitute. No purchase is released; actual availability and 20V negotiation remain commissioning checks.

## Tether splice insulation and strain relief — club_supply

Heat shrink for the two splices and the DATA wire end, three small cable ties, 12V polarity label. Installed: 0 set; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Splice insulation and tie strain relief for the 12 V wall end (2026-10-13); no receiver or fuse enclosure.

Club material. No enclosure: the SMPS2DXL board and the supply stay outside the robot, and nothing is soldered onto the board. Ties go before and after the splices and next to the SMPS2DXL plug (guide step pd-tether). Sourcing note recorded with the decision: Fabricate from club material. Accommodate 29.1x20.3x10.1mm receiver plus fuse insulation and wire bends; provide strain relief at both cable exits. Do not claim an old print is this enclosure.

## Power commissioning instruments — borrow_first

Multimeter, electronic load >=60W, oscilloscope and temperature probe. Installed: 0 set; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Borrow first; the 12 V wall end needs no USB PD readout.

Borrow instruments before powered assembly acceptance; current-limited bench supply and a multimeter alone do not measure the required transient waveform. No tool purchase is released. Sourcing note recorded with the decision: Borrow instruments before powered assembly acceptance; current-limited bench supply and a multimeter alone do not measure the required transient waveform. No tool purchase is released.

## ROBOTIS 12 V wall supply — owned

ROBOTIS SMPS 12V 5A (PS-10) with AC cord, OMX-AI kit accessory. Installed: 0 each; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Owned kit accessory; robot wall supply since 2026-10-13.

One set from an OMX-AI kit allocated to the duck (order 2034348); not the arm's set and not the reserved third kit. Stays outside the robot. No purchase. Its 5 A covers the walking peaks of about 2.7 A at 12 V. Sourcing note recorded with the decision: Owned OMX-AI kit accessory from a duck-allocated kit (order 2034348); no purchase.

## ROBOTIS SMPS2DXL adapter board — owned

ROBOTIS SMPS2Dynamixel (SMPS2DXL), SKU 902-0034-000, OMX-AI kit accessory. Installed: 0 each; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Owned kit accessory; 12 V wall end since 2026-10-13.

One set from an OMX-AI kit allocated to the duck (order 2034348); not the arm's set and not the reserved third kit. Stays outside the robot. No purchase. Every socket is live at 12 V when the supply is plugged in. Nothing is soldered onto the board; the cable stays plugged in and is tied to the board next to its plug. Reference: robotis.us/smps2dynamixel, cited in guide/content/wiring/smps2dxl.py. Sourcing note recorded with the decision: Owned OMX-AI kit accessory from a duck-allocated kit (order 2034348); no purchase.

## SMPS2DXL 3-wire cable, far plug cut off — owned

ROBOTIS 3-wire cable plugged into the SMPS2DXL, OMX-AI kit accessory. Installed: 0 lead; external/bench: 1; remaining purchase packages: 0; merchandise: $0.00.

Owned kit accessory, cut and spliced to the tether (guide step pd-tether).

One set from an OMX-AI kit allocated to the duck (order 2034348); not the arm's set and not the reserved third kit. Stays outside the robot. No purchase. Find GND with a meter: red probe on the middle wire; the outer wire that reads 11.5-12.5 V is GND. Wire-to-wire solder splices only; the cable keeps its full length and only the far plug is cut. Sourcing note recorded with the decision: Owned OMX-AI kit accessory from a duck-allocated kit (order 2034348); no purchase.

## Unified Pi header housing — club_supply

One non-stacking insulated 2x20 female housing for 2.54mm pitch and 12 matched contacts. Installed: 1 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Full housing plus twelve populated wire exits must fit7x52x15mm, centered on original Pi header. 52mm maximum length preserves1mm nominal Pi screw-head clearance; 54mm old envelope had zero clearance. Contact current ratings unchanged. Sourcing note recorded with the decision: Source one low-profile 2x20 female housing and its compatible terminals from RoboClub. Four power contacts must explicitly accept22AWG and each rate>=1.5A; four IMU and four audio contacts must fit the same housing. Preserve correct physical pin locations and check final connector height against gpio-housing-review.json. No kit or stock is assumed.

## M2x6 machine screws — club_supply

M2-0.4x6mm pan-head screw; head <=4mm diameter x1.72mm height. Installed: 4 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Obtain matching club stock; no purchase selected. See current electronics-fasteners.json. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## M2x10 machine screws — club_supply

M2-0.4x10mm pan-head screw; head <=4mm diameter x1.72mm height. Installed: 4 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Obtain matching club stock; no purchase selected. See current electronics-fasteners.json. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## M2x4 tapping screws — club_supply

M2x4 TAP; head <=4mm diameter x1.72mm height. Installed: 8 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Installed quantity from joint-fasteners.json. Tapping thread, not M2-0.4 machine screw. Club stock and receipt unverified; no purchase selected. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## M2x5 tapping screws — club_supply

M2x5 TAP; head <=4mm diameter x1.72mm height. Installed: 12 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Installed quantity from joint-fasteners.json. Tapping thread, not M2-0.4 machine screw. Club stock and receipt unverified; no purchase selected. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## M2x6 tapping screws — club_supply

M2x6 TAP; head <=4mm diameter x1.72mm height. Installed: 46 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Installed quantity from joint-fasteners.json. Tapping thread, not M2-0.4 machine screw. Club stock and receipt unverified; no purchase selected. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## M2x7 tapping screws — club_supply

M2x7 TAP; head <=4mm diameter x1.72mm height. Installed: 2 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Installed quantity from joint-fasteners.json. Tapping thread, not M2-0.4 machine screw. Club stock and receipt unverified; no purchase selected. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## M2x8 tapping screws — club_supply

M2x8 TAP; head <=4mm diameter x1.72mm height. Installed: 22 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Installed quantity from joint-fasteners.json. Tapping thread, not M2-0.4 machine screw. Club stock and receipt unverified; no purchase selected. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## M2x10 tapping screws — club_supply

M2x10 TAP; head <=4mm diameter x1.72mm height. Installed: 18 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Installed quantity from joint-fasteners.json. Tapping thread, not M2-0.4 machine screw. Club stock and receipt unverified; no purchase selected. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## M2.6x8 rear-center tapping screws — club_supply

M2.6x8 TAP; manufacturer-matched rear-center thread; ROBOTIS BHS rounded head profile, diameter5.5mm height1.565mm. Installed: 2 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Exact dimensions required by joint-fasteners.json and native clearance check. Club stock unverified; no purchase selected. Native head-profile check requires matching rounded BHS geometry; arbitrary same-diameter pan heads are not interchangeable in thigh recesses. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## Small M2.5 metal washers — club_supply

DIN433 / ISO7092 M2.5 metal washer: ID2.7mm OD5.0mm thickness0.5mm. Installed: 4 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Exact dimensions required by joint-fasteners.json and native clearance check. Club stock unverified; no purchase selected. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## M2.5x8 head-cap tapping screws — club_supply

M2.5x8 TAP; head <=4mm diameter x1.5mm height. Installed: 3 each; external/bench: 0; remaining purchase packages: 0; merchandise: $0.00.

Required in current design.

Current head-cap third boss restored; exact three installed screws from electronics-fasteners.json. Club stock and receipt unverified; no purchase selected. Sourcing note recorded with the decision: Engineering screw-length correction only; no purchase authorization or claim of club stock.

## Separate fastener cart authorization

The September 29 user request authorizes researching inexpensive compatible fasteners on Amazon and adding verified offers to cart. Checkout is not authorized. Other sourcing holds remain unchanged.

Status: partial_cart_verified. Selected packages: 2 offers, $20.58 merchandise. The $30 working ceiling is an agent assumption, not a user-selected budget.

[Exact authorization and evidence requirements](fasteners-amazon-20260929/README.md). Catalog fallback offers remain held; only the separate exact offer manifest can authorize fastener cart lines.

- 1 package(s) of [uxcell M2.5x6mm stainless Phillips pan head self-tapping screws, 100 pcs (+/-2%)](https://www.amazon.com/dp/B01L7PDGXO): $12.09; 8 working units for pi_mount_screws.
- 1 package(s) of [uxcell M2.5x8mm stainless Phillips pan head self-tapping screws, 50 pcs (+/-2%)](https://www.amazon.com/dp/B01KXTTSCI): $8.49; 3 working units for tap_m25_8.

Uncovered fastener requirements: 20 specifications. Native cart verified: True. No checkout or physical stock is implied.
