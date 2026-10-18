# Leg cabling before mechanical closure

Review: 2026-10-09. Problems P5/P6. **Process proposal; not a physical insertion or removal certificate.** The electrical architecture is being reviewed. These mechanical dependencies do not authorise adopting the previous fused-power topology, cutting cables or changing printed parts.

## Confirmed defect

Both current leg modules contain 20 mechanical operations and zero `wiringStage` or `beforeClose` annotations. Cabling is reached after those operations through a separate tab. A motor can therefore be surrounded and retained before the tutorial has asked the builder to identify either socket, thread a free plug, or preserve access. The omission is confirmed in the current generator and generated data; a particular socket being completely inaccessible is a separate claim.

The viewer also used one global wiring index, unrelated to the selected leg. A previously selected Pi-power stage could reappear in a leg module, and Next crossed into other subsystems. The saved source repair selects a specific cable within the selected module and limits navigation to that group. Eight regression checks against the actual enhanced data pass. Deployment is paused while the power architecture is reviewed; endpoint animation and browser acceptance are separate.

## Evidence limits that change the decision

The [ROBOTIS XL330 manual](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/) specifies JST EHR-03 housing, B3B-EH-A header and pins GND/VDD/DATA. The locally saved manufacturer drawing shows two side ports. The drawing does not provide a registered installed port-centre transform for this robot. Existing `wiring-spatial-data.json` motor anchors explicitly describe bounding-box centres and mark connector orientation unverified.

Consequently, neither a line ending inside a motor box nor a nearby printed part proves a blocked insertion. This review does **not** assert that the thigh plate, hip support or ankle fork necessarily prevents later insertion. It identifies the exact stations where that possibility must be checked before access is surrendered. It also does not turn the current DATA-only split harness into a standard three-wire bus: pin use remains an electrical decision.

## Proposed sequence for a new leg

The same source step numbers apply independently to left and right legs. Left motor roles are ankle 6, knee 7, hip pitch 8, roll 9, yaw 10. Right roles are ankle 1, knee 2, hip pitch 3, roll 4, yaw 5. No mirror clearance is inferred.

- **Before step 01 — thigh motors and reinforcing plate.** Identify and label the required motor ends on the loose knee and hip-pitch motors. Pre-seat them while both sockets can be inspected. Keep neighbouring motor ends free. Bring those free ends out through the still-open thigh station before its plate is fitted. Check the actual wired motor/plate approach; the previous bare-motor path does not cover added plugs.
- **Before step 05 — ankle motor into the fork.** Prepare the ankle leads on the loose motor, keeping the knee-side destination free. Use the open fork for initial cable passage. Check that the complete plugged motor can enter; do not substitute the bare-motor result.
- **Before step 07 — lower-link sleeve/boss closure.** Inspect seated housings and route departure outside the sleeve, locating pegs and mating seam. Keep the knee end free during the later rigid lower/ankle movement. Never pull a plug or cable through the interference-fit sleeve.
- **Before step 11 — foot seating.** Confirm that the outgoing ankle lead is visible and clear of the retaining boss. This is a pinch/access checkpoint, not evidence that the foot blocks a port.
- **Before step 13 — yaw link on the bench.** Prepare the loose yaw motor's assigned ends. Leave the roll/torso destinations free. Keep all leads clear of the four internal yaw screw tool corridors. Step 14 must still finish those screws before the roll motor is added.
- **Before step 15 — roll motor and passive support.** Prepare the roll motor's ends and recheck yaw plugs while this station is open. Lead the free destinations outside the open station before adding its retaining parts. Keep case screws and rear retainer clear.
- **Before step 17 — hip bridge on the thigh.** Inspect the hip-pitch plug and outgoing lead while the yaw/roll group is separate. Keep the roll-group end free; no housing may be threaded through a seated support ring.
- **Before step 19 — join the complete yaw/roll group.** Move the already attached leads with that group, without tensioning a prematurely closed cable loop. Connect remaining local destinations only after their housing passages are complete and the group is seated. Leave the torso interface accessible. Establish joint slack and observable plug seating before the final roll fastening.

These gates use the OMX prepare/assemble/check method: prepare and orient one actual plug, insert through a confirmed open approach, then inspect seating and strain relief. They are not eight extra cables. Cable quantity, final pin assignment, length and route coordinates remain tied to the selected electrical architecture and registered ports.

## Already assembled legs: preserve completed work

Start with a disconnected, supported leg. Inspect both real side sockets. If the intended keyed housing can seat directly with accessible grip space, **remove no part**. The tutorial must not assume a cover needs removal merely because it lies near the motor.

If a real plug is obstructed, identify the obstructing printed face at that socket before choosing a removal sequence. The current source gives these local retention stations, not an accepted disassembly instruction:

- The thigh plate is installed at step 01 and retained through case/rear operations 02/04. It is a structural station, not a proven cosmetic cover.
- The hip passive support and bridge are retained through 15/16 and 19/20. Removing them can release a shaft or case. The complete supported group, exact screws and removal path must be established first.
- The lower link, ankle sleeve and foot are already subject to explicit source-fit limitations at 07/11. Do not reverse these fitted joints merely to reach a cable. Preserve the user's assembled ankle/foot unless a targeted, supported recovery requires otherwise.

No whole-leg teardown, particular screw-removal count or replacement print is justified by the available connector evidence. The smallest remaining engineering check is actual socket-to-CAD registration and a local housing/grip approach against the named surrounding parts; only a demonstrated failure selects a specific local opening. This is a stage-B task, not a request to dismantle hardware now.

## Machine-checkable result

`operation-dependencies.json` binds the exact source files, 16 proposed gates, all ten motors' first enclosure operations, and the unresolved physical access boundary. `verify_operation_dependencies.py` confirms both proposed orders and rejects all 16 single-gate premature-closure mutations. It also rejects the current unaugmented guide for eight missing gates per side.

A passing process test cannot set `physicalInsertionVerified` or `integrationReady`: both remain false. Authoring the proposed gate list is complete; socket registration, plugged-subassembly approach, joint slack and exact already-built recovery are not.

AI assistance was used to draft.
