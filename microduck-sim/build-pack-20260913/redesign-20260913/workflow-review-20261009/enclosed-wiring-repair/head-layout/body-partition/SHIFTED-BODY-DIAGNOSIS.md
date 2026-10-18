# One shifted rear-bay pose

Native OpenRB origin is [-29.5,0,-1] mm; native X→world Y, native Y→world Z, native Z→world X. No other movement was tested and no shell was cut.

The previous two header-seat contacts with the torso base disappear. 118 unchanged, closed, positive-volume original STL components pass all 354 exact individual component checks against the torso base and both body shells. The other 24 source components cannot all be treated as positive-volume closed STL solids; their separately source-proven conservative component enclosures pass all 72 corresponding checks. This is conservative clearance evidence for those 24, not an invented exact-BRep pass. All real lower pins remain included.

The upward USB-C mould still intersects the left and right body roof by 106.738 and 65.541 mm³. The corrected source socket mouth is [-26.27,0.015,31.9] mm, outward +Z. The mould shoulder uses the separately stated assumed 1.2 mm exposed-metal gap. A 9×14 mm proposed corridor at X[-30.77,-21.77], Y[-7,7], Z[37,44] intersects 156.852 mm³ of the left shell and 104.403 mm³ of the right shell, but zero torso-base material.

This corridor is **not an existing service hole**. It crosses the two body-shell upper skins and their centre seam. The local intersected material spans Z38.845–42.009; no additional lower rib appears inside this bounded query. Cutting would therefore create a new opening through the original body surface and split the local shell-seam span. Neither aesthetics nor structural strength is accepted. The nearest nominal installed screw shaft is 13.253 mm from the query; no recorded fastener shaft is crossed, but that does not prove the shell load path is unaffected.

Native/source references: left shell source ID8 `7.obj` / `left_shell`, right shell ID10 `8.obj` / `right_shell`, torso base ID34 `m.obj` / `trunk_base`. Full world transforms and nearby screw records are in `corridor-fastener-proximity.json`. `usb-corridor-sections.svg` shows the same query at Z37/40/43; red is a query, not a proposed approved cut.

Known head alternative: the old curved-head OpenRB board alone cleared the original cap; the front Pi +0.5 mm pose also cleared fixed head parts individually. Those facts do not establish simultaneous board/plug clearance. The old OpenRB rear-facing 27 mm USB-C assembly crossed the original closed head boundary. Earlier failed joint/lane poses only reject those poses; they do not establish that all possible front/rear arrangements fail. No additional head pose was searched here.
