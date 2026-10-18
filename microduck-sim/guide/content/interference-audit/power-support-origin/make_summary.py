"""Write summary.json: the decision numbers of the power-support origin study, each with the file it comes from.
Reads only this folder's JSON outputs and the scratch reach arrays (no CAD). Run after every other script."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

HERE = Path(__file__).resolve().parent
J = lambda n: json.loads((HERE / n).read_text())
geo = J('geometry.json'); rs = J('reach-summary.json'); tf = J('trim-feasibility.json'); sw = J('sweep-summary.json')
cb = J('candidates/corner15-deck19-build.json'); cc = J('candidates/corner15-deck19-check.json')
src = L.walking_sources(); trace = np.load(L.SCRATCH / 'walk_trace.npy'); frame = np.load(L.SCRATCH / 'walk_frame.npy')
final = np.array([s['file'].startswith('phase1-candidate-') for s in src])[trace]
delay = np.array([s['sensor_delay_ticks'] == 2 for s in src])[trace]
adopted = np.array([not s['fell'] and not s['blend'] for s in src])[trace]


def gap_text(v):
    """99 = never flagged by the screen (true gap >= 2 mm guaranteed); 6.0 = beyond the exact search radius."""
    return '>= 2 (not flagged by the screen)' if v >= 98 else ('>= 6' if v >= 6.0 else round(float(v), 3))


side_out = {}
for side in ('left', 'right'):
    z = np.load(L.SCRATCH / f'reach-{side}-frames.npz'); ex = z['exact']; tb = z['exact_tb']
    d = {}
    for g, m in (('finalController_all33', final), ('finalController_withoutSensorDelay', final & ~delay),
                 ('finalController_sensorDelay40ms', final & delay), ('adopted_allControllers', adopted),
                 ('adopted_withoutSensorDelay', adopted & ~delay)):
        e = ex[m]; under = np.flatnonzero(m & (ex < 2))
        d[g] = dict(frames=int(m.sum()), minGapSupport_mm=gap_text(e.min()), framesUnder2mm=int((e < 2).sum()), contactFrames=int((e == 0).sum()),
                    minGapTray_mm=gap_text(tb[m, 0].min()), minGapBoard_mm=gap_text(tb[m, 1].min()),
                    runsUnder2mm=sorted(set(src[trace[i]]['file'] for i in under)),
                    timeOfUnder2mmFrames_s=[round(float((frame[under].min() + 1) * 0.02), 2), round(float((frame[under].max() + 1) * 0.02), 2)] if len(under) else None)
    o = rs[f'{side}_originalSupport']
    d['upstreamOriginalSupport'] = dict(adopted_minGap_mm=gap_text(o['adopted']['minGapSupport']), adopted_framesUnder2mm=o['adopted']['under2'],
                                        finalController_minGap_mm=gap_text(o['finalController']['minGapSupport']),
                                        excludedFallingRuns_minGap_mm=gap_text(o['excluded']['minGapSupport']))
    env = rs[f'{side}_envelope']; hip = rs[f'{side}_hipgrid']
    d['walkingEnvelopeGrid'] = dict(poses=env['poses'], grid=env['grid'], minGapSupport_mm=env['minGapSupport'], posesUnder2mm=env['under2'],
                                    posesUnder2mmByRegion=env['byRegionUnder2'], minGapTray_mm=env['minTray'], minGapBoard_mm=env['minBoard'])
    d['hipLinksOverWalkingYawRoll'] = dict(poses=hip['poses'], minGapSupport_mm=round(hip['minGapSupport'], 3))
    d['regionsUnder2mm_adopted'] = rs[side]['adopted']['framesUnder2ByRegion']
    d['partsUnder2mm_adopted'] = rs[side]['adopted']['partHitsUnder2']
    d['trimFeasibility_finalController'] = {k: tf[side]['finalController'][k] for k in
                                            ('postMinRemainingSection_mm2', 'postAtZ', 'postRemovedFraction_max', 'postMustRemoveBounds',
                                             'deckMustRemoveBounds', 'deckMustRemoveInnermostAbsY')}
    d['trimFeasibility_adoptedAll'] = {k: tf[side]['adopted'][k] for k in ('postMinRemainingSection_mm2', 'postRemovedFraction_max', 'deckMustRemoveInnermostAbsY')}
    d['candidate_corner15_deck19'] = {g: {k: cc[f'{side}_frames'][g][k] for k in ('currentMin', 'candidateMin', 'currentUnder2', 'candidateUnder2',
                                                                               'candidateContact0', 'trayMinInGroupRechecked')}
                                      for g in ('finalController', 'finalControllerNoSensorDelay', 'adopted')}
    d['sweep_clearPostX0_adopted'] = sw[side]['clearPostX0_adopted']
    d['sweep_innermostLegAbsY_byX'] = [(p['x'], p['innermostY_adopted']) for p in sw[side]['innermostLegY_inPostBand_byX'] if -50 <= p['x'] <= -20][::2]
    side_out[side] = d

ANSWERS = dict(
    whyIntroduced='The deck and its two hanger posts were added on 2026-09-12 as the "vented lower shelf for motor regulator" for the Pololu '
                  'D24V150F5 servo regulator, in the version that kept a 2S battery in the original back bay and moved both regulators into the '
                  'torso (hardware-design-20260912/whole-robot-20260912/assembly/README.md line 5; ../README.md lines 3, 24, 65; '
                  'assembly/build_compact_battery.py lines 23-34). Neither regulator is in the current wall-powered build. On 2026-10-09 the DFR1202 '
                  'took the battery bay (PROJECT-CONTEXT.json current_build.powerbank_trial_20261008.userDecision) and the OpenRB-150 moved onto the '
                  'empty deck (guide/print/release-V1.6/evidence/openrb_tray-change.json reason). microduck-sim is not tracked in git, so no commit exists.',
    positionReasonable='The power path (DFR1202 in the old battery bay, J and 10 A fuse in the rear bay, XT30 at the lower back) is on the back, '
                       'where upstream puts it, and does not use the deck. The deck now carries only the OpenRB tray. It hangs up to 13.4 mm below the '
                       'original part along the inner edge of the shin path; every adopted-frame approach under 2 mm lands on that added material, while '
                       'the original upstream shape stays >= 3.91 mm (left) and 4.79 mm (right) away. Balance does not need it. Acceptable at nominal '
                       'timing; no margin for a 40 ms sensor delay.',
    clearances='See sides.*: final controller left support 1.68 mm / tray 2.92 mm; right support 0.00 mm (3 contact frames, 0.68 mm3) / tray '
                '1.46 mm, all in phase1-candidate-old0-sensor40.json during the stop (t 25.58-25.96 s). Without the 40 ms sensor delay no frame is '
                'under 2 mm (closest measured 4.55 mm left, 3.45 mm right). Joint caps = MJCF ranges; minimum over them is 0.00 mm (they contain '
                'the walking envelope grid, which reaches 0.00 mm to support, tray and board on both sides).',
    trimOrRelocation='Not needed at nominal timing. For the 40 ms case a trim cannot reach 2 mm: the right post would keep 1.84 of 9.6 mm2 and '
                     'the deck edge would be cut to |y| 16.3 inside the tray footprint, with the tray still 1.46 mm away. Smallest candidate '
                     'corner15-deck19 (77.5 mm3, changes the already-printed support, hand-fileable) clears the left (1.68 -> 2.21 mm) but not the '
                     'right (0.00 -> 0.06 mm). A relocation that clears the 40 ms case changes the support and the tray (hangers to x -59.1..-51.1, '
                     'deck and tray narrowed to about |y| 16 at x -38..-22) or removes the deck and moves the OpenRB; it needs Shawn\'s confirmation.',
    recommendedAction='Keep the printed support unchanged; measure the real sensor delay before free walking; in the guide\'s back leg-clearance '
                      'check also watch the right post front-outer corner; if the delay is near 40 ms or rubbing appears, choose one of the two '
                      'redesigns. Guide steps.py line 846 should be corrected by its owner: for the final controller the right shin touches the '
                      'support, the left stays 1.68 mm away and its tray gap is 2.92 mm.')

out = dict(
    answers=ANSWERS,
    frame='robot frame, mm: x forward, y left, z up (MuJoCo trunk_base); print frame = robot frame + 57.5 mm in z',
    clearanceNote='Exact gaps (manifold3d min_gap) on every frame the screen flags; the screen flags every frame with a true gap below 2 mm. '
                  'A value below 2 mm is therefore the exact minimum. A value above 2 mm is the closest frame that was measured exactly; '
                  'frames the screen did not flag are only guaranteed to be at least 2 mm away. ">= 2 (not flagged)" means no frame was flagged; '
                  '">= 6" means beyond the 6 mm exact search radius.',
    deckPlastic=dict(volume_mm3=round(geo['added_regions']['deck_and_bosses']['volume_mm3'] + 2 * geo['added_regions']['lower_post_left']['volume_mm3']
                                      + 2 * geo['added_regions']['upper_post_left']['volume_mm3'], 1),
                     PLA_g=round((geo['added_regions']['deck_and_bosses']['volume_mm3'] + 2 * geo['added_regions']['lower_post_left']['volume_mm3']
                                  + 2 * geo['added_regions']['upper_post_left']['volume_mm3']) * 0.00124, 2),
                     openrb_g=13.0, openrb_source='build-pack-20260913/phase1/simulation/mass-manifest.json parts[openrb] (modelled in the head, body jaw_soft)'),
    walkingData=dict(trajectories=len(src), frames=int(len(trace)), adoptedFrames=int(adopted.sum()), finalControllerFrames=int(final.sum()),
                     source='build-pack-20260913/phase1/simulation (phase1-*.json, candidate-*/phase1-*.json)'),
    jointCaps=dict(note='The runtime caps (phase1/runtime/calibration.template.json joint_limits_rad) equal the MJCF ranges of robot_allcollisions.xml '
                        'for all ten leg joints, so caps and full MJCF range are the same box here. That box contains the walking envelope grid, '
                        'which already reaches 0.0 mm to the support, tray and board on both sides, so the minimum over the caps is also 0.0 mm.',
                   hipYaw_left=[-0.4363, 0.5236], hipYaw_right=[-0.5236, 0.4363], hipRoll=[-0.384, 0.384], pitchKneeAnkle=[-1.5708, 1.5708]),
    contactLocation=dict(reportedPoint=geo['reported_contact_point'], addedMaterialBelowOriginal_mm3=round(geo['material']['below_original_bottom_mm3'], 1),
                         addedOutsideOriginalBox_mm3=round(geo['material']['added_outside_original_aabb_mm3'], 1),
                         postSection_mm2=geo['left_post_section_area_mm2'], connectivity=geo['connectivity']),
    sides=side_out,
    candidate=dict(name='corner15-deck19', robotFrame=str(HERE / 'candidates/corner15-deck19-robot-frame.stl'),
                   printFrame=str(HERE / 'candidates/corner15-deck19-print-frame.stl'),
                   edit='45 deg, 1.5 mm chamfer on the front-outer vertical edge of each hanger post (z -57.5..-37.5) and 45 deg, 1.9 mm chamfer on the '
                        'bottom-outer edge of the deck at x -31..-22, both sides',
                   removed_mm3=round(cb['removed_mm3'], 2), removed_g=round(cb['removed_g_PLA'], 3), solids=cb['solids'], watertight=cb['watertight'],
                   bossesSlotsTraySeatUnchanged=all(v[0] == v[1] for k, v in cb['checks'].items() if k.startswith(('boss', 'deckSlot', 'traySeat'))),
                   postSection_mm2_before_after=cb['checks']['leftPostSection_z-50.0_mm2']),
)
(HERE / 'summary.json').write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)[:9000])
