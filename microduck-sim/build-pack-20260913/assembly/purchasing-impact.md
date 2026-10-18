# Mechanical purchase and print impact

2026-09-13. **15 total actuators, including one jaw actuator**: fourteen standalone XL330 motors plus one in the starter kit.

## Fixed decisions

- **Use community printed sliding supports.** Retain the matched community ankle/foot pairs and large printed rings. Do not purchase an additional set of official metal bearings or fifteen HNX active-output horns.
- **Idler screw requirement:** one matching BHS M2.6 x 6 TAP screw per installed passive idler/cap. Source from RoboClub first; no screw-kit purchase is selected. Confirm thread, length and head geometry before installation. See [sourcing decisions](../procurement/sourcing-policy.json).
- **Keep the supplied M2 servo screws.** Fifteen boxes supply 90 M2 x 6 TAP and 150 M2 x 8 TAP. Inventory covers 60 output fasteners and a 120-case-fastener upper bound; installed counts and case-hole lengths remain separate. Use M2 x 6 through 3 mm output frames, following the [manufacturer's length warning](https://emanual.robotis.com/assets/images/dxl/x/x330/x330_horn_screw.png).
- **Do not purchase separate large-regulator spacers.** Four 2 mm spacers are printed into the support. Fixed added-electronics screw quantities are in the print list; Pi uses four M2.5 x 6 tapping screws with no nuts.

## Geometry repaired locally

**Jaw axis:** measured circular sections locate both jaw ends and the motor output at X3.0 / Z−18 mm; only the old bearing seat was at X3.2. `motor-support-coaxial-print.stl` replaces source h.obj / ID24 with an integral fixed sliding seat. It preserves the original motor mounting interfaces and provides a 10.4 mm bore about the correct axis. The separate mouth bearing is removed from the selected physical design; no new bearing purchase is needed.

The new material has no overlap against 41 checked head objects. With the relieved cap, 61 jaw poses from 0–30 degrees at 0.5-degree intervals have no checked mesh overlap. This closes the original static axis mismatch and constant bearing interference. It does not establish print friction, motor calibration, grip force or jaw software actuation.

**Fuse-tie compatibility repair:** the real 1.1 mm-thick PLT2M-C tie fits the slot but failed the former 1.0 mm gap between tiers. Lowering only the lower tier by 0.5 mm creates a 1.5 mm gap; mounting holes and fasteners are unchanged. This local STL was rechecked and re-sliced.

**Previously completed:** the 42.6 mm-wide two-tier fuse carrier clears sampled leg motion; eleven fuse spaces, four retaining ties, alarm bracket and ENA-switch saddle are present. Pi and head screw envelopes and bare MicroB connector allowances are checked.

## Exact print inventory and spare boundary

Print **64 retained source instances + 11 current parts + 14 extra idler/cap instances = 89 instances**. The replaced source IDs are 6 (cap), 12 (power support) and 24 (head motor support).

Source inventory has eight printed idlers and six caps. Add six idlers and eight caps, reaching fourteen of each. This is an explicit maximum-one-pair-per-non-jaw-motor stocking allowance, not fourteen confirmed installations. The source CAD identifies ten large support-ring stations coaxial with motor shafts plus a separate structural pivot, but merges the two motor-side flanges in one mesh. It cannot prove which passive stations use a separate idler/cap. The final installed/spare split must be recorded during first-article assembly. This allowance prevents an additional print run from being a procurement blocker without misreporting installed quantities.

## Narrow remaining mechanical checks

**Joint case holes:** the source provides no per-hole screws. Before repeating each distinct stack, measure its printed thickness and allowed case penetration, then select the supplied M2 x 6 or M2 x 8 TAP. This affects the assembly record; it currently does not justify another general screw assortment.

**Ankle and sliding-fit first article:** source-section measurements confirm mirrored ankle output patterns: four diameter2.2 mm holes on a 6 mm radius, with diameter4.4 mm head recesses. Each passive seat is diameter15 mm; the printed small ring has OD14.6 mm, giving nominal 0.2 mm radial seat clearance. The ring bore is approximately diameter9.64 mm and its actual mating shaft fit remains a first-article check. The combined feet each contain an approximately diameter1.6 mm pilot spanning at least 4.5 mm of sampled depth. These dimensions narrow the interface question; they do not establish full ankle/foot motion. Retain each community ankle with its corresponding combined foot. Their geometry differs from the official simulation, so the old official collision result cannot certify those interfaces or ground friction. Check one ankle of each side and one hip support before repeating assembly. The current plan buys no metal-bearing alternative. If fit fails, revise the specific printed bore or mating piece using measured dimensions.

**Received-component envelopes:** measure the alarm's undocumented header offset, trimmed ENA terminals, insulated fuse assemblies, both MicroB strain-relief envelopes, actual USB-C plug and tie locks. These can require a local window/retainer edit or harness adjustment; they do not require changing the chosen Pi, camera or battery on present evidence.

**Physical motion and mass:** verify the 10.4 mm jaw bore and shaft fit, calibrate all motor offsets and jaw limits, route flexible wires through complete motion, and weigh the finished robot. The source still lacks a fifteenth actuated XML joint; the walking policy alone cannot drive the jaw. Follow the electrical first-power procedure before walking or grasping.

## Servo regulator cost revision

The current selection is Pololu #5671 D42V110F5 at $59.95, replacing #2881 at $79.95. Same four M2 mounting centers; lower top profile; printed shelf and Bambu bundles retained. Use ENA-to-GND disable and leave ENB/PFM open. Check the tight 0.2 mm nominal underside/shelf clearance on the actual print. [Evidence and alternatives](../power/cost-review/README.md).
