# Small ankle ring: the actual two interfaces

Problem P5; checked2026-10-06. The printed14.6mm part is a single plain annular sleeve. It has no separate inner/outer races, balls, or internal rolling mechanism. The user's observation that it stays tightly on the lower-leg link is consistent with the actual source geometry. It does not imply that the ankle joint should be fixed: when the sleeve stays on the link, the orange ankle must move relative to the sleeve's outer circumference and its contacting end face.

## Direct source measurements

`verify_ring_explanation.py` reads the untouched community3MF sources62/66/30, places them using the current guide's actual transforms, and independently samples64 directions plus complete material cross-sections. It returns a dictionary through `verify()` without writing files. The CLI and guide verifier may print `RING_INTERFACE_CHECK_PASS`. `ring-investigation.json` binds the inputs, code and current guide by SHA256.

- Source62 is the small ring; source68 is the same named community ring copy.14.6mm is its **outside diameter**, not its bore. Its width is3.0mm; the effective faceted bore diameter is9.643–9.652mm, approximately9.65mm.
- The lower-leg source30's actual cylindrical outer boss is approximately10.0mm: the64-direction effective diameter range is9.985–10.006mm. Its central opening is approximately5.5mm; that opening is **not** the boss's exterior or the ring's mating diameter.
- The orange source66 ankle pocket is approximately15.0mm: the effective range is14.980–15.006mm.
- The nominal source ring bore and source link boss overlap by0.168–0.179mm radially, roughly0.35mm diametrically. At each of three full cross-sections, their actual material intersection is5.3422mm². This is a real CAD interference, not merely a guess about printer shrinkage. It does not establish that the community author intended this particular amount of press fit.
- Before physical deformation, the ring's outside and the ankle pocket have0.190–0.204mm radial clearance, approximately0.4mm diametrically. Their source material cross-sections do not overlap.
- The ring is one watertight connected solid, Euler number0, volume282.875mm³. The material cross-section area is94.2916mm² at all sampled axial positions: one full annulus, not two independently moving rings.

These are nominal mesh measurements. Facet chords and a few micrometres of registration offset explain the small directional ranges. They are not measurements of the already printed parts.

## Position and axial contact

The guide's native ring centre differs from the original assembled FK reference ring centre by only0.002373mm. The ring is also aligned with the ankle motor's joint axis. The native placement is therefore not displaced onto an unrelated hole.

In the ring's local frame, its positive end is atz=+1.5mm. A direct axial ray at radius7.2mm finds the orange ankle's actual shoulder atz=1.5000028mm: the ring end is essentially seated against that shoulder. Atz=1.75mm on the outward side, all64 directions find a lip with an inside diameter of about14mm. Higher sections need not have the same complete shape. This supports inspecting the axial end-face interface as well as the outer cylindrical interface; it does not prove a particular assembly sequence or that a merged component would be impossible to install.

The full assembled bodies establish the motion relation: motor6's case and lower-leg link belong together, while the orange ankle is driven by the motor output. The sleeve need not slide relative to the printed link boss if it is held there. The actual relative rotation can occur at sleeve exterior ↔ ankle pocket, with end-face sliding at the shoulder. Calling this a sleeve around a “passive rear shaft” was imprecise: the directly measured mating feature here is the **printed lower-leg boss**, not a separately fitted ROBOTIS idler horn.

The original XML assigns the reference bearing visual to the ankle body. That assignment alone does not prove which interface is fixed: the part is circular, coaxial and rotationally symmetric, so rotating it around this axis leaves its visible geometry effectively unchanged.

## Printed ring versus original reference asset

The original `seeed_bearing__configuration_default.stl` reference asset has approximately15mm exterior,10mm middle bore and3mm width, with chamfers at both axial ends. The current community print source62 instead has14.6mm exterior, approximately9.65mm bore and flat unchamfered annular ends. They are not dimensionally identical parts.

The reference part's name and simplified annular STL do not establish whether the intended original hardware was a metal rolling bearing or a plain sleeve; internal hardware may be omitted from a visual CAD model. The currently printed source, however, demonstrably contains no internal rolling mechanism and acts as a sliding sleeve.

The checked [FanGe README](https://github.com/AI-FanGe/Microduck-build-tutorial/blob/main/README.md) lists printed structural parts and recommended PLA, but provides no explicit explanation of why this sleeve is separate or of a deliberate inner press fit. The checked [upstream README](https://github.com/pollen-robotics/microduck/blob/main/README.md) also gives no such mechanical rationale. This is a boundary on the checked evidence, not proof that no explanation exists anywhere.

## Could it be one part with the link?

In principle, yes: a lower link with the same enlarged outer cylindrical bearing surface could still rotate relative to the orange ankle. A separate ring is not mathematically required for that relative motion.

A separate insert can make wear replacement, material choice and local fit adjustment easier while retaining the long link. Those are engineering reasons for keeping an insert; they are **not documented author intent** in the sources checked here. Integrating it would still require checking the preserved bearing clearance, axial shoulder, wall strength and assembly path. Simply deleting the ring or combining the current overlapping meshes is not an accepted redesign. No CAD or printed dimension has been changed in this investigation.

A tight fit can also expand the sleeve's exterior. Therefore the uninstalled14.6mm exterior and15mm pocket do not guarantee that the installed pair moves freely. The useful physical question is whether the **orange ankle can move relative to the sleeve/link assembly**, with gear resistance distinguished from the sliding interface. There is no requirement that the sleeve visibly spin on the link. Installed expansion, friction and actual joint motion remain unverified.

## Minimal cross-section data for a diagram

Use a cut perpendicular to the ankle axis near the ring centre. Show a fixed printed lower-link boss with nominal outer radius5.0mm and central opening radius2.75mm; the sleeve spans nominal radii4.825–7.3mm; the orange pocket starts at radius7.5mm. Mark the0.175mm nominal radial inner interference separately from the0.20mm nominal outer clearance. The apparent overlapping band is intentional in the drawing of **source dimensions**, not a claim that installed material can occupy the same volume. Add an axial side view with the sleeve spanningz=-1.5..+1.5mm and the shoulder touching at+1.500003mm.

No printer job, CAD edit, dimension change or hardware motion test was performed.
