"""Print poses of the three V1.17 A7Z head parts, written to pose-sources-a7z.json (read by make_manifest.py next to the V1.16
pose-sources.json, which is copied unchanged). Read-only on every source.

    /tmp/microduck-cad-venv/bin/python scripts/pose_sources_a7z.py

- head_cap_a7z (world frame): the V1.9 cap pose, release-V1.9/manifest-V1.9.json head_cap_v19.sourceToPrint (roof on the bed);
  the A7Z cap is the V1.9 cap with material removed inside only, so the pose, contact strip and tip angle carry over.
- clip_cap_a7z (world frame): the V1.9 cap clip pose, release-V1.9/manifest-V1.9.json clip_cap_v19.sourceToPrint (tab seat face
  on the bed, screw hole vertical).
- face_panel_a7z (face-a7z/face_panel_a7z.stl, robot frame, byte-identical to world/face_panel.stl): the V1.8 face transform,
  release-V1.8/manifest-V1.8.json face_panel.sourceToPrint (front on the bed, bosses up). The registration check maps it through
  that transform plus the drop to the bed and compares the sorted vertices with face-a7z/face_panel_a7z-print.stl.
"""
import json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; PRINT = HERE.parents[1]
V19 = {p['key']: p for p in json.loads((PRINT / 'release-V1.9/manifest-V1.9.json').read_text())['parts']}
V18 = {p['key']: p for p in json.loads((PRINT / 'release-V1.8/manifest-V1.8.json').read_text())['parts']}


def main():
    pr = trimesh.load(PRINT / 'face-a7z/face_panel_a7z-print.stl', force='mesh'); tw = trimesh.load(PRINT / 'face-a7z/face_panel_a7z.stl', force='mesh')
    T8 = np.array(V18['face_panel']['sourceToPrint'], float); tw.apply_transform(T8); tw.apply_translation([0, 0, -tw.bounds[0, 2]])
    a = np.array(sorted(map(tuple, np.asarray(pr.vertices)))); b = np.array(sorted(map(tuple, np.asarray(tw.vertices))))
    dev = float(np.abs(a - b).max()) if a.shape == b.shape else None
    out = {'_doc': __doc__, 'poses': {
        'head_cap_a7z': {'V1.9 pose': dict(sourceToPrint=V19['head_cap_v19']['sourceToPrint'], **{'from': 'release-V1.9/manifest-V1.9.json head_cap_v19'},
                                           poseOrigin=V19['head_cap_v19']['poseOrigin'])},
        'clip_cap_a7z': {'V1.9 pose': dict(sourceToPrint=V19['clip_cap_v19']['sourceToPrint'], **{'from': 'release-V1.9/manifest-V1.9.json clip_cap_v19'},
                                           poseOrigin=V19['clip_cap_v19']['poseOrigin'])},
        'face_panel_a7z': {'V1.8 pose': dict(sourceToPrint=V18['face_panel']['sourceToPrint'], **{'from': 'release-V1.8/manifest-V1.8.json face_panel'},
                                             note='robot-frame face_panel_a7z.stl (= world/face_panel.stl) under the V1.8 face transform; checked against face_panel_a7z-print.stl',
                                             registeredTo=str(PRINT / 'face-a7z/face_panel_a7z-print.stl'), maxVertexDeviationMm=dev)}}}
    assert dev is not None and dev < 1e-3, dev
    (HERE / 'pose-sources-a7z.json').write_text(json.dumps(out, indent=1)); print('face registration max deviation', dev)


if __name__ == '__main__':
    main()
