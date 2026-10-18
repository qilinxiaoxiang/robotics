# Unscrewed holes in the printed parts

Problem P5. `unscrewed_holes.py` finds every screw-sized hole in the 49 printed parts of the current guide and says whether a guide screw (or a leg-guide screw) sits on it. Method and stages are in the script docstring. Run it under the bounded runner given there; `--stage classify` reuses the cached detect and probe results.

## Result (2026-10-13, guide revision guide-20261012)

177 hole records: 128 carry a guide screw, 46 a leg-guide screw, 1 is documented as having another purpose (the jaw pivot centring hole), and 2 are candidate missing screws. `unscrewed-holes.json` holds every record; `missingScrewCandidates` lists the open ones.

- **Passive support top tabs into the yaw links** (4 joints, 8 records). Each tab has a 2.2 mm hole facing a 2.05 mm, 3.4 mm deep pilot in the yaw link. Shawn fitted M2 × 6 in all four on 2026-10-12. They are now in the guide as `P-passive_tab-01..04` (step hip-roll-refit). The heads keep at least 0.58 mm from the hip bridge over the full hip-roll range (±0.384 rad) and 1.6 mm from the hip-roll motor case.
- **Torso shells, rear cross hole at x −38, z 35** (1 joint, 2 records). The left shell has a 2.2 mm clearance hole behind a 3.5 to 3.8 mm bore; the right shell has a 1.6 mm, 4.8 mm deep pilot. No schedule uses it, and a stocked M2 head (about 4.0 mm) does not pass the 3.5 mm bore. The proposed fix (left tunnel bored to 4.4 mm from y 2.05 to its mouth in the shell reprint, walls at least 0.95 mm; one M2 × 6 dropped in from the left, head on the tunnel floor at y 2.05, 3.2 mm of shank in the right pilot, tip 1.5 mm short of the pilot end) waits for Shawn's confirmation of the connection method; the path is clear of every part and cable (nearest cable 5.9 mm). Only even M2 lengths are stocked, so M2 × 7 is not an option.

The `clear` stage named in the docstring is not wired into the main run. The head clearances above were measured separately (surface sampling, 33 roll angles).
