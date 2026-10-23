# U20CAM model from the ROBOTIS OMX-F CAD

Source: ROBOTIS OMX hardware page (https://ai.robotis.com/omx/hardware_omx.html), OMX-F STEP
(https://www.robotis.com/service/download.php?no=2224, file OMX-AI-Follower.stp, Creo export 2026-09-15), part
`CAMERA_INNOMAKER_720P`. Read 2026-10-23 with `extract_step_part.py <stp> <outdir> CAMERA`.

`u20cam-local.stl`: the camera in its own frame, mm. Board in the u-v plane (32 x 32), w along the lens axis, lens towards -w.

- PCB: w 7.38..8.98 (1.6 thick); four corner holes dia 2.09 on a 28.0 square; two dia 1.2 holder-screw holes 18.0 apart.
- Holder base 21.9 x 13.1, 4.0 above the PCB front; round body dia 13.4 to 12.0 above it.
- Lens barrel dia 11.9 to 18.0; front ring dia 14.0 from 18.0 to 22.0. Lens front 22.0 mm above the PCB front.
- Plug on the back: 8.5 x 3.5, 5.0 tall, u -10.7..-2.2 at the +v edge (v 10.9..14.4).

The face-u20 build used render estimates (lens front 15.4, ring dia 15.1, holder 5.5, plug 3.0 tall centred).
`real_cam_fit.py` places this model in the head (lens along +x, plug edge to +y): with the V1.30 bosses the lens front
is at x 95.6, 6.2 mm past the trim; with the board 6.6 mm further back (bosses 14.3 mm) it is at x 89.0 and the nearest
parts are the trim bore 1.0 mm, face 1.7, lower shell 3.9, cap 5.6, jaw frame 7.0 (`real_cam_fit.json`).
