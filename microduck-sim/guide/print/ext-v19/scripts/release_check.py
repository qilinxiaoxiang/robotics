#!/usr/bin/env python3
"""Mesh integrity of every ext-v19 release solid as exported (meshcheck.py: watertight, one body, no edge shared by
more than two faces, no boundary edge, no duplicate or coincident faces, every probed face separating inside from
outside by the generalized winding number at +-1e-3 and +-1e-4 mm), plus manifold3d re-import (status, bodies,
volume, genus) and sha256. Writes ../checks/release-meshcheck-v19.json.
"""
from __future__ import annotations

import ext_lib as E
import meshcheck

FILES = dict(E.PARTS) | {'resistor_envelope_v19': E.OUT / 'resistor_envelope_v19-world.stl'}


def main():
    out = {'_method': __doc__.strip(), 'parts': {}}
    for key, p in FILES.items():
        r, _ = meshcheck.check(p)
        M = E.stl_man(p)
        r['manifold3d'] = {'status': str(M.status()), 'bodies': len(M.decompose()), 'volumeMm3': M.volume(),
                           'genus': M.genus()}
        r['sha256'] = E.sha(p)
        r['bounds'] = E.bbox(M)
        out['parts'][key] = E.rnd(r, 4)
        fs = r['faceSeparationTest']
        print(key, 'clean', r['clean'], 'wt', r['watertight'], 'bodies', r['bodies'], 'pinched',
              r['edgesSharedByMoreThanTwoFaces'], 'coincident', r['coincidentFaceGroupsByGeometry'], 'dup',
              r['duplicateFaceGroups'], 'sepDefects', fs['defectFacesFailingAllEps'], 'needles',
              r['needleFacesInradiusBelow1e-4'], 'needleArea', round(r['needleTotalAreaMm2'], 6), 'needleMaxEdge',
              round(r['needleMaxEdgeMm'], 4), 'vol', round(M.volume(), 3), r['sha256'][:12], flush=True)
    out['allClean'] = all(v['clean'] for v in out['parts'].values())
    E.jdump(out, E.OUT / 'checks' / 'release-meshcheck-v19.json')
    print('all clean', out['allClean'])


if __name__ == '__main__':
    main()
