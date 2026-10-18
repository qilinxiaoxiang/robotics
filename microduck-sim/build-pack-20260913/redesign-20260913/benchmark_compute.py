"""Hardware-free latency check of the exact installed walking and jaw actors."""
from pathlib import Path
import hashlib
import json
import platform
import time
import numpy as np
import onnxruntime as ort

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[1]
RUNTIME = HERE.parent / "phase1/runtime/bundle/community/src/agents"

def measure(fn, iterations=5000):
    for _ in range(200):
        fn()
    samples=[]
    for _ in range(iterations):
        start=time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns()-start)/1e6)
    return {"samples": iterations, "median_ms": float(np.median(samples)),
            "p99_ms": float(np.percentile(samples,99)), "max_ms": max(samples)}

result={"platform":platform.platform(), "machine":platform.machine(),
        "python":platform.python_version(), "numpy":np.__version__,
        "onnxruntime":ort.__version__, "hardware_opened":False,
        "scope":"Actor-only inference with synthetic inputs; excludes camera, USB, IMU and scheduling.",
        "models":{}}
options=ort.SessionOptions()
options.intra_op_num_threads=1
options.inter_op_num_threads=1
for name in ("walk61", "stand61"):
    path=RUNTIME/(name+".onnx")
    session=ort.InferenceSession(str(path),sess_options=options,providers=["CPUExecutionProvider"])
    feed={session.get_inputs()[0].name:np.zeros((1,61),dtype=np.float32)}
    result["models"][name]={"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                             "input_shape":[1,61], "output_shape":[1,14],
                             **measure(lambda:session.run(None,feed))}
path=SIM/"microduck-simulator/app/public/policies/jaw-ppo.json"
actor=json.loads(path.read_text())
layers=[(np.asarray(layer["weight"],dtype=np.float32),
         np.asarray(layer["bias"],dtype=np.float32)) for layer in actor["layers"]]
def jaw():
    x=np.zeros(actor["observationSize"],dtype=np.float32)
    for i,(weight,bias) in enumerate(layers):
        x=weight@x+bias
        if i<len(layers)-1:x=np.tanh(x)
    return int(np.argmax(x))
result["models"]["jaw_ppo"]={"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                                "input_shape":[20], "output_shape":[2], **measure(jaw)}
result["actor_compute_fits_20ms_period"]=all(v["p99_ms"]<20 for v in result["models"].values())
(HERE/"compute-benchmark.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
