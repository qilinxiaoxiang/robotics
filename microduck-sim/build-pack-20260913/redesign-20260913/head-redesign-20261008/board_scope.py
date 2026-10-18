"""Board identity boundary for the isolated head candidate; changes no geometry."""
import base64, hashlib
import numpy as np
BOARD_SOURCES = [
 {'url':'https://www.raspberrypi.com/news/raspberry-pi-zero/', 'verified':'2026-10-08', 'facts':{'originalZeroBoardFootprintMm':[65,30]}},
 {'url':'https://www.raspberrypi.com/documentation/computers/raspberry-pi.html', 'verified':'2026-10-08', 'facts':{'originalZeroCsi':'CSI added from rev1.3; 22-pin, 0.5mm pitch', 'pi3AplusBAndBplusCsi':'15-pin, 1mm pitch'}},
 {'url':'https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-b-plus-product-brief.pdf', 'verified':'2026-10-08', 'facts':{'pi3BplusBoardFootprintMm':[85,56]}},
 {'url':'https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-a-plus-product-brief.pdf', 'verified':'2026-10-08', 'facts':{'pi3AplusBoardFootprintMm':[65,56], 'scope':'Board footprint, not a populated CAD envelope.'}}
]
def apply_board_scope(report, parts):
 p=next(p for p in parts if p['key']=='pi')
 v=np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3)
 report['boardScope']={
  'userClarification':'Available board is Pi 3 or first-generation Pi Zero; not Zero 2 W. Exact subtype/revision is unknown.',
  'referenceModel':'First-generation Pi Zero outline reference',
  'referenceMeshKind':'65 x 30 mm PCB slab only; populated components, connectors and cables are not represented.',
  'referenceMeshWorldBoundsMm':[v.min(0).tolist(),v.max(0).tolist()],
  'referenceMeshWorldExtentsMm':np.ptp(v,axis=0).tolist(),
  'referenceVerticesSha256':hashlib.sha256(base64.b64decode(p['positionB64'])).hexdigest(),
  'pi3FitVerified':False,'exactBorrowedBoardIdentified':False,'completeZeroBoardFitVerified':False,
  'placementConclusion':'The existing Zero-outline slab remains in place in this candidate only. The measured 6.92 mm camera gap does not establish complete Zero-board fit or Pi 3 fit.',
  'cameraCableConclusion':'A first-generation Zero with CSI (original Zero rev1.3 or Zero W) uses a 22-pin/0.5mm board connector and a 15-to-22-pin camera cable. Earlier original Zero revisions lack CSI. Pi 3 A+/B/B+ uses a 15-pin/1mm board connector and a 15-to-15-pin camera cable. Exact board, cable length and routing remain unverified.'
 }
 report['officialSources']=[s for s in report['officialSources'] if s['url'] not in {x['url'] for x in BOARD_SOURCES}]+BOARD_SOURCES
 report['status']='zero-outline-eye-candidate-pi3-and-complete-board-fit-unverified'
 report['ribbonRouteStatus']='Only camera connector and first 12mm exit reserved. The reference Zero outline has no verified populated connector envelope. Full cable loop, exact board-specific cable, bend radius and latch access remain unverified; Pi 3 routing has not been modeled.'
 report['unchanged']=['Zero-outline reference slab pose and four mounting pilots; not a complete-board fit claim','OpenRB/audio positions','head-cap shell geometry','native single-eye outside outline']
 return report
