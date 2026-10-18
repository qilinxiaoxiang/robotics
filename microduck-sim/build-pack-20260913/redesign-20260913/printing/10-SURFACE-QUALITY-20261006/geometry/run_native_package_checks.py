"""Read available final native variants; write owned geometry/native reports only."""
from pathlib import Path
import argparse,hashlib,json,sys,traceback
from concurrent.futures import ProcessPoolExecutor,as_completed
import audit_native_bore_envelopes as bore
import audit_native_functional_seats as seats

G=Path(__file__).resolve().parent;OUT=G/'native';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit_variant(v,signatures):
    printer=v['printer'];group=v['group'];project=v['project'];native=v.get('archive',v.get('native_archive',v.get('gcode')))
    native=str(Path(native).resolve())
    key=printer+'-'+group;bp=OUT/(key+'-bore.json');sp=OUT/(key+'-seats.json');entry=dict(printer=printer,group=group,primary=v.get('primary',False),errors=[])
    try:
        actual_sig=dict(project_sha256=sha(project),file_sha256=sha(native),checker_source_hashes=signatures)
        cached=False;rebound_exact_gcode=False
        if bp.exists() and sp.exists():
            b=json.loads(bp.read_text());s=json.loads(sp.read_text())
            cached=b.get('checker_signature')==actual_sig and s.get('checker_signature')==actual_sig
            if not cached:
                prior=b.get('checker_signature',{})
                prior_seat=s.get('checker_signature',{})
                unchanged_inputs=(prior.get('project_sha256')==actual_sig['project_sha256'] and
                                  prior_seat.get('project_sha256')==actual_sig['project_sha256'] and
                                  prior.get('checker_source_hashes')==signatures and prior_seat.get('checker_source_hashes')==signatures)
                if unchanged_inputs:
                    _,_,outer_hash,body_hash=bore.read_code(native,project,printer)
                    # This is an exact body-byte proof, not a claimed unchanged
                    # physics or header-stripped comparison. Archive machine and
                    # geometry values are independently checked by the other gate.
                    if body_hash==b.get('gcode_sha256')==s.get('gcode_sha256'):
                        rebound_exact_gcode=True;cached=True
                        for report,path in [(b,bp),(s,sp)]:
                            report['exact_gcode_bytes_rebound_from_file_sha256']=report['file_sha256']
                            report['gcode']=native;report['file_sha256']=outer_hash;report['checker_signature']=actual_sig
                            path.write_text(json.dumps(report,indent=2)+'\n')
        if not cached:
            b=bore.audit(project,native,group,printer);b['checker_signature']=actual_sig;bp.write_text(json.dumps(b,indent=2)+'\n')
            s=seats.measure(project,native,group,printer);s['checker_signature']=actual_sig;sp.write_text(json.dumps(s,indent=2)+'\n')
        entry.update(project=project,native=native,project_sha256=actual_sig['project_sha256'],native_sha256=actual_sig['file_sha256'],
                     bore_report=str(bp),bore_report_sha256=sha(bp),seat_report=str(sp),seat_report_sha256=sha(sp),
                     bore_passed=b['passed'],seat_passed=s['passed'],cached_exact_source_and_file_hash=cached and not rebound_exact_gcode,rebound_exact_gcode_bytes_and_project=rebound_exact_gcode,
                     actual_object_count=len(b['objects']),instance_indices=[o['manifest_instance_index'] for o in b['objects']])
        entry['passed']=b['passed'] and s['passed']
    except Exception as exc:entry['errors'].append(str(exc));entry['traceback']=traceback.format_exc();entry['passed']=False
    return entry

def run(manifest):
    package=json.loads(Path(manifest).read_text());variants=package['variants'];rows=[];primary=[]
    signatures={str(p):sha(p) for p in [G/'surface-audit.json',G/'native-feature-requirements.json',
                                       G/'audit_native_bore_envelopes.py',G/'audit_native_functional_seats.py',G/'native_material_frame.py',G/'native_anchor_paths.py',G/'source_core_slab.py']}
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(audit_variant,v,signatures):v for v in variants}
        for future in as_completed(futures):
            entry=future.result();rows.append(entry)
            if entry.get('primary'):primary.extend(entry.get('instance_indices',[]))
            print('NATIVE_VARIANT',entry['printer']+'-'+entry['group'],entry['passed'],entry['errors'],flush=True)
            partial=dict(variants=rows,manifest=str(Path(manifest).resolve()),manifest_sha256=sha(manifest),complete_ten_variants=False,
                         complete_primary_89=False,physical_fit_verified=False,physical_finish_verified=False)
            (G/'native-functional-verification-in-progress.json').write_text(json.dumps(partial,indent=2)+'\n')
    rows.sort(key=lambda entry:(entry['printer'],entry['group']))
    coverage=len(primary)==89 and len(set(primary))==89 and set(primary)==set(range(89))
    result=dict(passed=len(rows)==10 and coverage and all(r['passed'] for r in rows),
                checked_available_variants=len(rows),available_variants_passed=all(r['passed'] for r in rows),
                complete_ten_variants=len(rows)==10,complete_primary_89=coverage,primary_instance_indices=primary,
                variants=rows,manifest=str(Path(manifest).resolve()),manifest_sha256=sha(manifest),source_hashes=signatures,
                scope='Native known-empty bore bead-envelope and sparse functional-interface ROI checks; source geometry/spacing/thumbnails/machine verification remain separate gates.',
                physical_fit_verified=False,physical_finish_verified=False)
    (G/'native-functional-verification.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');args=p.parse_args();r=run(args.manifest)
    print(json.dumps({k:r[k] for k in ['passed','checked_available_variants','available_variants_passed','complete_ten_variants','complete_primary_89']}))
    sys.exit(0 if r['passed'] else 1)
