# XL4015 module (ROBOTIS OMX-AI kit "DC converter")

Source: ROBOTIS Docs interactive assembly guide, follower model with converter=xl4015,
`https://docs.robotis.com/interactive/omx/models/follower-xl4015.glb?v=hardware-v004-materials-v027-timing-v029`
and its manifest `follower-xl4015.json` (fetched 2026-10-14 with `capture_robotis_glb.mjs` + curl). Part `part_0310`,
sourceName `DC_CONVERTER_ROBOTIS`, label "XL4015 DC converter". Steps 57/58 of that guide fit it with four M2 x 6 screws.

`xl4015_module_robotis_mm.stl`: that node alone, world transform applied, scaled to mm (model frame: PCB normal = +y,
long axis = z). Measured from the mesh (trimesh section at the PCB mid-plane):

- PCB outline 61.7 x 26.2 mm, about 1.5 mm thick.
- Components on one face: 12.5 mm tall in the middle (inductor / capacitors), 9.5 mm at both terminal ends.
  Other face: 4.0 mm (pins). Total stack about 18 mm.
- Four mounting holes dia 2.5 mm, 2.6 mm in from each edge: pattern 21.0 x 56.5 mm.
- Screw terminals: IN pair at one end (IN+ / IN- pins 5 mm apart, 3.3 mm from the PCB end), OUT pair at the other end.
- Trimmer location not identified from the mesh; keep a window on the component face over the end regions.
