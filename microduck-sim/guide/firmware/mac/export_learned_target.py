#!/usr/bin/env python3
"""Export the open-vocabulary detector that learned_target.py runs, with the text prompts baked in as classes.

Runs on the Mac mini only (torch + ultralytics; the robot and the MacBook venvs have neither):

    uv venv ~/.venvs/duck-onnx --python 3.12
    uv pip install --python ~/.venvs/duck-onnx/bin/python torch torchvision ultralytics onnx onnxruntime onnxslim \
        opencv-python-headless numpy "git+https://github.com/ultralytics/CLIP.git"
    ~/.venvs/duck-onnx/bin/python export_learned_target.py --out learned_target.onnx
    ~/.venvs/duck-onnx/bin/python export_learned_target.py --weights yolov8s-worldv2.pt --size 288,480 --out x.onnx

Default: YOLOE-11s (yoloe-11s-seg.pt) at 384x640, the best of the four models (YOLO-World s and m, YOLOE-11s and v8s) compared on the
robot frames on 2026-11-12. The segmentation branch is cut off the graph (learned_target.py reads boxes only).

No training: the weights are the published ones (ultralytics downloads them and the text tower on first use: CLIP for YOLO-World, the
572 MB MobileCLIP for YOLOE);
the text tower runs once here, and the ONNX file holds only the image network plus one embedding per prompt. The
prompts end up in the ONNX metadata ("names"), where learned_target.py reads them. A new object name means a new
export; the list below is the bank the pickup code can choose from without one.

Licence: Ultralytics code and weights are AGPL-3.0 (ultralytics/__init__.py line 1, package METADATA).
"""
import argparse
import os
import shutil

PROMPTS = ["small orange ball", "orange ball", "ball", "orange toy", "orange object", "pink ball", "red ball",
           "sports ball", "ping pong ball", "bead", "orange"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", default="yoloe-11s-seg.pt")
    ap.add_argument("--size", default="384,640", help="H,W of the network input, multiples of 32 (640x360 frames "
                                                      "letterbox into 384x640 without resizing)")
    ap.add_argument("--prompts", default="|".join(PROMPTS), help="'|' separated")
    ap.add_argument("--out", default="learned_target.onnx")
    args = ap.parse_args()
    from ultralytics import YOLOE, YOLOWorld
    prompts = args.prompts.split("|")
    hw = [int(v) for v in args.size.split(",")]
    if "yoloe" in os.path.basename(args.weights):
        m = YOLOE(args.weights)
        m.set_classes(prompts, m.get_text_pe(prompts))
    else:
        m = YOLOWorld(args.weights)
        m.set_classes(prompts)
    f = m.export(format="onnx", imgsz=hw, opset=17, simplify=True, dynamic=False, nms=False)
    import onnx
    g = onnx.load(f)
    if len(g.graph.output) > 1:   # YOLOE-seg: output1 is the mask prototypes; drop that branch, keep the metadata
        first = g.graph.output[0].name
        tmp = f + ".boxes.onnx"
        onnx.utils.extract_model(f, tmp, [g.graph.input[0].name], [first])
        cut = onnx.load(tmp)
        del cut.metadata_props[:]
        cut.metadata_props.extend(g.metadata_props)
        onnx.save(cut, tmp)
        os.replace(tmp, f)
    shutil.move(f, args.out)
    print(f"wrote {args.out} ({os.path.getsize(args.out) / 1e6:.1f} MB), input {hw[0]}x{hw[1]}, prompts {prompts}")


if __name__ == "__main__":
    main()
