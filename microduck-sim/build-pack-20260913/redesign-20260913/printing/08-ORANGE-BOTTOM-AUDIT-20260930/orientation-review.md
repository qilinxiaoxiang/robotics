# Orange orientation diagnosis and rigid-transform recommendation

The current orange project has a correctable orientation issue in **community-8**. The earlier conclusion that0.75mm trimming removes meaningful material remains valid, but support presence alone is not a sufficient response. Lay its intended broad bottom face flat, preserve its mesh, then regenerate its support and verify the native first layer.

## Per-part verdict

- **community-8: rotate, do not cut.** Two large near-bottom facet regions total1174.540mm². Their area-weighted normal is tilted **1.997139°** from horizontal; current vertical range is0–0.8760005mm. The plane is intrinsically almost flat: spread along its own normal is only **0.003396mm**. This distinguishes a tilted broad face from a genuinely wavy0.876mm surface. Its intersection with a horizontal slice grows gradually from one edge, explaining small initial contact/patches despite appearing flat in a perspective view. The candidate shortest rigid rotation places the selected face within0–0.003396mm of the bed. At Z=0.1mm, model section grows from **158.116 to1401.220mm²** (8.86×); at0.2mm,328.966 becomes1475.598mm². Volume remains11389.371mm³; no material is removed.

- **community-10: keep current orientation.** Its corresponding broad face totals1178.345mm². Tilt is only **0.038082°**, current Z spread0.036058mm, intrinsic plane spread0.002873mm. A candidate precision rotation improves the0.1mm section from1382.172 to1400.679mm², about1.34%. It is already effectively laid flat at a0.2mm layer scale. A microscopic section at0.0001mm can show separate islands, but that is not evidence that the native0.2mm first layer has the same fragmentation. A diagnostic rotation is recorded, not recommended as necessary.

- **community-60: keep current orientation.** Its low downward facets are exactly horizontal and coplanar. Rotation is the identity. The model’s changes in section are designed edges/pockets, not a tilted intended plane. The0.1mm section routine counts21 polygons, but one is145.6823mm² and all20 others total only0.26975mm²; the largest small polygon is0.12752mm². Therefore raw component count exaggerates the apparent fragmentation; inspect native extrusion paths before classifying these tiny section slivers as a print problem. Flattening or cutting is not justified by that count.

- **community-18: keep current orientation.** Its199.945mm² underside is exactly horizontal and coplanar; candidate transform is the identity. The four through-holes are intended voids. Its0.1mm section is199.9446mm² before and after; no flattening adjustment is needed.

## Applying the candidate

`orientation-candidates.json` binds to the current07-COMPACT orange editable project by SHA-256 and gives each object ID. Apply **only community-8 / object16** unless new native evidence supports another adjustment. The matrix is a world-space left multiplication: `new_build_transform = rigid_world_delta_transform_4x4 @ old_build_transform`. It already rotates around the current bounding-box center and lands the minimum vertex atZ=0. It is the shortest Rodrigues rotation from the measured face normal to downward, with determinant+1 and no extra yaw. Leave all component transforms and mesh vertices unchanged.

Horizontal positions may then be repacked. Re-slice using the current printer/material process, check support/brim separation and bed exclusion zones, and examine the native first-layer model paths. A transformed model section predicts improvement; it is not a substitute for the resliced toolpaths or a physical first-layer test. Do not reuse existing G-code after changing a project transform.

## Method and boundaries

Loaded exact transformed meshes with `analyze_bottom.py:load_meshes`. Selected coplanar-connected near-bottom facets larger than20mm², whose normals are within0.1° of the largest low downward facet. The area-weighted normal and full selected-vertex projection spread distinguish tilt from nonplanarity. The JSON contains exact4×4 matrices, old/new bounds, volumes and section areas at0.0001/0.01/0.05/0.1/0.2mm. These files are analysis artifacts only; no original STL,3MF or G-code was modified.
