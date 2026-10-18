"""Verify current per-connection assembly evidence and its user-facing handoff."""
from pathlib import Path
import hashlib
import json
import re

P = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect_assembly():
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    try:
        ledger = json.loads((P/'assembly-fasteners.json').read_text())
        require(ledger.get('physical_assembly_verified') is False, 'Unmeasured physical assembly success')
        rows = ledger['connections']
        require(rows and len({r['id'] for r in rows}) == len(rows), 'Missing or duplicate fastener connections')
        for row in rows:
            require(row.get('passed') is True and bool(row.get('spec')) and row.get('quantity',0)>0,
                    'Unverified fastener: '+row.get('id','unnamed'))
        reports = {}
        for filename, digest in ledger['source_reports'].items():
            path=P/filename
            require(sha(path)==digest, 'Assembly schedule predates geometry report: '+filename)
            report=json.loads(path.read_text()); reports[filename]=report
            require(report.get('passed') is True, 'Failed connection audit: '+filename)
            required_sources={'evidence_sources.py', 'assembly_fk.py', 'robot_allcollisions.xml'}
            required_sources.update({'jaw-head-seats.json', 'verify_joint_fasteners.py'} if path.name=='joint-fasteners.json' else {'camera-fastener-validation.json', 'electronics_audit.py', 'electronics-head-closure-verification.json'})
            require(required_sources <= {Path(name).name for name in report['source_hashes']}, 'Incomplete fastener source binding: '+filename)
            for name, expected in report['source_hashes'].items():
                source=Path(name) if Path(name).is_absolute() else (P/name if (P/name).exists() else path.parent/name)
                require(source.is_file() and sha(source)==expected, 'Fastener evidence source changed: '+name)
            actual={r['id']:r for r in rows if r['audit_file']==filename}
            require(set(actual)=={r['id'] for r in report['connections']}, 'Connection coverage changed: '+filename)
            for r in report['connections']:
                if r['id'] in actual:
                    require(all(actual[r['id']].get(k)==v for k,v in r.items()), 'Schedule differs from native measurement: '+r['id'])
        electronics=reports['fastener-audit/electronics-fasteners.json']
        e={r['id']:r for r in electronics['connections']}
        require(e['camera_pcb_10']['full_nut_engagement'] and e['camera_pcb_10']['quantity']==4, 'Camera nut engagement regression')
        require(e['imu_rear_cover']['quantity']==4 and 'M2 x 6' in e['imu_rear_cover']['spec'], 'Rear-cover old alarm stack regression')
        require(e['fuse_carrier']['quantity']==4 and e['fuse_carrier']['nut_quantity']==4, 'Working fuse carrier fasteners omitted')
        require('4 diameter x1.5' in e['pi']['spec'], 'Pi head envelope regression')
        joint=reports['fastener-audit/joint-fasteners.json']
        require(joint.get('motor_count')==15, 'Joint audit does not cover all fifteen motors')
        require(not joint.get('unresolved'), 'Unresolved joint connection remains')
        require(joint.get('clearance_checks_passed') is True, 'Screw head or retainer interference remains')
        closure_binding=electronics.get('head_closure_native_verification',{})
        require(closure_binding.get('passed') is True, 'Head closure native verification missing')
        closure_path=Path(closure_binding['path'])
        require(sha(closure_path)==closure_binding['sha256'], 'Head closure report changed after electronics audit')
        closure=json.loads(closure_path.read_text())
        require(closure.get('passed') is True, 'Head closure native report failed')
        for name, digest in closure['source_hashes'].items():
            source=Path(name)
            require(source.is_file() and sha(source)==digest, 'Head closure evidence source changed: '+name)
        catalog={r['id']:r for r in json.loads((P.parent/'procurement/catalog-en.json').read_text())}
        required_catalog={'pi_mount_screws':e['pi']['quantity']+e['motor_support_frame']['quantity'],
          'tap_m25_8':e['head_cap_closure']['quantity'], 'm2_18':e['openrb']['quantity'],
          'm2_25':e['audio_carrier']['quantity'], 'm2_10':e['camera_pcb_10']['quantity'],
          'm3_10':e['camera_foot']['quantity'], 'm3_20':e['camera_hinge']['quantity'],
          'm2_20':e['fuse_carrier']['quantity'], 'm2_6':e['imu_rear_cover']['quantity'],
          'm2_5':e['imu_clamp']['quantity'], 'm2_nuts':14,'m3_nuts':3,'m3_washers':4,
          'washer_m25_din433':joint['small_washers']}
        for length in [4,5,6,7,8,10]:
            required_catalog[f'tap_m2_{length}']=joint['fastener_totals'][f'M2 x {length} TAP']
        required_catalog['idler_screw_sets']=joint['fastener_totals']['M2.6 x 6 TAP']
        required_catalog['tap_m26_8']=joint['fastener_totals']['M2.6 x 8 TAP']
        for item,quantity in required_catalog.items():
            require(item in catalog and catalog[item]['installed_quantity']==quantity,
                    'Procurement engineering count differs from installed connection schedule: '+item)
        guide=(P/'ASSEMBLY.html').read_text()
        require('ASSEMBLY.html' in (P/'START-HERE.html').read_text(), 'Current handbook omits assembly route')
        for row in rows:
            require(row['id'] in guide, 'Reader guide omits connection: '+row['id'])
        for required in ['head-cap-usb-service-print.stl','7 × 52 × 15','M2×10','400 mm','SC0727','DFR1202']:
            require(required in guide, 'Current assembly instruction missing: '+required)
        for match in re.finditer(r'(?:href|src)="([^"#]+)',guide):
            target=match[1].split('#')[0]
            if '://' not in target:
                require((P/target).exists(), 'Broken assembly resource: '+target)
        require(not re.search(r'<table\b',guide,re.I), 'Assembly guide contains disabled user-facing tables')
    except (OSError, KeyError, TypeError, ValueError) as exc:
        errors.append('Incomplete assembly handoff: '+str(exc))
    return errors

if __name__=='__main__':
    errors=inspect_assembly()
    report={'passed':not errors,'errors':errors,'physical_tests':0}
    (P/'assembly-handoff-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if errors:
        raise SystemExit(1)
    print('FASTENER_ACCEPTANCE current geometry, all fifteen motors and installed connection schedule verified')
    print('GUIDE_ACCEPTANCE current assembly route, instructions and all connection groups verified')
