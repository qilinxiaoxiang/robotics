"""Where can a Pololu 3419 VL53L8CX carrier (12.7 x 22.9 mm) sit behind the A7Z face panel?
Read-only on the repo. Board lies flat on the face back (x 80.1), components forward, sensor at the
board centre looking +x through a future window. Envelope depth DEPTH covers 0.3 air + 1.8 parts +
1.02 PCB + ~3.4 solder joints and wire bends on the back."""
import json, sys, numpy as np, trimesh
R = '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/'
W, A, F = R + 'world/', R + 'a7z-head/', R + 'face-a7z/'
OUT = sys.argv[1]
FACE_BACK, FACE_FRONT = 80.1, 81.4
DEPTH, MARGIN = 6.5, 0.5
BOARD = (12.7, 22.9)
HALF = np.radians(22.5)          # 45 x 45 deg FoV (Pololu 3419 page)

obs_paths = {
    'face_bosses': F + 'face_panel_a7z.stl', 'eye_trim': F + 'eye_trim_a7z.stl', 'camera': F + 'camera_13m214.stl',
    'head_cap': A + 'head_cap_a7z-world.stl', 'clip_cap': A + 'clip_cap_a7z-world.stl', 'head_bottom': W + 'head_bottom.stl',
    'jaw_frame': W + 'jaw_frame.stl', 'antenna': W + 'antenna.stl', 'antenna_coax': W + 'antenna_coax.stl',
    'clip_head': W + 'clip_head.stl', 'amplifier': W + 'amplifier.stl', 'speaker': W + 'speaker.stl',
    'speaker_retainer': W + 'speaker_retainer.stl', 'touch_xiao': W + 'touch_xiao.stl', 'neck_pitch_ring': W + 'neck_pitch_ring.stl',
}
for p in ['l1', 'l2', 'r1', 'r2', 'm']:
    obs_paths['touch_pad_' + p] = W + f'touch_pad_{p}.stl'
for p in ['pcb', 'soc_a733', 'ram', 'wifi_module_fcu760k', 'usb_c_power', 'usb_c_otg_dp', 'micro_hdmi', 'ipex_socket', 'csi_connector']:
    obs_paths['a7z_' + p] = W + f'a7z_{p}.stl'
M = {k: trimesh.load(p) for k, p in obs_paths.items()}
face = trimesh.load(F + 'face_panel_a7z.stl')

# free depth behind the face back, on a 0.5 mm grid
ys = np.arange(-44, 44.01, 0.5); zs = np.arange(110, 155.01, 0.5)
Y, Z = np.meshgrid(ys, zs, indexing='ij')
start = np.c_[np.full(Y.size, FACE_BACK - 0.05), Y.ravel(), Z.ravel()]
# is there face plate in front (x 80.1..81.4)?
loc, ri, _ = face.ray.intersects_location(np.c_[np.full(Y.size, 70.0), Y.ravel(), Z.ravel()], np.tile([1, 0, 0], (Y.size, 1)))
plate = np.zeros(Y.size, bool)
for i, x in zip(ri, loc[:, 0]):
    if abs(x - FACE_BACK) < 0.05: plate[i] = True
free = np.full(Y.size, 40.0); who = np.array([''] * Y.size, dtype=object)
for k, m in M.items():
    if m.is_watertight:
        inside = m.contains(start)
        free[inside] = 0; who[inside] = k
    loc, ri, _ = m.ray.intersects_location(start, np.tile([-1, 0, 0], (Y.size, 1)), multiple_hits=False)
    if len(ri) == 0: continue
    d = start[ri, 0] - loc[:, 0]
    b = d < free[ri]; free[ri[b]] = d[b]; who[ri[b]] = k
free[~plate] = 0
free = free.reshape(Y.shape); who = who.reshape(Y.shape); plate = plate.reshape(Y.shape)

cone_parts = {k: M[k] for k in ['eye_trim', 'head_cap', 'jaw_frame', 'head_bottom']}
def cone(yc, zc):
    """Fraction of a 45x45 deg pyramid from the sensor aperture (x 79.8) clipped within 1 m, and by what."""
    o = np.array([FACE_BACK - 0.3, yc, zc]); hits = {}
    a = np.linspace(-1, 1, 15) * np.tan(HALF)
    dirs = np.array([[1, u, v] for u in a for v in a]); dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    O = np.tile(o, (len(dirs), 1)); best = np.full(len(dirs), 1000.0); bw = [''] * len(dirs)
    for k, m in cone_parts.items():
        loc, ri, _ = m.ray.intersects_location(O, dirs, multiple_hits=False)
        for i, p in zip(ri, loc):
            d = np.linalg.norm(p - o)
            if d < best[i]: best[i] = d; bw[i] = k
    clipped = best < 1000
    for i in np.where(clipped)[0]: hits[bw[i]] = hits.get(bw[i], 0) + 1
    return round(float(clipped.mean()), 3), hits

# sweep board centres, both orientations
cands = []
need = DEPTH
for orient, (wy, hz) in {'landscape': (BOARD[1], BOARD[0]), 'portrait': (BOARD[0], BOARD[1])}.items():
    for yc in np.arange(-40, 40.01, 0.5):
        for zc in np.arange(112, 153.01, 0.5):
            m = (np.abs(Y - yc) <= wy / 2 + MARGIN) & (np.abs(Z - zc) <= hz / 2 + MARGIN)
            if m.sum() < (wy + 2 * MARGIN) * (hz + 2 * MARGIN) / 0.25 * 0.95: continue
            if not plate[m].all(): continue
            fmin = float(free[m].min())
            if fmin < need: continue
            cands.append(dict(orient=orient, y=float(yc), z=float(zc), min_free=round(fmin, 2),
                              cam_axis_mm=round(float(np.hypot(yc + 0.09, zc - 131.11)), 1)))
print(len(cands), 'footprints fit')
# keep, per side and orientation, the spot closest to the camera axis; then cone-check them
picked = []
for orient in ['landscape', 'portrait']:
    for side in [-1, 1]:
        c = [d for d in cands if d['orient'] == orient and np.sign(d['y']) == side]
        if not c: continue
        c.sort(key=lambda d: d['cam_axis_mm'])
        for d in c[:40]:
            frac, hits = cone(d['y'], d['z'])
            d['cone_clipped'] = frac; d['cone_hits'] = hits
            if frac == 0: picked.append(d); break
        else:
            picked.append(min(c[:40], key=lambda d: d['cone_clipped']))
for d in picked: print(d)
np.savez(OUT + '/freemap.npz', Y=Y, Z=Z, free=free, plate=plate, who=who.astype(str))
json.dump(dict(params=dict(depth=DEPTH, margin=MARGIN, board=BOARD, fov_deg=45, face_back=FACE_BACK),
               n_fit=len(cands), picked=picked, all=cands), open(OUT + '/tof_place.json', 'w'), indent=1)
