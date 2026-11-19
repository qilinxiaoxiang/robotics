"""Presentation renderer for flight.py clips (drawing only; called after the run's outcome row is computed).

flight.py uses it only when one of --video-size, --video-fps, --video-look, --video-caption, --cam-smooth, --cam-fovy
(or --video-label, --video-crf, --cam-dist-end, a non-zero --cam-dz) is given; without them flight.py's own render() runs unchanged (640x480, 25 fps, the scene's default look).
The replay is the logged qpos of the same run: every frame is the physics state nearest to its time stamp (qpos is
logged every physics step in this mode, so the time error is at most half a step). Nothing here feeds back into the
simulation. No thrust plumes, no motion blur.

Look "studio": light matte floor with a faint 0.1 m checker (so motion over the floor stays readable), light
background with distance fog, one shadow-casting key light, and for the table scenarios the table drawn as a top on
four legs with the same footprint and top height as the collision box (which is hidden).
"""
import time
from pathlib import Path

import mujoco
import numpy as np

BG = (0.93, 0.935, 0.94)
FONTS = ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/HelveticaNeue.ttc",
         "/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def _studio_look(m):
    floor = m.geom("floor").id
    mat = int(m.geom_matid[floor])
    if mat >= 0:
        texids = np.atleast_1d(m.mat_texid[mat])
        tid = int(texids[texids >= 0][0]) if (texids >= 0).any() else -1
        if tid >= 0:      # faint two-tone checker in place of the blue one (same texture size and repeat)
            w, h, nc, adr = int(m.tex_width[tid]), int(m.tex_height[tid]), int(m.tex_nchannel[tid]), int(m.tex_adr[tid])
            yy, xx = np.mgrid[0:h, 0:w]
            chk = ((xx * 2 // w) + (yy * 2 // h)) % 2
            img = np.where(chk[..., None] == 0, np.array([206, 207, 208]), np.array([195, 196, 198])).astype(np.uint8)
            if nc == 4:
                img = np.concatenate([img, np.full((h, w, 1), 255, np.uint8)], axis=2)
            m.tex_data[adr:adr + w * h * nc] = img[..., :nc].ravel()
        m.mat_reflectance[mat] = 0.0; m.mat_specular[mat] = 0.0; m.mat_shininess[mat] = 0.0
        m.mat_rgba[mat] = [1, 1, 1, 1]
    for tid in range(m.ntex):     # skybox: flat light background
        if m.tex_type[tid] == mujoco.mjtTexture.mjTEXTURE_SKYBOX:
            n = int(m.tex_width[tid]) * int(m.tex_height[tid]) * int(m.tex_nchannel[tid]); adr = int(m.tex_adr[tid])
            px = np.array([int(255 * c) for c in BG] + [255], np.uint8)[:int(m.tex_nchannel[tid])]
            m.tex_data[adr:adr + n] = np.tile(px, n // len(px))
    m.vis.rgba.fog[:] = [*BG, 1]; m.vis.rgba.haze[:] = [*BG, 1]
    ext = float(m.stat.extent)
    m.vis.map.fogstart, m.vis.map.fogend = 3.5 / ext, 11.0 / ext
    m.vis.headlight.ambient[:] = 0.42; m.vis.headlight.diffuse[:] = 0.22; m.vis.headlight.specular[:] = 0.0
    if m.nlight:                  # key light from the upper front-left, casting the shadows
        v = np.array([0.16, 0.24, -1.0]); v /= np.linalg.norm(v)
        m.light_dir[0] = v; m.light_castshadow[0] = 1
        m.light_diffuse[0] = 0.55; m.light_ambient[0] = 0.0; m.light_specular[0] = 0.15
    m.vis.quality.shadowsize = 8192


def _add_box(scn, pos, size, rgba):
    if scn.ngeom >= scn.maxgeom:
        return
    g = scn.geoms[scn.ngeom]
    mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_BOX, np.array(size, float), np.array(pos, float),
                        np.eye(3).ravel(), np.array(rgba, np.float32))
    scn.ngeom += 1


def _draw_table(scn, c, half, top_z):
    """Top and four legs inside the collision box's footprint; the top surface is the collision box's top."""
    wood, leg = (0.80, 0.66, 0.47, 1), (0.30, 0.31, 0.33, 1)
    th, lg = 0.018, 0.022
    _add_box(scn, [c[0], c[1], top_z - th], [half[0], half[1], th], wood)
    _add_box(scn, [c[0], c[1], top_z - 2 * th - 0.03], [half[0] - 0.05, half[1] - 0.05, 0.03], leg)      # apron
    for sx in (-1, 1):
        for sy in (-1, 1):
            _add_box(scn, [c[0] + sx * (half[0] - 0.05), c[1] + sy * (half[1] - 0.05), (top_z - 2 * th) / 2],
                     [lg, lg, (top_z - 2 * th) / 2], leg)


CJK_FONTS = ("/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/PingFang.ttc",
             "/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf")


def _caption_overlay(text, W, H, lower=False):
    """RGBA strip with the text, and its top-left position: the frame's top-left corner, or (lower) a lower-third label
    at 80 % of the frame height. The font size follows the shorter side of the frame."""
    from PIL import Image, ImageDraw, ImageFont
    size = max(12, round(min(H, W) * 0.027))
    font = None
    for f in (CJK_FONTS if any(ord(ch) > 0x2E7F for ch in text) else ()) + FONTS:
        if Path(f).exists():
            font = ImageFont.truetype(f, size); break
    if font is None:
        font = ImageFont.load_default()
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=font)
    px, py = round(size * 0.6), round(size * 0.42)
    img = Image.new("RGBA", (x1 - x0 + 2 * px, y1 - y0 + 2 * py), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=round(size * 0.35), fill=(20, 22, 26, 185))
    dr.text((px - x0, py - y0), text, font=font, fill=(255, 255, 255, 255))
    arr = np.asarray(img).astype(np.float32)
    margin = round(min(H, W) * 0.033)
    return arr[..., :3], arr[..., 3:4] / 255.0, margin, (round(H * 0.80) if lower else margin)


def render(m, d, a, qlog, qdt):
    import imageio
    t0 = time.time()
    W, H = (int(v) for v in (a.video_size or "640x480").lower().split("x"))
    fps = float(a.video_fps or 25)
    studio = a.video_look == "studio"
    if studio:
        _studio_look(m)
    m.vis.global_.offwidth = max(int(m.vis.global_.offwidth), W); m.vis.global_.offheight = max(int(m.vis.global_.offheight), H)
    if a.video_size or studio:
        m.vis.quality.offsamples = 8
    if a.cam_fovy:
        m.vis.global_.fovy = a.cam_fovy
    r = mujoco.Renderer(m, H, W)
    cam = mujoco.MjvCamera(); cam.azimuth, cam.elevation, cam.distance = a.cam_az, a.cam_el, a.cam_dist
    opt = mujoco.MjvOption(); opt.geomgroup[3] = 0      # the pack itself is drawn (visual_parts); hide the collision boxes
    trunk = m.body("trunk_base").id
    table = m.geom("table").id
    draw_table = studio and a.scenario in ("table_up", "table_down")
    if studio:
        m.geom_rgba[table, 3] = 0.0                     # hidden; the drawn table replaces it in the table scenarios
    caps = [_caption_overlay(a.video_caption, W, H)] if a.video_caption else []
    if a.video_label:
        caps.append(_caption_overlay(a.video_label, W, H, lower=True))
    ease = [float(v) for v in a.cam_ease.split(",")]
    wr = imageio.get_writer(a.video, fps=fps, codec="libx264", macro_block_size=1, quality=None, pixelformat="yuv420p",
                            output_params=["-crf", f"{a.video_crf:g}", "-preset", "slow", "-movflags", "+faststart"])
    n = int(math_floor((len(qlog) - 1) * qdt * fps)) + 1
    look = None
    last = None
    for i in range(n):
        q = qlog[min(len(qlog) - 1, int(round(i / fps / qdt)))]
        d.qpos[:] = q
        mujoco.mj_forward(m, d)
        if a.cam_dist_end is not None:                   # ease the camera distance (smoothstep between the two times)
            s = float(np.clip((i / fps - ease[0]) / max(1e-6, ease[1] - ease[0]), 0, 1)); s = s * s * (3 - 2 * s)
            cam.distance = a.cam_dist + (a.cam_dist_end - a.cam_dist) * s
        if a.cam_follow:
            p = d.xpos[trunk].copy()
            if look is None or not a.cam_smooth:
                look = p
            else:                                        # first-order lag on the look-at point (camera only)
                look = look + (p - look) * (1 - np.exp(-1 / fps / a.cam_smooth))
            cam.lookat[:] = look + np.array([0.0, 0.0, a.cam_dz])
        else:
            cam.lookat[:] = [0.25, 0, 0.55]
        r.update_scene(d, cam, opt)
        if studio:
            r.scene.flags[mujoco.mjtRndFlag.mjRND_FOG] = 1
            r.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION] = 0
        if draw_table:
            _draw_table(r.scene, m.geom_pos[table], m.geom_size[table], float(m.geom_pos[table][2] + m.geom_size[table][2]))
        f = r.render()
        if caps:
            f = f.copy()
        for rgb, al, x, y in caps:
            reg = f[y:y + rgb.shape[0], x:x + rgb.shape[1]].astype(np.float32)
            f[y:y + rgb.shape[0], x:x + rgb.shape[1]] = (reg * (1 - al) + rgb * al).astype(np.uint8)
        wr.append_data(f)
        last = f
    wr.close()
    if a.still_t is not None and a.still_t < 0 and last is not None:     # --still-t -1: the last frame
        imageio.imwrite(str(Path(a.video).with_name(Path(a.video).stem + "_end.png")), last)
    print(f"RENDER_HD {a.video} {W}x{H} {fps:g}fps frames={n} wall_s={time.time() - t0:.1f}", flush=True)


def math_floor(x):
    return int(np.floor(x + 1e-9))
