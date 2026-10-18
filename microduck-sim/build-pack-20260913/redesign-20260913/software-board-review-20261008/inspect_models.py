#!/usr/bin/env python3
"""Inspect frozen actors and run one CPU smoke input; no robot imports/devices."""
from pathlib import Path
import hashlib,json,platform
import onnx,onnxruntime as ort,numpy as np
D=Path(__file__).resolve().parent
models=D.parents[1]/'phase1/runtime/bundle/community/src/agents'
rows=[]
for name in ('walk61.onnx','stand61.onnx'):
    p=models/name;m=onnx.load(p);s=ort.InferenceSession(str(p),providers=['CPUExecutionProvider'])
    output=s.run(None,{s.get_inputs()[0].name:np.zeros((1,61),np.float32)})[0]
    rows.append({'model':str(p.relative_to(D.parents[3])),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'input':{'shape':s.get_inputs()[0].shape,'type':s.get_inputs()[0].type},'output':{'shape':s.get_outputs()[0].shape,'type':s.get_outputs()[0].type},'initializerTypes':{onnx.TensorProto.DataType.Name(t):sum(v.data_type==t for v in m.graph.initializer) for t in set(v.data_type for v in m.graph.initializer)},'operators':sorted(set(n.op_type for n in m.graph.node)),'zeroInputOutputFinite':bool(np.all(np.isfinite(output))),'zeroInputOnlyNotGaitTrial':True})
assert all(r['initializerTypes']=={'FLOAT':10} and r['input']['shape']==[1,61] and r['output']['shape']==[1,14] and r['zeroInputOutputFinite'] for r in rows)
r={'host':platform.platform(),'onnxruntime':ort.__version__,'modelReadAndCPUInferencePassed':True,'rows':rows,'hardwareOpened':False}
(D/'model-inspection.json').write_text(json.dumps(r,indent=2)+'\n');print('FROZEN_MODEL_CPU_SMOKE_PASS')
