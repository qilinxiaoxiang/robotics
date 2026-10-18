# PB1033MI port faces and B/C orientation

9 October 2026. Source review only; no new CAD, printing changes, power operation, or Fusion interaction.

**Recommendation: continue C with both narrow end faces open.** Its lower height remains useful, and its integrated USB-C lead can connect to the received 5991 receiver close to the outlet. B is electrically equivalent and can be equally simple to wire if its upper and lower end faces remain reachable. The choice does not require a rigid plug box, an extra long USB cable, or another battery measurement.

## What the evidence actually shows

The owner’s `IMG_6952.HEIC` is preserved. The adjacent JPEG is a display conversion. The photo shows PB1033MI identification, the broad labelled face, and the built-in cable leaving an upper narrow edge near a corner. It does **not** show the standalone USB-C and USB-A receptacles; their exact face must not be claimed from that photo alone.

`official-port-diagram.png` is a crop of the manufacturer manual, preserving its three views and labels. The broad view is approximately 125:153 in the crop, the thin side view approximately 50:154, and the two-receptacle end view approximately 125:50. Their aspect relationships match the specified **65.9×80.9**, **26×80.9**, and **65.9×26 mm** faces respectively. This supports assigning the adjacent independent USB-A/USB-C receptacles to a **65.9×26 narrow end face**, perpendicular to the 80.9 mm body axis. These are drawing-aspect observations, not measured port coordinates or connector tolerances.

The manual identifies USB-C **IN2/OUT2** beside USB-A **OUT3** on that end view. The integrated USB-C lead is **IN1/OUT1**. Its two adjacent appearances in the looped storage position are not two permanently attached cables. The separate side view shows the stowed plug, indicator lamps, and check button; the button is not the robot’s power disconnect.

The prior owner description supplied in this review was “integrated lead on top, standalone ports on bottom.” That supports opposite ends of the long body axis. The newer phrase “charging port on the long edge” does not independently assign a port to the 80.9 mm side wall: it may describe the long edge of the narrow rectangular end face. We therefore retain the supported end-face reading, explicitly avoid creating millimetric port poses, and keep the nearby side strip open as well. No conclusion assumes the photograph shows its hidden bottom.

Sources: [Xiaomi official specifications](https://www.mi.com/global/product/xiaomi-33w-power-bank-10000-integrated-cable/specs/), [Xiaomi official product presentation](https://www.mi.com/global/product/xiaomi-33w-power-bank-10000-integrated-cable/), [saved manufacturer manual](../sources/pb1033mi-manual.pdf). The crop is from its English Product Overview. The official web image host returned unsupported `application/octet-stream` in the web viewer; those unavailable images are not treated as visually inspected evidence.

## C: long axis front to back

With the existing concept dimensions **X=80.9, Y=26, Z=65.9 mm**, the supported port faces are front/rear. Use the integrated male USB-C lead as the single output into 5991; place the receiver nearby on the robot, with its USB-C socket facing the naturally relaxed cable approach. The receiver need not be centred on an invented 25 mm box or mounted rigidly on the battery. The converter and distribution can be reached by the receiver’s short DC pair, independently of the battery lead’s exact resting curve.

Prefer orienting the independent receptacle end toward whichever fore/aft face stays easiest to reach after the torso is installed. A fore/aft flip changes access, not the power architecture. The opposite integrated-lead end must also remain open for the strain relief, unplugging and battery withdrawal. This is a placement rule, not a checked cable path.

For charging, disconnect robot power and either use the independent USB-C input through the open end or remove the bank. Do not rely on running the robot during charging or on adding a second bank output: the existing power review found a shared multi-port 5 V/3 A rating and unverified transition behaviour. Removal should require unplugging the accessible 5991 connection and releasing the bank retainer, without dragging a retained connector through a close-fitting slot.

## B: long axis vertical

With **X=65.9, Y=26, Z=80.9 mm**, the same end faces point up/down. A lead-up orientation makes receiver placement nearby straightforward, but puts the independent receptacles below. Therefore B is not automatically worse for power wiring; it is less convenient for in-place charging if the lower end is blocked. An open bottom and removable bank can solve this without additional printed cable channels. Flipping the bank exchanges these access priorities.

C is 15 mm lower and 15 mm longer front-to-back than B, with the same 26 mm width and conceptual 22 mm total stance widening. Select B only if its shorter depth has a demonstrated mechanical benefit and both end-access operations remain practical. No current source proves that B needs a longer power cable or C needs a new lead.

## Required correction to the concept, not a new print

Retire the fixed **25 mm** service volumes as acceptance evidence: they are trial visual allowances, not Xiaomi connector, strain-relief or finger-space dimensions. Do not close either narrow end or wrap a rigid frame over the nearby side strip/plug-storage region. Use an open receiving channel plus a releasable retainer, with the small receiver fixed locally after the natural cable route is chosen. Avoid a dedicated moulded pocket that locks an uncertain connector pose.

The present STEP files are envelope concepts. Neither B nor C has accepted battery insertion, retainer strength, whole-robot motion clearance or cable handling. This review changes the interface reasoning; it does not label either concept printable. Exact socket offsets and natural cable shape are not prerequisites for choosing C or keeping these faces open.
