# MicroDuck power system V2 (proposal, 2026-11-19)

Status: proposal for Shawn's approval. Nothing bought, no CAD. Supersedes the swappable 650 mAh LiPo backpack
(`../battery-backpack-20261015/`); the switch and cutoff details are in `../power-switch-20261119/README.md`.

## Problems (Shawn, 2026-11-19)

1. The hard switch gets left on and the pack drains to damage (dead Tattu cell; servos at factory settings).
2. Press once for on with a light, and the light goes out by itself after shutdown; software shutdown cuts power.
3. Runtime is 20-30 min walking and at most 40 min mostly idle; target about 2 h.
4. Charge while running, and later charge by backing onto a dock.

## Picture

```
dock:  USB-C PD charger -> Adafruit 5991 (20 V) -> XL4015 CC/CV (8.6 V, 2 A) -> two spring plates in a V funnel
robot: two contacts under the tail -> Schottky diode -> pack node
       STRIX 2S 3200 mAh pack (fixed) -> pack node -> Pololu #2813 -> OpenRB J4 (servos) + DFR1202 (A7Z 5 V)
       XIAO (5 V from the DFR1202 lead) reads pack voltage, middle cell (XH lead) and the contact voltage;
       XIAO or A7Z GPIO -> Pololu OFF through one diode each
```

## Parts and reasons

- **PV-1 Battery (chosen 2026-11-19, Amazon): Crazepony/ALIENMODEL 2S 3000 mAh LiPo, B08LZ8L4YD**, $22.99, In
  Stock with two-day delivery, 110 g, 72 x 34 x 20 mm, 5C continuous (15 A) / 10C burst (30 A), XT30 and DC5.5
  leads plus JST-XH balance (listing photo shows XT30). Higher current rating than the STRIX below and on Amazon.
  Alternative: **STRIX Power Stix 2S1P 18650 Li-ion 3200 mAh, XT30, model STX-170042.** Problem 3. ReadyMadeRC
  (Ohio) $21.99, In Stock, page read 2026-11-19: 101 g, 69 x 37 x 19.2 mm, 10 A continuous, XT30 16 AWG, XH balance
  lead, 4.2 V per cell, charge up to 3.2 A, 23.68 Wh. Runtime scaled from the Tattu 650 (43 g) as measured by
  Shawn: 3200 / 650 = 4.9 times, so about 1.5-2 h walking and about 3 h mostly idle, less some for Li-ion sag under
  load. Mass +58 g on a 960 g robot (6 %); the flight study (`extensions/flight-20261110/leg_load.json`) puts static
  hip roll at 20 % of the 0.96 N m limit with no pack and 34 % with a 725 g pack, so 58 g is far inside the joints.
  The sim mass manifest, `current.json` and the walking check still follow the AGENTS.md model rule before walking.
  The pack is fixed in the backpack (charged on the robot), so the swap plugs go away. Simpler option rejected: a
  2S LiPo of the same capacity is about 170 g.
- **PV-2 Switch, cutoff, LED button, A7Z power-off, idle timeout:** PS-1 to PS-5 of `../power-switch-20261119/`.
  Added here: the XIAO also reads the middle cell through the XH lead (100 k / 100 k), so it cuts at pack 6.3 V or
  either cell 3.1 V, held 3 s. Per-cell protection without a BMS, whose 10-20 A over-current trip would drop the
  robot in a fall (all servos stalled 25-29 A).
- **PV-3 Charge input: two spring contacts under the tail, a 5 A Schottky diode (SB560 class), into the pack node
  ahead of the switch.** Problem 4. Ahead of the switch so the pack charges with the robot off; with the robot on,
  the dock feeds the load and the pack together, which is charging while running. The diode blocks the pack from
  back-feeding the contacts and the dock, and protects against reversed polarity. Its 0.3-0.5 V drop puts an 8.6 V
  dock at about 8.2 V on the pack (4.1 V per cell): slightly short of full, kinder to the cells. Balance: the XH
  lead stays reachable; the B3 balances the pack about monthly, and the XIAO reports cell difference.
- **PV-4 Dock: USB-C PD charger, Adafruit 5991 and an XL4015 CC/CV board (both already owned from the charger
  backpack), set 8.6 V and 2 A, wired to two plates in a V funnel.** Problem 4. The current limit makes a shorted
  plate harmless (2 A), so v1 needs no robot detection. Charge time with the robot sitting torque-off about 2 h.
  Contacts on contacts, not wireless: Qi needs a few mm of alignment and wastes 30-40 %; a funnel takes 1-2 cm.
  Docking behaviour (see a marker, turn, back in, sit) is software after the hardware works.

## Buy

- STRIX 2S 3200 XT30 x1, $21.99 (ReadyMadeRC, ground shipping from Ohio).
- Pololu #2813, $8.95.
- 16 mm momentary pushbutton with LED ring, 12 V LED version.
- SB560-class Schottky diode, 1N4148 x2, resistors 100 k / 33 k (RoboClub drawers likely).
- Spring contacts rated 2 A or more (RoboClub has a pogo pin drawer; check the rating).
- Not needed any more: the second B3 charger and the extra Tattu 650 in the Amazon cart (2026-11-01).
