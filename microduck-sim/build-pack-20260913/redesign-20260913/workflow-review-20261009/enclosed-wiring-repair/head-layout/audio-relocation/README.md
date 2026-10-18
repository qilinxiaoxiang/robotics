# Current local amplifier repair — +Y13

The current native amplifier and its two support/pilot interfaces passed 178 affected-pair checks, including the MicroB receiving model that was previously omitted. Fusion captured the reference transform; all 7,507 actual mesh nodes reproduce the checked position within 2.18e−6 mm. `positive-y13-native/local-acceptance.json` is the current local receipt. `reference-capture-lineage.json` proves that capturing the reference changed only the F3D archive/readback metadata: the checked STEP and STL bytes are unchanged, and no geometry check was rerun.

This accepts only the named local interface. OpenRB remains a head requirement; its placement, complete camera ribbon, other wiring, final populated closure and physical fit remain pending. The withdrawn earlier subset and its MicroB collision remain below as history.

## Prior one-position check — superseded

The specified translation (−29, +17.2, 0) mm from the previous amp16z2 pose is clear against 88 independently checked rigid neighbors, including the current native closed cap and four Pi posts, the individual populated Pi parts, camera, jaw and unchanged speaker/cradle/keeper. Both 8 mm terminal lead receiving segments are clear. The native cap is used as a whole; no obsolete feature was silently omitted.

The two mounting holes are source Eagle plated Ø2.5 mm holes, 12.7 mm apart. `mount-and-sequence.json` records source coordinates, their world lower/upper PCB faces, the native Eagle-to-world transformation and connector directions. `amplifier-front-free-bay-world.stl` is the translated existing amplifier plus terminal receiving model, not a new printed part.

Both terminal driver shafts intersect the fitted roof (14.64 and 15.00 mm³), regardless of whether Pi is fitted. Prewire the loose amplifier on the bench. Its two PCB mounting drivers are clear of Pi, camera and speaker but encounter the head yaw-link in the assembled robot: install and fasten the amplifier on the detached roof. The four new Pi screw/nut positions are separated from the amplifier in X by at least 15.39 mm.

The check completed in 3.74 s with 217 MiB peak sampled memory. New supporting posts and complete flexible wiring/closure remain separate work. This result does not change a print release or establish physical fit.

## Native closed-roof integration completed

`native/MicroDuck-closed-head-Pi-audio-mounts.f3d` contains the original closed roof, four Pi mounts, four native audio support/pilot pairs, the original-position speaker and its retained keeper, a native cradle with one 0.95 mm lower screw-bearing pad, and 88 current hardware/reference meshes. Both revised printed parts have separate STEP/STL outputs.

The formerly proposed 3.3 mm blind hole at speaker Y17 would leave only 0.437 mm minimum sampled exterior distance. The single pad increases its screw stack to 5.96 mm: the retained M2.5×8 has 2.04 mm nominal entry and a 2.35 mm pilot leaves 0.31 mm tip clearance. The outer-roof distance is now 1.040 mm sampled, with a 1.022 mm continuous disk coverage bound. The other speaker hole retains its original stack and 3.3 mm pilot. These are tapping-interface engineering dimensions, not certified plastic pullout strength.

`native/audio-local-assembly-check.json` passed 8,722 independent and sampled checks: added supports versus current populated Pi/fixed head, the prewired audio parts entering a detached cap from below, Pi joining afterward, and four mounting driver corridors. Sampling is 0.25 mm over 15 mm translation. The run took 4.55 s and 231 MiB. `native/local-acceptance.json` binds the exact native and check outputs. This is local digital mounting acceptance; complete flexible routing, final populated head closure and physical commissioning remain open.

## Original exterior versus internal material removal

The native original-minus-current test retains its original `passed:false`: 0.5765735 mm³ of original material is removed at the single speaker Y17 blind pilot. This is the intended internal bore, not a crown/rear opening. Its eight-face bounds end at Z135.8 and match the planned Ø2.1 mm bore; the original exterior remains at least 1.02242 mm away. `native/closed-exterior-explanation.json` binds the unchanged subtraction report and states `CLOSED_ORIGINAL_EXTERIOR_RETAINED_WITH_INTERNAL_BLIND_BORE`. It does not accept populated head closure or physical fit.

## Current-layout acceptance withdrawn: omitted MicroB pair

The previous 8,722-check result remains valid only for its recorded subset. The separately generated current MicroB plug receiving model was imported into Fusion but omitted from that numerical inventory. Its intersection with the relocated amplifier is 196.0544 mm³. `native/local-acceptance.json` therefore withdraws current-layout acceptance while preserving the original receipt separately. The closed exterior and speaker endwall calculation are unaffected. A single unified rigid inventory now includes that connector before evaluating the next positive-Y amplifier pose.
