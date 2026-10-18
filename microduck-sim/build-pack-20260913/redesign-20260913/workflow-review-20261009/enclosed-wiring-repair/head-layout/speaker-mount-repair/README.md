# Speaker cage: move the mounting ears inside the closed head

The actual speaker stays at the current transformed position. The old negative-Y mounting ears intersected the original curved cap by **27.081803 mm³** (cradle 15.921836, keeper 11.159967). The replacement retains the source perimeter seating geometry and moves the two screw ears to **[5, −21.5] and [45, −21.5] mm**. A 0.5 mm local clearance trim removes the keeper's remaining outer-edge contact. The obsolete lower pad belonging to the removed ear is removed too; it does not become a small unintended first-layer contact.

The cap exterior, speaker, amplifier, jaw, camera and board poses are unchanged. Two source-conformal internal roof posts support the new ears. They are an **addition to the final cap**, not a request to overwrite the independently updated controller/Pi mounts. The `cap-with-speaker-posts-candidate-world.stl` file is a local visual reference containing only the source shell and these two posts.

## Integration

Use `speaker-mount-fragment.json`. Its two replacement meshes are world-frame solids; add `speaker_roof_posts-candidate-world.stl` to the final cap. Do not print the posts separately. The two screw-envelope files identify the real mounting space and are not printed parts.

`assembly-check.json` binds the current `custom-harness-package.json`: all independent controller, Pi, USB, amplifier and fixed mechanism bodies are included. **1,700 checks pass**, including staged assembly on the detached cap, both driver cylinders, full screw envelopes, and closure of the changed speaker subset against the fixed mechanism. The later controller/Pi support additions are not in that source manifest and must be checked by the integration owner. This is local mechanical acceptance, not complete-head, electrical, load-strength or physical manufacturing acceptance.

The earlier fixed-controller closure negative is retained. That state was incorrect for the current design: OpenRB, Pi, amp and their rigid connectors attach to the cap and move with it. It is not waived as a collision; it documents why the proposed stationary-controller assembly sequence would fail.

## Assembly and hardware

With the cap detached and board access still open, place the keeper against the roof posts, insert the actual speaker from below, then fit the lower cradle. Fasten the two screws from below before the controller/Pi obstruct the tool approach. Install the rest of the cap-mounted electronics, then close the cap as one subassembly.

The existing geometric hardware intent is retained: two M2.5 × 8 tapping screws, Ø5 × 1.7 mm head envelope, 5.01 mm stack and 2.99 mm pilot engagement. The new pilots are Ø2.1 × 3.3 mm deep, leaving 0.31 mm nominal screw-end allowance. The clearance holes through both cage halves are Ø2.8 mm. This does not certify the actual screw-to-printed-plastic thread fit; it is the same source interface, not a newly asserted stock item.

## Print inputs

- `speaker_cradle-print.stl`: Black ×1, 45.2 × 21.7 × 1.2 mm; intended continuous planar bed contact **250.053 mm²**.
- `speaker_keeper-print.stl`: Black ×1, 45.2 × 21.7 × 1.0 mm; intended continuous planar bed contact **248.865 mm²**.

The exact world-to-print rigid transforms are in the fragment. No material was shaved off a functional ring solely to make it lay flat. Both exported solids are closed and have consistent winding. Their final native slices and functional-hole readback belong to the final incremental plate, which has not yet been sliced.

Reproduce with `build_candidate.py`, then `check_candidate.py`, then `finish_subset.py`, each through the shared 512 MiB / 120 s bounded launcher. The measured heaviest local check was about 212 MiB / 8.5 seconds; no whole-scene union or global layout search is used.
