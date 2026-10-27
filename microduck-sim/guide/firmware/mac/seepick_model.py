"""Install a trained seeing-pick policy as the runtime's seepick61.onnx (walk_brain.py mode "seepick").

The microduck_rl export lists the passive jaw joint (passive_mouth) in the joint_names, default_joint_pos,
joint_stiffness and joint_damping metadata, although the network itself is the 61-input, 14-action contract (the
mouth is scripted on the phase, not a policy output). walk_brain asserts the 14-joint metadata of the walk policy, so
this drops the passive entries, checks the network shape and the default pose against walk61, and writes the model
with its source and sha256 in the metadata.

  python seepick_model.py <candidate.onnx>          e.g. microduck_rl-grasp/cmu/grasp/policies/sp-b-1027_2000.onnx
"""
import argparse
import hashlib
import os
import sys

import onnx

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "..", "..", "..", "hardware-design-20260912", "whole-robot-20260912", "runtime-overlay",
                      "models")
PER_JOINT = ("joint_names", "default_joint_pos", "joint_stiffness", "joint_damping")


def convert(src, dst, walk=os.path.join(MODELS, "walk61.onnx")):
    m = onnx.load(src)
    meta = {p.key: p.value for p in m.metadata_props}
    names = meta["joint_names"].split(",")
    keep = [k for k, n in enumerate(names) if not n.startswith("passive_")]
    for key in PER_JOINT:
        if key in meta:
            vals = meta[key].split(",")
            assert len(vals) == len(names), key
            meta[key] = ",".join(vals[k] for k in keep)
    inp = [d.dim_value for d in m.graph.input[0].type.tensor_type.shape.dim]
    out = [d.dim_value for d in m.graph.output[0].type.tensor_type.shape.dim]
    if inp[-1] != 61 or out[-1] != 14 or len(keep) != 14:
        sys.exit(f"{src}: input {inp}, output {out}, {len(keep)} servo joints; the runtime needs 61 -> 14")
    wmeta = {p.key: p.value for p in onnx.load(walk).metadata_props}
    for key in ("joint_names", "default_joint_pos", "observation_names"):
        if meta[key] != wmeta[key]:
            sys.exit(f"{key} differs from walk61:\n  {meta[key]}\n  {wmeta[key]}")
    meta["source"] = os.path.basename(src)
    meta["source_sha256"] = hashlib.sha256(open(src, "rb").read()).hexdigest()
    del m.metadata_props[:]
    for k, v in meta.items():
        m.metadata_props.add(key=k, value=v)
    onnx.save(m, dst)
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("candidate")
    ap.add_argument("--out", default=os.path.join(MODELS, "seepick61.onnx"))
    a = ap.parse_args()
    meta = convert(a.candidate, a.out)
    sha = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
    print(f"{a.out}: from {meta['source']} (sha256 {meta['source_sha256'][:12]}), installed sha256 {sha[:12]}")


if __name__ == "__main__":
    main()
