# Single next candidate — not yet a clearance pass

Use `single_circle_candidate.py` and `single-circle-candidate.json`. The earlier quintic spline candidates are rejected mathematical controls.

Head strain point: `[-47, 23.2, 151]` in neutral world coordinates, fixed to `jaw_soft`, tangent local neutral +Z. Existing R16 outlet starts `[-31,23.2,125]`, turns to +Z at `[-47,23.2,141]`, then travels 10 mm straight. The old +25 mm outlet test already covers this prefix; source bindings remain those recorded in the prior report.

Torso strain point: `[-66,50,35]`, fixed to `trunk_base`, outward tangent +Y. This is a proposed side guide, not the actual IMU connector. Both support clips and their screw access must be designed after the path clears.

The moving tangent first turns through an R16 circular arc to global +Y. A tangent-continuous U joins the resulting point to the torso guide: straight leg, quarter-circle, cross-straight, quarter-circle, straight leg. The core circle radius is min(16, half the XZ chord); straight legs absorb all length variation. The whole free segment is exactly 375 mm. That value is derived from the maximum required U length across all 229 poses, including rigid-invalid poses, rounded up to 5 mm. No angle is silently removed.

Pure math: all 229 endpoints and exact lengths pass. The 186 native-clear poses have minimum center radius 11.506512 mm, so the radius after subtracting the entire Ø7 receiving section is at least 8.006512 mm. This is a geometric receiving bound, not manufacturer fatigue certification. The original rigid-invalid cases remain recorded and can have radius 4.336918 mm. The full source angle domain is therefore not claimed accepted.

Root-only first CAD command, when the sole token is free:

```sh
python3 H/run_bounded_cad.py --max-mib 512 --seconds 120 --report H/cabling-release-20261008/neck-repair/resource-neutral.json -- /tmp/microduck-cad-venv/bin/python H/cabling-release-20261008/neck-repair/check_single_circle_candidate.py --neutral-first --end 0
```

Replace H with the actual absolute head-redesign directory. The checker refuses to run outside the guard. Neutral failure is saved immediately and stops; only a neutral pass warrants a following bounded `--start 0 --end 229` run. Every completed pose is flushed and fsynced to JSONL; source change prevents resuming stale output. No optimizer or parameter sweep is present.

The 375 mm is only the free exterior segment. Add the head-internal trunk, outlet, strain relief and actual terminal fanouts before choosing wire cut lengths. The received 150±10 mm Adafruit4397 is not sufficient by itself, and 250 mm old extensions are not automatically sufficient. This report does not claim new wire stock exists or release procurement holds.

Still required: native solid intersections, self-clearance, intermediate angular motions, local guides/attachment proof, actual connector-to-connector leads, motor buses, prewiring and closure sequence. Pi can move −2Y/−1Z without changing this exterior head-body anchor transform, but the internal bridge must be rechecked against that final pose.
