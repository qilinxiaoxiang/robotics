# MicroDuck individual replacement parts — 8 October 2026

The numbered files correspond to the online replacement list. Units: mm. Geometry retains the assembly world frame. These are individual STL geometry inputs, not sliced printer jobs. Select the matching printer/material and inspect orientation, supports and all functional seats in the native slicer before printing.

Only parts marked “Geometry ready · fit prototype” are in the download. Held camera/audio parts are listed separately to prevent printing a design whose cable route can still change.

## Individual parts

- **01 · Split jaw main body** — Yellow, ×1; replaces community-4.stl. Included as 01_jaw_frame_yellow_qty1.stl The one-piece passive bearing traps the assembled motor shaft. The removable cheek allows rigid assembly.
- **02 · Removable passive-side jaw cheek** — Yellow, ×1; replaces New part; joins 01. Included as 02_jaw_passive_cheek_yellow_qty1.stl Retains the original complete coaxial bearing; two M2.5 × 8 tapping screws close the cheek after the jaw is seated.
- **03 · Lower lip pad with internal access relief** — White, ×1; replaces community-42.stl. Included as 03_lower_pad_white_qty1.stl Provides room for the cheek joints and screwdriver without changing the exposed lip surface.
- **04 · Curved lower head shell with seat clearance** — Yellow, ×1; replaces community-2.stl. Held; not in the print download. Held: the populated first-generation Zero W needs a revised internal board/header window. The pictured earlier jaw-clearance shell must not be reprinted for the current electronics layout; the revised shell is awaiting integrated assembly checks.
- **05 · Restored curved cap with internal mounts** — Orange, ×1; replaces head-cap-usb-service-print.stl (box conversion). Held; not in the print download. Restores the original curved head and provides controller/audio mounts. Complete cable routing may still change openings or mounts.
- **06 · Face panel with internal camera anchors** — White, ×1; replaces community-76.stl. Held; not in the print download. Supports the eye camera before fitting the Pi. Camera ribbon routing must be settled before freezing its position.
- **07 · Eye trim with camera clearance** — Black, ×1; replaces community-48.stl. Held; not in the print download. Clears the eye-mounted camera lens and its checked field of view; follows the final camera pose.
- **08 · Removable internal camera frame** — Black, ×1; replaces Replaces the rooftop foot and cradle. Held; not in the print download. Held: eye-camera fastening is being revised for rear access before Pi installation. The earlier six-screw frame is not the current manufacturing release; final screw direction, supporting frame and cable clearance remain under review.
- **09 · Speaker lower cradle** — Orange, ×1; replaces New part; replaces the old combined audio carrier. Held; not in the print download. Supports the purchased speaker frame inside the curved cap; wire exits and terminal access must pass before release.
- **10 · Speaker rear keeper** — Orange, ×1; replaces New part; used with 09. Held; not in the print download. Retains the speaker from the rear while leaving its diaphragm free. Install after the prewired amplifier.
- **11 · Head-pitch bracket with even-length screw seats** — Black, ×1; replaces community-28.stl. Included as 11_neck_pitch_black_qty1.stl Adds 1 mm under the four ID13 output screw heads for M2 × 6 tapping screws; clears the four existing thin bore membranes.
- **12 · Left lower-leg link with even-length screw seats** — Black, ×1; replaces community-30.stl. Included as 12_OPTIONAL_lower_black_qty1.stl Optional new-build replacement with four integral 1 mm screw seats for M2 × 6 tapping screws. It is not an instruction to dismantle the completed legs. A separate conditional washer repair preserves the existing links and force-fitted ankles.
- **13 · Right lower-leg link with even-length screw seats** — Black, ×1; replaces community-32.stl. Included as 13_OPTIONAL_right_lower_black_qty1.stl Optional new-build replacement with four integral 1 mm screw seats for M2 × 6 tapping screws. It is not an instruction to dismantle the completed legs. A separate conditional washer repair preserves the existing links and force-fitted ankles.

## Retain existing parts

- **Ankles, feet and completed lower joints** — User reports them seated. Their redesign is deferred.
- **Torso base, rings and power support** — The demonstrated issue is assembly order: install closed rings before joining the legs and power support after fastening.
- **IMU clamp and cover** — Approach the IMU clamp from negative X. Use M2 × 6 pressure screws with the specified 1.8 mm head stand-off; no geometry change.
- **Original complete jaw motor support and upper lip pad** — Retained by the current split-jaw candidate.

Physical fit and material strength remain unverified. Follow PRINTING/WORKFLOW.md for native slicing.

AI assistance was used to draft.
