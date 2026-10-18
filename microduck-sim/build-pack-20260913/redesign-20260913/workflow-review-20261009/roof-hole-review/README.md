# Why the head crown has a rectangular opening

Verified 9 October 2026; P5/P6. **The front crown opening was added by the assistant for the Pi's Micro-USB OTG connector route. It is not an original community feature, a screw-access hole, a cooling requirement, or a missing display triangle.** The current Fusion cap and final head viewer inherit it. No released geometry was changed in this review.

![Original and current cap, top projection](roof-top-comparison.png)

The graphic compares actual mesh faces, not a concept box. The left is `curved-head/community-curved-head-world.stl`; the right is `gpio-audio-repair/speaker-final-export/speaker-pilot-fix/cap-speaker-pilot-fixed-world.stl`. The front is toward positive world X. The red outline is the later 9×19 mm USB cutter cross section near Z=155 mm. Orange interior surfaces can project into openings; this is a top projection, not a photograph or thickness map.

## Trace to the current file

The original curved source is recovered from upstream `top_head_shell` by `curved-head/build_curved_layout.py`. It has material across the highlighted region. `curved-head/build_mounts_and_paths.py` then subtracts the old Pi USB moulding receiving box plus 0.5 mm clearance per side. That receiving solid has world bounds approximately X60.2–68.2, Y−0.1–17.9, Z146.05–171.05 mm, yielding an axis-aligned 9×19 mm opening footprint. This is the first assistant cut.

The later `usb-access/usb-repair/apply_usb_service_opening.py` applies `positive-x225-service-opening-spec.json`: another **9×19 mm** rectangular cross section, along axis `[0.01154, −0.03412, 0.99935]`, with a 55.5 mm swept length that covers the plug and 30 mm approach. The updated opening record reports 204.381 mm³ removed from its input cap. Its source cap already descends from the earlier USB-cut cap; a portion of the earlier opening remains. Therefore the visible combined opening is not simply one accurately minimized 9×19 mm hole. The spec comment saying the previous Micro-USB hole was not inherited is inconsistent with that geometry lineage and must not be reused as proof.

The cut passes through the subsequent audio restraint and speaker-pilot fixes. The final cap SHA256 is `afe6a08b7fe3336b7533cc3d2916a4c387cbadc1d56d8c3d80c3aa6fb95d5d1a`. The Fusion import manifest identifies `head_cap` as “USB-service head cap,” with 26,084 triangles and no placement translation; its serialization has SHA `594924c6464306cc3d49d2b0bfe217957c4caa699511bc1ba1fa92efbeacdcbe`. The final viewer manifest binds the same final speaker-pilot-fixed source.

## Actual plug versus an assumed receiving solid

The **25×18×8 mm plug size is an assistant engineering receiving assumption**. It is hardcoded in `build_design.py`, alongside `usb_plug_vendor_dimensions_verified: false`, and repeated in the USB review. It is not measured from the owner's SC0727 and not an official moulding drawing. The [official Raspberry Pi product page](https://www.raspberrypi.com/products/micro-usb-male-to-usb-a-female-cable/) identifies a Micro-USB male to USB-A female cable and specifies 80 mm cable length; it does not supply those three moulding dimensions or define a verified 80 mm flexible-only span.

Consequently the finite calculation below diagnoses the **accepted envelope model and its stale placement**, not confirmed physical intrusion by the actual connector:

- With the earlier positive-X2.25 pose, the fully seated receiving solid overlaps the uncut original cap by **242.003 mm³**. The current cut cap has zero overlap with it.
- With the final three 2 mm Pi spacers, the plug should follow the PCB by approximately `[−1.9929, +0.1657, +0.0287]` mm. That seated receiving solid overlaps the original cap by **242.482 mm³** and the current cut cap by **9.22564 mm³**.
- The latter overlap lies at X62.906–64.733, Y−4.337–−0.600, Z153.767–155.647 mm. This reveals that the old plug-clearance receipt cannot be inherited after moving the Pi. It does not justify cutting another patch for an unverified solid.

Both loaded caps are watertight; the test uses two meshes and two seated solids, not a cached full robot. `roof-probe.json` binds inputs and numeric results. The guarded run completed in 3.4 seconds at approximately 200 MiB. The diagnostic front-roof removal ROI in that JSON includes other source differences and is not asserted to be the unique aperture volume or its dimensional tolerance.

## Practical decision

**“Plug it in first, then close the cap” does not solve the seated receiving-model overlap.** The issue in that model persists at the final seated pose, not just during insertion. But the available source does not establish that the physical connector requires this large hole. Do not describe it to the user as a demonstrated unavoidable feature.

First resolve whether phase-one operation still uses the Pi-to-OpenRB USB OTG link. The model currently embeds that earlier choice; central converter placement does not itself require any crown opening. If OpenRB is instead connected directly to the Mac and the Pi carries only sensor data, the reason for this Pi Micro-USB window may disappear, subject to the independently checked runtime and data/power architecture. This review does not silently change that ownership.

If the link remains, use a verified actual connector boundary and final PCB pose before changing the roof; neither arbitrary enlargement nor blind filling is justified. If the link is retired, restore only the original native curved material in the two historical Pi-opening regions while retaining the current internal mounts, speaker pilots, and separate rear OpenRB cable access. A global union with the original cap would risk filling unrelated intended openings and is not the proposed repair.

The exact source changes would be to retire the Pi `usbcut` in `curved-head/build_mounts_and_paths.py` and the later `positive-x225-service-opening-spec.json` operation, then replay the current mount/restraint/pilot changes from the uncut curved source, or prove a strictly localized native-surface restoration against those same features. Such a restored cap must be checked against the final connected hardware and its closure path before release. No fill mesh or new hole was generated now, because the user's question is provenance and necessity, and actual connector evidence remains distinct from the old assumption.
