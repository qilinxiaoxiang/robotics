"""Render an already-recorded trajectory; rendering does not change physics results."""
from pathlib import Path
import argparse,json
import imageio.v2 as imageio
import mujoco,numpy as np
from evaluate import load
ap=argparse.ArgumentParser();ap.add_argument('trace',type=Path);ap.add_argument('--seconds',type=float,default=12);args=ap.parse_args()
trace=json.loads(args.trace.read_text());m,d,*_=load(trace['config'])
renderer=mujoco.Renderer(m,height=720,width=960)
out=args.trace.parent/'MicroDuck-full-assembly-walking.mp4'
with imageio.get_writer(out,fps=25,codec='libx264',quality=7) as writer:
    for index,row in enumerate(trace['rows']):
        if row['time']>args.seconds:break
        if index%2:continue
        d.qpos[:]=row['qpos'];mujoco.mj_forward(m,d)
        cam=mujoco.MjvCamera();cam.lookat=d.xpos[m.body('trunk_base').id].copy()+[0,0,.055]
        cam.distance=.60;cam.azimuth=135;cam.elevation=-10
        renderer.update_scene(d,camera=cam);frame=renderer.render();writer.append_data(frame)
        if abs(row['time']-6.02)<.005:
            imageio.imwrite(out.with_suffix('.png'),frame)
            for g in range(m.ngeom):
                if m.geom(g).name in ['new_cad_visual_5']:m.geom_rgba[g,3]=.24
            renderer.update_scene(d,camera=cam);imageio.imwrite(out.with_name('MicroDuck-full-assembly-inside.png'),renderer.render())
            for g in range(m.ngeom):
                if m.geom(g).name in ['new_cad_visual_5']:m.geom_rgba[g,3]=1
renderer.close();print(out)
