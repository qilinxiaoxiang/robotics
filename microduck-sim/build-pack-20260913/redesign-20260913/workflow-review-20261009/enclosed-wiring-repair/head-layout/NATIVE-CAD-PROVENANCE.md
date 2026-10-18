# Native CAD source for enclosed head repair

The eligible XL330 source is **fanhao375/microduck-replica-cad v1.1**, not the removed STL collection in the main repository and not the FT changed-parts STEP package. The downloaded 332,776,144-byte release matches its published SHA256. Actual ZIP inspection found 57 SolidWorks files and no STEP. Eighteen relevant head files are extracted in `sources/head-source/`.

Start with `top_head_shell_头部上壳.SLDPRT`, then the dependent `10_头部总成.SLDASM`. Autodesk documents native SolidWorks upload/translation; source feature history does not transfer. A successful import must be read back as a solid BREP, with curve/surface types and dimensions checked. The original SLDPRT was subsequently imported successfully in Fusion Education; it is a faceted BREP, with the readback below. That does not make earlier STL mesh imports analytical or parametric solids.

The source PDF pages 14–15 show parallel transverse boards behind the face. The archive contains a Zero2W reference and RobotHAT; it does not contain OpenRB or the owned USB adapter pair. The newer README names Radxa in its BOM, which does not change the archived CAD component identity. Thus neither the original placement nor its general instruction to install ribbon before closing proves clearance for our first-generation ZeroW/OpenRB wiring.

No controller-topology change, shell-hole relocation or whole-scene mesh-to-BREP conversion is made here. Native v1.1 was geometrically registered to the community cap as detailed below; any locally modified current cap must retain its own feature lineage. Existing FT fit parts, camera-hole variants and changed ankle revisions must not silently replace the assembled XL330 robot. The machine-readable report binds sources and names the narrow next checks.

## Native readback update
Fusion Education imported the original cap as one solid with 13,588 planar faces. The source is a faceted BREP; its analytical curves and parametric history have not been recovered. `native-cap-comparison.json` registers it to the community cap within export precision (directional differences 0.02769/0.02316 mm³), not exact boolean equality.
