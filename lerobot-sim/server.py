"""A local manual controller for the official SO-101 MuJoCo model.

P1: aligned observation/action demonstrations; P0: measured replay error.
This is a project UI, not an official LeRobot GUI or a trained policy.
"""
import io
import json
import logging
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import mujoco
import numpy as np
from flask import Flask, Response, abort, jsonify, request, send_from_directory
from PIL import Image
from werkzeug.serving import make_server
from cartesian import move_tool

ROOT = Path(__file__).resolve().parent
PORT = 8766
FPS = 10
app = Flask(__name__, static_folder=str(ROOT / "static"))
logging.getLogger("werkzeug").setLevel(logging.ERROR)
commands = queue.Queue(maxsize=100)
state = {"ready": False}
jpeg = b""
lock = threading.Lock()

@app.before_request
def local_only():
    if request.host not in {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}:
        abort(403)
    if request.method == "POST":
        origin = request.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}:
            abort(403)
        if not request.is_json:
            abort(415)

@app.get("/")
def index():
    return send_from_directory(ROOT / "static", "index.html")

@app.get("/api/state")
def get_state():
    with lock:
        return jsonify(state)

@app.get("/frame.jpg")
def frame():
    with lock:
        return Response(jpeg, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})

@app.post("/api/command")
def command():
    value = request.get_json()
    if not isinstance(value, dict) or value.get("op") not in {
        "control", "move", "grip", "reset", "record", "save", "replay", "camera", "shutdown"
    }:
        abort(400)
    try:
        if value["op"] == "control":
            value["index"] = int(value["index"])
            value["value"] = float(value["value"])
            if not 0 <= value["index"] < 6 or not np.isfinite(value["value"]):
                abort(400)
        if value["op"] == "camera" and value.get("view") not in {"front", "side", "top"}:
            abort(400)
        if value["op"] == "move":
            delta = np.asarray(value.get("delta"), dtype=float)
            if delta.shape != (3,) or not np.isfinite(delta).all() or np.linalg.norm(delta) > .020001:
                abort(400)
            value["delta"] = delta.tolist()
        if value["op"] == "grip" and value.get("open") not in (True, False):
            abort(400)
        commands.put_nowait(value)
    except (KeyError, ValueError, TypeError):
        abort(400)
    except queue.Full:
        abort(429)
    return jsonify(queued=True)

def main():
    global jpeg, state
    model = mujoco.MjModel.from_xml_path(str(ROOT / "models/robotstudio_so101/scene_box.xml"))
    data = mujoco.MjData(model)
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [0.12, 0, 0.14]
    camera.distance, camera.azimuth, camera.elevation = 0.85, 130, -25
    renderer = mujoco.Renderer(model, height=480, width=640)
    names = [model.actuator(i).name for i in range(6)]
    home = np.array([0, -0.35, 0.65, 0.8, 0, 0.8])
    recording = False
    samples = []
    initial = None
    saved_episodes = sorted((ROOT / "outputs").glob("demo-*.npz"))
    last_path = saved_episodes[-1] if saved_episodes else None
    playback = None
    play_index = 0
    max_error = 0.0
    exporter = None
    export_log = None
    status = "用方向按钮移动夹爪，或用 W / A / S / D、R / F 键操作。"

    def reset():
        mujoco.mj_resetData(model, data)
        data.qpos[:6] = home
        data.ctrl[:] = home
        # Start the free object on the table. No pickup keyframe or attachment.
        data.qpos[6:13] = [0.22, 0.02, 0.03, 1, 0, 0, 0]
        mujoco.mj_forward(model, data)

    reset()
    http = make_server("127.0.0.1", PORT, app, threaded=True)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    print(f"SO-101 playground: http://127.0.0.1:{PORT}", flush=True)
    running = True
    try:
        while running:
            tick = time.monotonic()
            if exporter is not None and exporter.poll() is not None:
                status = ("演示已保存为 LeRobot 数据集；仍需收集成功演示并训练。"
                          if exporter.returncode == 0 else "原始演示已保存；数据集转换失败，详见 outputs 中的日志。")
                export_log.close()
                exporter = None
            while not commands.empty():
                cmd = commands.get_nowait()
                op = cmd["op"]
                if op == "shutdown":
                    running = False
                elif op == "camera":
                    camera.azimuth, camera.elevation = {
                        "front": (130, -25), "side": (90, -20), "top": (90, -85)
                    }[cmd["view"]]
                elif op == "control" and playback is None:
                    i = cmd["index"]
                    data.ctrl[i] = np.clip(cmd["value"], *model.actuator_ctrlrange[i])
                elif op == "move" and playback is None:
                    new_controls, status = move_tool(model, data.ctrl, cmd["delta"])
                    if new_controls is not None:
                        data.ctrl[:] = new_controls
                elif op == "grip" and playback is None:
                    data.ctrl[5] = 1.2 if cmd["open"] else 0.0
                    status = "夹爪张开。" if cmd["open"] else "夹爪闭合；夹住物体需要两侧接触。"
                elif op == "reset" and not recording:
                    playback = None
                    reset()
                    status = "已重置场景。"
                elif op == "record" and not recording and exporter is None and playback is None:
                    recording, samples = True, []
                    initial = (data.qpos.copy(), data.qvel.copy(), data.ctrl.copy())
                    status = "正在记录手动演示，最长 30 秒。"
                elif op == "save" and recording:
                    recording = False
                elif op == "replay" and last_path is not None and not recording and exporter is None:
                    with np.load(last_path, allow_pickle=False) as saved:
                        playback = {key: saved[key].copy() for key in saved.files}
                    mujoco.mj_resetData(model, data)
                    data.qpos[:] = playback["initial_qpos"]
                    data.qvel[:] = playback["initial_qvel"]
                    data.ctrl[:] = playback["initial_ctrl"]
                    mujoco.mj_forward(model, data)
                    play_index, max_error = 0, 0.0
                    status = "正在重放已记录的动作；这不是模型自主决策。"
            if playback is not None:
                data.ctrl[:] = playback["action"][play_index]
                max_error = max(max_error, float(np.max(np.abs(data.qpos[:6] - playback["state"][play_index]))))
            mujoco.mj_forward(model, data)
            renderer.update_scene(data, camera=camera)
            pixels = renderer.render()
            if recording:
                samples.append((data.qpos[:6].astype(np.float32).copy(), data.ctrl.astype(np.float32).copy(), pixels[::2, ::2].copy()))
                if len(samples) >= 30 * FPS:
                    recording = False
            if not recording and samples:
                output = ROOT / "outputs"
                output.mkdir(exist_ok=True)
                last_path = output / ("demo-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".npz")
                np.savez_compressed(last_path, state=np.stack([s[0] for s in samples]),
                    action=np.stack([s[1] for s in samples]), images=np.stack([s[2] for s in samples]),
                    initial_qpos=initial[0], initial_qvel=initial[1], initial_ctrl=initial[2],
                    fps=FPS, task="Manual SO-101 movement demonstration; success not labeled")
                samples = []
                export_log = last_path.with_suffix(".log").open("w")
                exporter = subprocess.Popen([sys.executable, str(ROOT / "export_dataset.py"), str(last_path)],
                    stdout=export_log, stderr=subprocess.STDOUT, cwd=ROOT)
                status = "原始演示已保存，正在转换为本地 LeRobot 数据集。"
            buffer = io.BytesIO()
            Image.fromarray(pixels).save(buffer, format="JPEG", quality=85)
            with lock:
                jpeg = buffer.getvalue()
                state = {"ready": True, "names": names, "ranges": model.actuator_ctrlrange.tolist(),
                    "qpos": data.qpos[:6].tolist(), "ctrl": data.ctrl.tolist(), "time": round(data.time, 1),
                    "recording": recording, "frames": len(samples), "exporting": exporter is not None,
                    "playing": playback is not None, "replay_error_rad": max_error,
                    "saved": last_path.name if last_path else None, "status": status,
                    "gripper_xyz": data.site("gripperframe").xpos.tolist(),
                    "box_xyz": data.body("box").xpos.tolist(), "contacts": int(data.ncon)}
            mujoco.mj_step(model, data, nstep=round(1 / FPS / model.opt.timestep))
            if playback is not None:
                play_index += 1
                if play_index >= len(playback["action"]):
                    playback = None
                    status = f"动作重放完成。最大关节偏差 {max_error:.5f} 弧度；这不等于抓取成功。"
            time.sleep(max(0, 1 / FPS - (time.monotonic() - tick)))
    except KeyboardInterrupt:
        pass
    finally:
        if exporter is not None:
            exporter.wait(timeout=60)
            export_log.close()
        http.shutdown()
        renderer.close()

if __name__ == "__main__":
    main()
