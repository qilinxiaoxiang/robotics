# Local restoration of the original curved crown

This candidate actually fills both assistant-added Pi USB crown openings with the corresponding original community curved-shell material. It is not a flat lid or an external cover. The current internal posts, speaker screw pilots, rear OpenRB cable service opening and all other current material are retained.

Use `head-cap-roof-restored-candidate-world.stl` in the existing guide/world millimetre coordinates, without another transform. It is one watertight body with 26,336 triangles. Added material is 494.889149 mm³. Boolean readback found no removed current material or added material outside the original curved shell within 1e-5 mm³ tolerance. Exact source inputs, hashes, port pose and preservation checks are in `roof-restoration.json`.

The exact historical cuts plus a 0.02 mm rim select the reconstruction patch. The rim overlaps existing native material so coincident cut boundaries form a single closed solid. It does not offset the outer surface. An initial zero-rim Boolean produced a numerically zero-volume extra component; that failed attempt is retained in `join-diagnostic-resource.json`. No components were deleted to make the candidate pass. `native-roof-reconstruction-patch-world.stl` is a diagnostic source patch, not a separate printable part.

The initial export of the Boolean *difference* patch was not watertight because of numerical thin slivers. The delivered full cap passed independently; the diagnostic export instead contains the clean original reconstruction patch used for the union. This changes neither the full cap nor its material-preservation checks.

## Interface boundary

The Pi Micro-USB port direction remains nearly world +Z: [0.011537, -0.034125, 0.999351]. The old model's seated shoulder follows the final 2 mm Pi spacers to [67.499093, 4.900770, 141.695534] mm. This shoulder and its 25×18×8 mm body are declared receiving assumptions, not official socket/moulding dimensions. The [official SC0727 page](https://www.raspberrypi.com/products/micro-usb-male-to-usb-a-female-cable/) only establishes the cable interfaces and 80 mm cable length; it imposes no head-roof opening.

That old seated receiving solid overlaps the restored cap by 242.482266 mm³. The restoration therefore does not certify the old upward OTG route. Connecting the plug before closing does not solve that model's final overlap. Rearward routing of the flexible cable alone also cannot change the seated plug body's direction.

The current CAD architecture uses Mac-to-OpenRB USB through the retained rear service hole, with the Pi USB socket empty and the Pi retaining its sensor role. This explicitly removes the old Pi OTG receiving solid from the connected assembly; its failed overlap remains a negative record, not a waived collision. Runtime migration has not been validated.

The entire native reconstruction patch was checked against all 160 non-cap parts in the current original-body manifest: 159 pairs are separated by their exact mesh bounds, and the remaining face-panel pair has zero solid intersection. This includes the current Pi, real discrete header pins, component receivers, camera ribbon and connectors present in that manifest. The patch includes the overlapping 0.02 mm rim, so this is stronger than testing only newly added material. It ran in 7.75 seconds at 323 MiB. `patch-static-check.json` binds every input and reports complete coverage. The cap is ready for CAD integration under this architecture; whole wired closure, physical fit, runtime and printing release are separate gates and are not claimed here.

## Reproduce

From the project root, run the existing head resource guard with 512 MiB / 120 s, `--parallel-light --wait-lock-seconds 30`, and `restore_roof.py`. It loads only the two caps, original USB receiving mesh and small pose/spec inputs. The successful run took 2.0 seconds at approximately 263 MiB. No released print file, root manifest, Fusion UI or current deployment was changed.

Run `check_patch_static.py` through the same bounded guard after reconstruction, then `finalize_adoption.py` with ordinary Python to bind the current architecture and static receipt. The reconstruction-only report is preserved separately.
