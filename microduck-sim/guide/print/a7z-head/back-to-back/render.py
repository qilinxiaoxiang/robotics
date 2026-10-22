"""Pictures of the back-to-back candidate: three vtk renders of the real meshes with labels, written to renders/."""
import json
from pathlib import Path

import matplotlib
import numpy as np
import trimesh
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

import build_b2b as B

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams['font.family'] = 'PingFang SC'
HERE = B.HERE
OUT = HERE / 'renders'
OUT.mkdir(exist_ok=True)
W, H = 1500, 1100
COL = {'cap': '#f4f2ec', 'ears': '#e74c3c', 'pcb': '#2e7d32', 'hs': '#3a3a3a', 'plug': '#8e44ad', 'coax': '#ff8f00',
       'ribbon': '#ffb74d', 'screw': '#111111', 'sd': '#1f6fb2', 'csi': '#5dade2', 'cam': '#2ca02c', 'jaw': '#b03a2e',
       'fixed': '#bdbdbd', 'fan': '#9e9e9e'}


def actor(m, color, opacity=1.0, clip=None, front=False):
    pts = vtk.vtkPoints(); pts.SetData(numpy_to_vtk(np.asarray(m.vertices, float), deep=True))
    cells = np.hstack([np.full((len(m.faces), 1), 3), m.faces]).astype(np.int64).ravel()
    ca = vtk.vtkCellArray(); ca.SetCells(len(m.faces), numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(ca)
    src = pd
    if clip is not None:
        plane = vtk.vtkPlane(); plane.SetOrigin(*clip[0]); plane.SetNormal(*clip[1])
        c = vtk.vtkClipPolyData(); c.SetInputData(pd); c.SetClipFunction(plane); c.Update(); src = c.GetOutput()
    nf = vtk.vtkPolyDataNormals(); nf.SetInputData(src); nf.SetFeatureAngle(35); nf.Update()
    mp = vtk.vtkPolyDataMapper(); mp.SetInputData(nf.GetOutput())
    if front:                                     # the ears share faces with the cap: draw them just in front
        mp.SetResolveCoincidentTopologyToPolygonOffset(); mp.SetRelativeCoincidentTopologyPolygonOffsetParameters(-4, -4)
    a = vtk.vtkActor(); a.SetMapper(mp)
    r, g, b = matplotlib.colors.to_rgb(color)
    a.GetProperty().SetColor(r, g, b); a.GetProperty().SetOpacity(opacity)
    a.GetProperty().SetSpecular(0.15); a.GetProperty().SetAmbient(0.25)
    return a


def render(items, cam_pos, focal, up, labels, path, title, parallel=None):
    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    for m, c, o, clip in items:
        ren.AddActor(actor(m, c, o, clip, front=(c == COL['ears'])))
    cam = ren.GetActiveCamera(); cam.SetPosition(*cam_pos); cam.SetFocalPoint(*focal); cam.SetViewUp(*up)
    if parallel:
        cam.ParallelProjectionOn(); cam.SetParallelScale(parallel)
    else:
        cam.SetViewAngle(28)
    ren.ResetCameraClippingRange()
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H); rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.Update()
    img = w2i.GetOutput(); nx, ny, _ = img.GetDimensions()
    arr = np.frombuffer(img.GetPointData().GetScalars(), np.uint8).reshape(ny, nx, -1)[::-1, :, :3]
    coord = vtk.vtkCoordinate(); coord.SetCoordinateSystemToWorld()
    fig = plt.figure(figsize=(W / 100, H / 100 + 0.6), dpi=100)
    ax = fig.add_axes([0, 0, 1, H / (H + 60)]); ax.imshow(arr); ax.axis('off')
    for p, text, (dx, dy), col in labels:
        coord.SetValue(*p); x, y = coord.GetComputedDoubleDisplayValue(ren); y = H - y
        ax.annotate(text, xy=(x, y), xytext=(x + dx, y + dy), fontsize=13, color=col,
                    bbox=dict(boxstyle='round,pad=0.25', fc='white', ec=col, alpha=0.92),
                    arrowprops=dict(arrowstyle='->', color=col, lw=1.4))
    fig.suptitle(title, fontsize=16, y=0.995)
    fig.savefig(path, dpi=100); plt.close(fig)


def sections(cap, ears, P, gp, path):
    zt = B.ZTOP
    layers = [('head_bottom', gp['head_bottom'], '#d9d9d9'), ('jaw_frame', gp['jaw_frame'], '#e6b0aa'),
              ('jaw_support', gp['jaw_support'], '#b03a2e'), ('motor15', gp['motor15'], '#7b241c'),
              ('face_panel', gp['face_panel'], '#d9d9d9'), ('camera', gp['camera_board'], COL['cam']),
              ('cap', cap, '#f4f2ec'), ('ears', ears, COL['ears']), ('pcb', P['a7z_pcb'], COL['pcb']),
              ('hs', P['heatsink_6530b'], COL['hs']), ('plug', P['dupont_plugs'], COL['plug']),
              ('sd', P['a7z_microsd_card'], COL['sd']), ('csi', P['a7z_csi_connector'], COL['csi']),
              ('ribbon', P['camera_ribbon_b2b'], COL['ribbon']), ('screw', P['ear_screws_m2x8'], COL['screw']),
              ('kit', P['kit_screw_head'], COL['screw']), ('coax', P['antenna_coax_b2b'], COL['coax'])]
    fig, axs = plt.subplots(1, 2, figsize=(18, 8.5))
    for ax, y0, title in ((axs[0], 29.0, '剖面 y = +29（机器人左边两个孔）'), (axs[1], -29.0, '剖面 y = −29（机器人右边两个孔）')):
        for name, m, c in layers:
            sec = m.section(plane_origin=[0, y0, 0], plane_normal=[0, 1, 0])
            if sec is None:
                continue
            p2, T4 = sec.to_2D(to_2D=np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, -y0], [0, 0, 0, 1]], float))
            for poly in p2.polygons_full:
                xs, zs = poly.exterior.xy
                ax.fill(xs, zs, fc=c, ec='#333', lw=0.5, alpha=0.95 if name != 'jaw_frame' else 0.6)
                for hole in poly.interiors:
                    hx, hz = hole.xy; ax.fill(hx, hz, fc='white', ec='#333', lw=0.4)
        ax.set_xlim(30, 92); ax.set_ylim(106, 160); ax.set_aspect('equal'); ax.grid(alpha=0.15)
        ax.set_title(title, fontsize=14); ax.set_xlabel('x（mm，向右 = 机器人前方）'); ax.set_ylabel('z（mm，向上）')
    A0, A1 = axs
    kw = dict(fontsize=11, arrowprops=dict(arrowstyle='->', lw=1.2))
    A0.annotate('上耳朵（红）一直长到头顶', xy=(72.5, zt - 1), xytext=(76, 156), color=COL['ears'], **kw)
    A0.annotate('M2×8：从前面穿过耳朵、板子，\n拧进 6530B 自带螺纹', xy=(74, zt - 3.5), xytext=(78, 146), **kw)
    A0.annotate('A7Z 竖着（绿），\n元件面朝后', xy=(68.8, 128), xytext=(80, 117), color=COL['pcb'], **kw)
    A0.annotate('6530B', xy=(61, 130), xytext=(44, 152), color=COL['hs'], **kw)
    A0.annotate('左下角 Radxa CM2×4×4\n（没有耳朵，上面是摄像头插座）', xy=(70.6, zt - 26.5), xytext=(74, 108.5), **kw)
    A0.annotate('下巴舵机座', xy=(48, 122), xytext=(32, 112), color='#b03a2e', **kw)
    A1.annotate('右下耳朵 + 45° 筋（红）', xy=(72.8, zt - 25), xytext=(76, 109), color=COL['ears'], **kw)
    A1.annotate('microSD', xy=(70.4, zt - 15), xytext=(78, 132), color=COL['sd'], **kw)
    fig.suptitle('剖面（填色）：耳朵在板子前面，6530B 在后面；离头顶壳最近 0.63 mm，离下壳 1.72 mm', fontsize=15)
    fig.tight_layout(); fig.savefig(path, dpi=100); plt.close(fig)


def main():
    ld = lambda f: trimesh.load(HERE / f)
    cap, ears = ld('head_cap_b2b-world.stl'), ld('ears_only.stl')
    P = {f.stem: trimesh.load(f) for f in (HERE / 'parts').glob('*.stl')}
    gp = B.guide_parts()
    chk = json.loads((HERE / 'checks.json').read_text())
    board = [(P['a7z_pcb'], COL['pcb'], 1, None), (P['heatsink_6530b'], COL['hs'], 1, None),
             (P['dupont_plugs'], COL['plug'], 0.55, None), (P['antenna_coax_b2b'], COL['coax'], 1, None),
             (P['camera_ribbon_b2b'], COL['ribbon'], 1, None), (P['ear_screws_m2x8'], COL['screw'], 1, None),
             (P['kit_screw_head'], COL['screw'], 1, None), (P['a7z_microsd_card'], COL['sd'], 1, None),
             (P['a7z_csi_connector'], COL['csi'], 1, None), (P['a7z_microsd_socket'], COL['sd'], 1, None),
             (P['fan_lead_loop'], COL['coax'], 0.35, None)]
    zt = B.ZTOP
    # 1. Looking into the cap from below and in front (face, camera and head bottom off), cap opaque.
    items = [(cap, COL['cap'], 1, None), (ears, COL['ears'], 1, None)] + board
    labels = [((73.6, 29, zt - 1.5), '左上耳朵：一直长到头顶，\n打印不用支撑', (-330, -120), COL['ears']),
              ((73.6, -29, zt - 1.5), '右上耳朵', (60, -120), COL['ears']),
              ((73.6, -36, zt - 22), '右下耳朵 + 45° 加强筋\n（贴着侧壁那根圆柱）', (90, 40), COL['ears']),
              ((70.4, 29, zt - 26.5), '左下角：Radxa 自带 CM2×4×4，不用耳朵\n（正上方是摄像头插座）', (60, 110), COL['screw']),
              ((70.6, 30, zt - 15), '摄像头插座 + 排线', (-360, -40), '#d35400'),
              ((70.4, -27, zt - 16), 'microSD', (120, 0), COL['sd']),
              ((60, -20, zt - 30), '6530B（风扇朝后）', (-330, 90), COL['hs'])]
    render(items, (190, -120, 70), (62, 0, 128), (0, 0, 1), labels, OUT / 'b2b-1-inside.png',
           '头盖里面（从前下方看，面板/摄像头/下壳拿掉）：3 个耳朵 + 1 颗自带螺丝固定板子和 6530B')
    # 2. Filled sections through the screw holes at y = +29 (left) and y = -29 (right), seen from the robot's left.
    sections(cap, ears, P, gp, OUT / 'b2b-2-section.png')
    # 3. From the front with the face and camera off: what the screwdriver sees.
    items = [(cap, COL['cap'], 1, ((80.0, 0, 0), (-1, 0, 0))), (ears, COL['ears'], 1, None)] + board
    labels = [((75.2, 29, zt - 3.5), 'M2×8', (-150, -90), COL['screw']), ((75.2, -29, zt - 3.5), 'M2×8', (90, -90), COL['screw']),
              ((75.2, -29, zt - 26.5), 'M2×8', (90, 60), COL['screw']),
              ((71.2, 29, zt - 26.5), 'CM2×4×4（先装）', (-300, 60), COL['screw'])]
    render(items, (260, 0, 130), (60, 0, 128), (0, 0, 1), labels, OUT / 'b2b-3-front.png',
           '从前面看（面板、摄像头拿掉）：三颗 M2×8 从前面拧，螺丝刀直线可达', parallel=42)
    ducts(cap, P, gp, chk)
    print('renders', sorted(p.name for p in OUT.glob('*.png')), 'checks', chk['walls']['shellBehindCutMin_mm'])


def ducts(cap, P, gp, chk):
    """Air duct pictures: inside from behind, the right cheek outside, and a filled section through the fan."""
    ins, walls = trimesh.load(HERE / 'shroud_insert-world.stl'), trimesh.load(HERE / 'duct_walls_only.stl')
    du = chk['ducts']
    board = [(P['a7z_pcb'], COL['pcb'], 1, None), (P['heatsink_6530b'], COL['hs'], 1, None),
             (P['dupont_plugs'], COL['plug'], 0.6, None), (P['fan_lead_loop'], COL['coax'], 0.5, None)]
    # 4. inside from behind and below, the rear of the cap cut away at x 44
    items = [(cap, COL['cap'], 1, ((44.0, 0, 0), (1, 0, 0))), (walls, '#8e44ad', 1, None), (ins, '#e74c3c', 1, None),
             (P['fan_inlet_zone'], '#90caf9', 0.55, None)] + board
    labels = [((48.2, -18, 125), '导风插片（单独打印，红）\n接好线后从下往上推进卡槽', (-420, 40), '#e74c3c'),
              ((48.2, -36, 137), '右脸颊两道卡槽', (-380, -60), '#8e44ad'),
              ((55, 3.0, 125), '插片上的挡条：\n热风不回风扇口', (150, 170), '#e74c3c'),
              ((55, 15, 125), '风扇进风口（蓝）', (-250, 150), '#1565c0'),
              ((56.4, 39, 125), '左挡板', (160, -40), '#8e44ad'),
              ((56.4, 18, 149), '插头上方挡板', (160, -110), '#8e44ad')]
    render(items, (-45, -55, 95), (55, -5, 132), (0, 0, 1), labels, OUT / 'b2b-4-duct-inside.png',
           '风道（从后下方看，头盖后半截切掉）：插片把散热片吹出的热风拦住，引到右脸颊出风窗')
    # 5. right cheek from outside
    dark = trimesh.creation.box(bounds=[[12.0, -25.0, 112.0], [75.0, 25.0, 140.0]])     # behind the slots, so they show
    items = [(cap, COL['cap'], 1, None), (dark, '#263238', 1, None)]
    labels = [((62.5, -42, 126), f"出风窗 4 条 × 1.6 mm（每侧 {du['slotOpen_mm2']['exhaust']:.0f} mm²）", (40, 150), '#e65100'),
              ((42.0, -41, 125), f"进风窗 4 条（每侧 {du['slotOpen_mm2']['intake']:.0f} mm²）", (-330, 150), '#0277bd')]
    render(items, (40, -260, 128), (40, 0, 132), (0, 0, 1), labels, OUT / 'b2b-5-cheek.png',
           '右脸颊外面（左边对称）：前面一组出风，后面一组进风，铜箔区域都没开孔', parallel=48)
    # 6. filled section through the fan at z 122 with the air path
    fig, ax = plt.subplots(figsize=(12, 10))
    layers = [('jaw_support', gp['jaw_support'], '#cfcfcf'), ('motor15', gp['motor15'], '#bdbdbd'),
              ('clip_head', gp['clip_head'], '#d7ccc8'), ('camera', gp['camera_board'], COL['cam']),
              ('cap', cap, '#f4f2ec'), ('walls', walls, '#8e44ad'), ('insert', ins, '#e74c3c'),
              ('fan', P['fan_inlet_zone'], '#90caf9'), ('hs', P['heatsink_6530b'], COL['hs']), ('pcb', P['a7z_pcb'], COL['pcb'])]
    z0 = 122.0
    for name, m, c in layers:
        sec = m.section(plane_origin=[0, 0, z0], plane_normal=[0, 0, 1])
        if sec is None:
            continue
        p2, _ = sec.to_2D(to_2D=np.eye(4))
        for poly in p2.polygons_full:
            xs, ys = poly.exterior.xy
            ax.fill(xs, ys, fc=c, ec='#333', lw=0.5, alpha=0.95)
            for hole in poly.interiors:
                hx, hy = hole.xy; ax.fill(hx, hy, fc='white', ec='#333', lw=0.4)
    from matplotlib.patches import FancyArrowPatch
    for p0, p1, c in [((41, 49), (41, 34), '#0277bd'), ((41, -49), (41, -34), '#0277bd'), ((42, 12), (52, 12), '#0277bd'),
                      ((52.3, -2), (52.3, -30), '#c62828'), ((53, -33), (62, -36), '#c62828'), ((62, -36), (62, -50), '#e65100'),
                      ((62, 36), (62, 50), '#e65100')]:
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle='-|>', mutation_scale=18, lw=2.2, color=c))
    ax.text(30, 14, '冷风（脖子 + 进风窗）', color='#0277bd', fontsize=11)
    ax.text(51, -16, '热风', color='#c62828', fontsize=11, ha='right')
    ax.set_xlim(14, 96); ax.set_ylim(-55, 55); ax.set_aspect('equal'); ax.grid(alpha=0.2)
    ax.set_xlabel('x（向前）mm'); ax.set_ylabel('y（向左）mm')
    ax.set_title(f'剖面 z = {z0:.0f}（穿过风扇）：红 = 导风插片，紫 = 头盖上的挡板，蓝 = 风扇进风口', fontsize=13)
    fig.tight_layout(); fig.savefig(OUT / 'b2b-6-duct-section.png', dpi=110); plt.close(fig)


if __name__ == '__main__':
    main()
