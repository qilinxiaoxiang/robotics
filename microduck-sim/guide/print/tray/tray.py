"""OpenRB-150 tray for the MicroDuck power-support lower deck. Robot frame, mm (x fwd, y left, z up).
Base plate bottom on the deck top (z=-55.5). Printed base down (bed plane z=-55.5)."""
import cadquery as cq, json, sys

P = dict(
    Zd=-55.5, t=1.2,            # deck top, plate thickness
    Zpcb=-50.5, pcb=1.6,        # PCB bottom, thickness
    deck_x=(-59.1, -10.95), deck_hw=17.2,          # on-deck plate (front edge overhangs deck front -11.9 by 0.95)
    cant_x=(-85.5, -59.1), cant_hw=15.3,           # cantilever plate behind deck
    thick_x=(-85.5, -58.2),                        # thickened cantilever zone (stepped by y band)
    thick_bands=[(0.0, 4.6, -53.3), (4.6, 8.6, -52.85), (8.6, 13.4, -52.45)],  # (|y| from, to, top z)
    standoffs=[(-54.93, 12.7), (-54.93, -12.7), (-16.07, 12.7), (-16.07, -12.7)], cut_d=6.0,
    straps=[-43.25, -27.75], strap_w=4.4, strap_y=5.5, strap_slot_y=(2.0, 5.5), strap_depth=0.6,
    front_pad_x=(-17.5, -12.75), front_y=(4.7, 9.5),
    post_x=(-12.75, -10.95), lip_x=(-14.95, -12.75), lip_y=(5.0, 9.5), lip_gap=0.3, lip_t=1.5,
    ribs=[((-54.2, -17.5), (-9.4, -7.8)), ((-36.7, -17.5), (7.8, 9.4)),
          ((-51.5, -19.6), (10.95, 12.3)), ((-51.5, -19.6), (-12.3, -10.95))],
    rear_holes=[(-76.7, 10.25), (-76.7, -10.25)], pad_d=5.5, pilot_d=1.7,
    rails_x=(-85.5, -58.4), rail_y=(13.3, 15.3), rail_top=-43.5, pad_chamfer=0.6,
    # side DYNAMIXEL ports: the JST-EH housings sit at x -64.7..-54.7 with their mouths 0.6 mm inside the rails,
    # so each rail is cut down to just below the PCB top where the plug goes in (interference-audit/tray-port.json)
    port_notch_x=(-66.2, -58.0), port_notch_y=(13.0, 15.7), port_notch_z=-49.4,
)

def box(x, y, z):
    return cq.Workplane('XY').box(x[1]-x[0], y[1]-y[0], z[1]-z[0], centered=False).translate((x[0], y[0], z[0]))

def cyl(cx, cy, z0, z1, d):
    return cq.Workplane('XY').circle(d/2).extrude(z1-z0).translate((cx, cy, z0))

def build(p=P):
    Zd, Zt = p['Zd'], p['Zd'] + p['t']
    Zp = p['Zpcb']; Ztop = Zp + p['pcb']
    # plate: on-deck + cantilever, rounded outer corners
    plate = (cq.Workplane('XY').workplane(offset=Zd)
             .polyline([(p['cant_x'][0], -p['cant_hw']), (p['cant_x'][1], -p['cant_hw']), (p['cant_x'][1], -p['deck_hw']),
                        (p['deck_x'][1], -p['deck_hw']), (p['deck_x'][1], p['deck_hw']), (p['cant_x'][1], p['deck_hw']),
                        (p['cant_x'][1], p['cant_hw']), (p['cant_x'][0], p['cant_hw'])]).close().extrude(p['t']))
    plate = plate.edges('|Z').fillet(0.8)
    body = plate
    # stepped thick zone on the cantilever (stays below every board-bottom feature during the slide)
    for a, b, ztop in p['thick_bands']:
        for s in (1, -1):
            y0, y1 = sorted((s*a, s*b))
            body = body.union(box(p['thick_x'], (y0, y1), (Zt - 0.01, ztop)))
    # rear screw pads (full height to PCB bottom), top edge chamfered as an entry ramp
    for hx, hy in p['rear_holes']:
        pad = cyl(hx, hy, Zt - 0.01, Zp, p['pad_d']).faces('>Z').edges().chamfer(p['pad_chamfer'])
        body = body.union(pad)
    # outboard side rails: cantilever stiffeners, board guide rails and USB-C bumper ears (rear ends)
    for s in (1, -1):
        y0, y1 = sorted((s*p['rail_y'][0], s*p['rail_y'][1]))
        rail = box(p['rails_x'], (y0, y1), (Zt - 0.01, p['rail_top']))
        rail = rail.edges('|Y').edges('>Z').fillet(1.0)
        body = body.union(rail)
    # front pads, posts and lips (PCB front edge slides under the lips)
    for s in (1, -1):
        y0, y1 = sorted((s*p['front_y'][0], s*p['front_y'][1]))
        body = body.union(box(p['front_pad_x'], (y0, y1), (Zt - 0.01, Zp)))
        lip_lo = Ztop + p['lip_gap']; lip_hi = lip_lo + p['lip_t']
        body = body.union(box(p['post_x'], (y0, y1), (Zt - 0.01, lip_hi)))
        ly0, ly1 = sorted((s*p['lip_y'][0], s*p['lip_y'][1]))
        lip = box(p['lip_x'], (ly0, ly1), (lip_lo, lip_hi))
        lip = lip.faces('<Z').edges('|Y').edges('<X').chamfer(0.5)   # entry chamfer at rear-bottom edge
        body = body.union(lip)
    # ribs under the PCB
    for xr, yr in p['ribs']:
        body = body.union(box(xr, yr, (Zt - 0.01, Zp)))
    # cuts: standoff clearance holes, zip-tie slots + strap channels, pilot holes
    for cx, cy in p['standoffs']:
        body = body.cut(cyl(cx, cy, Zd - 1, Zp + 5, p['cut_d']))
    for sx in p['straps']:
        xr = (sx - p['strap_w']/2, sx + p['strap_w']/2)
        body = body.cut(box(xr, (-p['strap_y'], p['strap_y']), (Zt - p['strap_depth'], Zt + 0.5)))
        for s in (1, -1):
            y0, y1 = sorted((s*p['strap_slot_y'][0], s*p['strap_slot_y'][1]))
            body = body.cut(box(xr, (y0, y1), (Zd - 1, Zt + 1)))
    for hx, hy in p['rear_holes']:
        body = body.cut(cyl(hx, hy, Zd - 1, Zp + 1, p['pilot_d']))
    for s in (1, -1):
        y0, y1 = sorted((s*p['port_notch_y'][0], s*p['port_notch_y'][1]))
        body = body.cut(box(p['port_notch_x'], (y0, y1), (p['port_notch_z'], p['rail_top'] + 1)))
    assert len(body.solids().vals()) == 1 and body.val().isValid() and body.val().Volume() > 0, 'tray build failed'
    return body

if __name__ == '__main__':
    b = build()
    s = b.val()
    print('valid', s.isValid(), 'volume', round(s.Volume(), 2), 'solids', len(b.solids().vals()))
    bb = s.BoundingBox(); print('bbox', [round(v, 2) for v in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)])
    cq.exporters.export(b, 'openrb_tray-world.step')
    cq.exporters.export(b, 'openrb_tray-world.stl', tolerance=0.01, angularTolerance=0.1)
    json.dump(P, open('tray-params.json', 'w'), indent=1)
