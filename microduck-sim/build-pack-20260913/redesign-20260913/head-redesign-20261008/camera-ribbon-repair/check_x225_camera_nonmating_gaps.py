from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py');m=json.loads(read(O/'candidate-manifest.json'));files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']};cam=load(H/files['camera_board']);housing=cam^box([79.05,-50,100],[95,50,160]);checks=[]
for k in ['face_panel','eye_trim','head_cap','pi','zero_w_components','zero_w_gpio_solder_tails']:
 q=load(H/files[k]);v,bb=n['volume'](housing,q);checks.append({'part':'camera_front_housing_excluding_PCB_bearing_plane','obstacle':k,'overlapMm3':v,'minimumGapCapped5Mm':float(housing.min_gap(q,5)),'boundsMm':bb})
r={'integrationReady':False,'scope':'Non-mating front housing only; PCB bearing/contact surfaces excluded explicitly byX>=79.05','engineeringTargetMm':.5,'manufacturerToleranceClaim':False,'checks':checks,'sourceHashes':n['hashes']};(O/'camera-nonmating-gaps.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(checks,indent=2))
