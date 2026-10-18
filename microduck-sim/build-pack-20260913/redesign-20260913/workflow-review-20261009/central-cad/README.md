# Central battery C — real source reference and structural skeleton

Problem P0/P5. Stage review dated 2026-10-09. **Not printable and not whole-robot acceptance.** No V1.4 geometry changed.

The supplied 8 MB complete `reference/microduck/cad/microduck.step` is an earlier humanoid with arms. XCAF inspection found 21 assemblies / 275 leaf components including shoulder, humerus, radius, pelvis and chest. These are not the current 15-motor duck. Its saved BREP leaves and inventory are historical evidence only. There is no rigid registration that makes its different mechanism the current robot.

The pinned AI-FanGe commit `49678215d0b40529522772a40c06c216390449dd` has the community 3MF/STL sources, but no current complete STEP. The trustworthy current geometry is the registered per-part mesh from the guide, with the final head scene replacing all historical head parts. Meshes remain meshes; no reconstructed analytic geometry or native feature history is claimed.

## Open in Fusion

- `fusion-import-manifest.json`: 166 separately named STL mesh references, colors, groups, millimeter units, and source hashes. World coordinates already include C's ±11 mm whole-leg translation. **Do not apply the translation again.**
- `current-duck-baseline-mesh-reference.3mf`: original registered layout, 166 mesh objects.
- `current-duck-C-mesh-reference.3mf`: 166 current reference meshes plus the nominal C bank envelope. This is an assembly reference, not a print plate.
- `C-lowered8-loadpath-skeleton.step`: 9 valid analytic load-path box primitives and one nominal battery box; read back as 10 valid BREP shapes. No original printed part is mislabeled as BREP.
- `central-bridge-primitives.json`: the same primitive dimensions and 16 original mounting-hole axes for direct Fusion scripting. The neck axes remain fixed; hip case axes translate with their entire legs.
- `mesh-export-readback.json`: all STL triangle corners checked against the source point coordinates plus only the stated translation, within float32 roundoff.

The initial C envelope has center `[-5,0,-6]`, size `80.9 × 26 × 65.9 mm`. It conflicts with the old central base/power structure and overlaps the ID12 receiving box. The independent **lowered8** skeleton uses battery center `[-5,0,-14]`; the original C remains unchanged for comparison. Both retain the same +22 mm total stance increase, yaw-axis spacing 57 mm and hip-pitch spacing 107 mm.

## Concrete structural direction

Replace the old plate crossing through the battery with two hip saddles connected above the battery. The skeleton connects upper hip case rails through inner webs to a central upper bridge, then to cheeks surrounding the unchanged neck attachment. Its bridge is Z20..22 mm, bank top is Z18.95 mm, and case-facing webs retain 1 mm from the conservative hip motor bodies. Both battery end faces remain open for front/rear cable access and extraction.

The original source hole axes are recorded, not invented. The eventual neck cheeks must retain the actual shaft, sliding-bearing and screw-pocket profiles from community 8/10. The current boxes intentionally do not model those recesses. The lower hip seat islands around S10-case069/070 and S05-case073/074 must also be connected back to the frame: upper rails alone are not a finished retention design. Screw stack/length, tray floor/straps and converter relocation remain detailed-design work.

C remains preferable to B: both need the same lateral shift and central redesign, but B is 15 mm taller. Holding the same top clearance would put B's bottom 15 mm lower. B has no established cable-access advantage that compensates for this in the current evidence.

## Bounded evidence

`selected-central-intersections.json` compares the nominal B/C bank against 16 selected real central source meshes. C overlaps the existing base 749 mm³, old power support 6646 mm³, left/right shells 558/457 mm³ and the converter receiving box 6240 mm³. This establishes which structures must change; it is not a failure of the new yet-undesigned frame. Invalid source motor meshes are explicitly incomplete in this initial boolean report; separated AABBs are recorded independently.

`actual-central-sections.svg` shows actual mesh-plane contours at Y0 and Z0, not bounding-box silhouettes. Remote legacy fuse geometry is clipped from the plot; it remains in the numerical report and assembly reference.

`central-bridge-static.json` checks the proposed lowered8 skeleton against 51 intact shifted leg and fixed neck pieces, plus the battery: zero intersections at neutral pose. Open source motor meshes are replaced only for this conservative test by closed convex hulls enclosing all source vertices. Minimum observed gap is 1 mm to the hip motors, 1.05 mm to the bank. The structural union has one connected component. This does not certify bearing pockets, all hardware, strength, insertion, or joint motion. Replaced legacy central pieces are excluded explicitly, never hidden as a clearance pass.

Resource receipts record each isolated task. The historical STEP import used 393 MiB / 9.6 s; selected mesh checks 259 MiB / 2.4 s; skeleton checks 380 MiB / 4.7 s; skeleton STEP export/readback 283 MiB / 2.1 s. No whole-scene search, slicing, source-part editing or purchasing was performed.
