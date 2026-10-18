#!/usr/bin/env python3
"""Source-bound cap classification/retirement. Each CAD mode needs root token.

Single canonical base: curved-head/curved-cap-final-candidate-world.stl.
No broad removal box and no union of competing full-cap branches.
"""
import argparse,gc,json
from pathlib import Path
import bounded_amp_check as core
D=Path(__file__).resolve().parent;H=D.parent;K=H/'curved-head';U=H/'usb-access/usb-repair'
BASE=K/'curved-cap-final-candidate-world.stl';NATIVE=K/'community-curved-head-world.stl';AUDIO=K/'audio-roof-posts-world.stl';MOUNTS=K/'audio-mounts.json';OPENRB=K/'openrb-four-internal-posts-world.stl';ROTATED=H/'cabling-release-20261008/audio-route-candidate.json'

def inputs(extra=()):return core.fingerprint([Path(__file__),D/'bounded_amp_check.py',BASE,NATIVE,AUDIO,MOUNTS,OPENRB,ROTATED,*extra])
def load(p):return core.solid({'path':p})
def vol(s):return max(0,float(s.volume()))
def describe_solid(s):return {'volumeMm3':vol(s),'boundsMm':list(s.bounding_box()) if vol(s)>1e-5 else None}
def old_rows():
 rows=[r for r in json.loads(MOUNTS.read_text())['posts'] if r['owner']=='amplifier'];assert len(rows)==2;return rows

def old_amp_features(native):
 """Select only the recorded amp posts from the exact audio-post artifact.
 Cylinders are tight selectors, not direct cutters applied to the cap.
 """
 audio=load(AUDIO);selected=None
 for r in old_rows():
  # +.001 selector tolerance covers STL float round-off; the actual cutter
  # remains bounded by the unchanged source audio-post mesh.
  p=[*r['xyMm'],r['startZmm']-.001]
  selector=core.mf.Manifold.cylinder(r['postLengthMm']+.002,2.001,circular_segments=96).translate(p)
  s=audio^selector;selected=s if selected is None else (selected+s).as_original();del s,selector;gc.collect()
 speaker=audio-selected
 removable=(selected-native).as_original();del audio,selected;gc.collect()
 return removable,speaker

def classify(delta):
 core.guarded_import();usb=U/'head-cap-usb-service-world.stl';ampfile=D/'amplifier-terminal-receiving-world.stl';amp=load(ampfile).translate(delta);cap=load(usb);contact=amp^cap;del amp,cap;gc.collect()
 native=load(NATIVE);skin=contact^native;added=contact-native;out={'deltaWorldMm':delta,'contact':describe_solid(contact),'nativeSkinContact':describe_solid(skin),'addedFeatureContact':describe_solid(added),'integrationReady':False,'inputHashes':inputs([usb,ampfile])}
 old,speaker=old_amp_features(native);matched=added^old;unclassified=added-old
 out['matchedOriginalAmpPostContact']=describe_solid(matched);out['otherAddedFeatureContact']=describe_solid(unclassified)
 out['partitionResidualMm3']=out['contact']['volumeMm3']-out['nativeSkinContact']['volumeMm3']-out['addedFeatureContact']['volumeMm3'];assert abs(out['partitionResidualMm3'])<1e-3
 for key,s in [('all',contact),('native-skin',skin),('old-amp-post',matched),('other-added',unclassified)]:
  if vol(s)>1e-5:core.export(s,D/f'amp-cap-contact-{key}-world.stl')
 core.atomic_json(D/'amp-cap-contact-classification.json',out);print(json.dumps({k:v for k,v in out.items() if k!='inputHashes'}))

def retire():
 core.guarded_import();native=load(NATIVE);base=load(BASE);old,speaker=old_amp_features(native);removed=base^old;after=(base-old).as_original()
 # Prove the exact changed set retains skin and every source non-amp audio
 # feature plus all OpenRB posts. Do not waive such loss as source contact.
 tests={'nativeSkinRemovedMm3':vol(removed^native),'speakerFeatureRemovedMm3':vol(removed^speaker)}
 del speaker;gc.collect();openrb=load(OPENRB);tests['openrbFeatureRemovedMm3']=vol(removed^openrb);del openrb;gc.collect()
 tests['addedMaterialMm3']=vol(after-base);tests['unexpectedRemovalMm3']=vol((base-after)-old)
 assert all(v<1e-4 for v in tests.values()),tests
 core.export(after,D/'cap-original-amp-posts-retired-world.stl')
 report={'status':'ORIGINAL_AMP_POSTS_RETIRED_ONLY','integrationReady':False,'canonicalBase':str(BASE),'originalAmpPosts':old_rows(),'removed':describe_solid(removed),'preservationChecks':tests,'inputHashes':inputs(),'outputSha256':core.sha(D/'cap-original-amp-posts-retired-world.stl'),'pending':'New amp posts, hardware relocation, current USB opening and explicit current neck cut; complete scene and motion.'}
 core.atomic_json(D/'cap-original-amp-posts-retired.json',report);print(json.dumps({k:v for k,v in report.items() if k!='inputHashes'}))

def new_post(number,delta):
 core.guarded_import();assert number in [0,1];p=json.loads(ROTATED.read_text())['newAmpHoleBottomMm'][number];p=[p[i]+delta[i] for i in range(3)]
 native=load(NATIVE);near=native^core.mf.Manifold.cube([4.02,4.02,60],True).translate([p[0],p[1],140]);del native;gc.collect();filled=near
 # One roof patch/layer at a time; no transformed scene cache.
 for i in range(1,61):
  shifted=near.translate([0,0,-i*.5]);filled=(filled+shifted).as_original();del shifted;gc.collect()
 raw=core.mf.Manifold.cylinder(30,2,circular_segments=48).translate(p);bore=core.mf.Manifold.cylinder(7.2,1.05,circular_segments=48).translate([p[0],p[1],p[2]-.1]);post=((raw^filled)-bore).as_original();del near,filled,raw,bore;gc.collect()
 f=D/f'amp-new-post-{number}-world.stl';core.export(post,f)
 # Candidate preparation only: remaining wall, native-skin containment,
 # thread support, and path tests must run on the assembled final candidate.
 report={'integrationReady':False,'number':number,'deltaWorldMm':delta,'holeBottomMm':p,'diameterMm':4,'pilotDiameterMm':2.1,'pilotDepthMm':7.2,'spec':'M2.5 x8 TAP','pcbStackMm':1.57,'nominalEngagementMm':6.43,'inputHashes':inputs(),'output':str(f),'outputSha256':core.sha(f),'bounds':describe_solid(post),'pending':'Must check full-depth supporting material, interference and tool access; no strength/physical acceptance.'}
 core.atomic_json(D/f'amp-new-post-{number}.json',report);print(json.dumps({k:v for k,v in report.items() if k!='inputHashes'}))

def assemble():
 core.guarded_import();basefile=D/'cap-original-amp-posts-retired-world.stl';receipt=json.loads((D/'cap-original-amp-posts-retired.json').read_text());assert core.sha(basefile)==receipt['outputSha256']
 for p,h in receipt['inputHashes'].items():assert core.sha(p)==h,p
 cap=load(basefile);src=[basefile,D/'cap-original-amp-posts-retired.json'];delta=None
 for i in range(2):
  rfile=D/f'amp-new-post-{i}.json';r=json.loads(rfile.read_text());f=Path(r['output']);assert core.sha(f)==r['outputSha256']
  for p,h in r['inputHashes'].items():assert core.sha(p)==h,p
  if delta is not None:assert r['deltaWorldMm']==delta
  delta=r['deltaWorldMm'];post=load(f);cap=(cap+post).as_original();del post;gc.collect();src.extend([rfile,f])
 assert len(cap.decompose())==1,'New post disconnected from cap';output=D/'cap-new-amp-before-final-openings-world.stl';core.export(cap,output)
 report={'status':'NEW_AMP_CAP_BEFORE_CURRENT_USB_AND_NECK_CUTS','integrationReady':False,'deltaWorldMm':delta,'output':str(output),'outputSha256':core.sha(output),'inputHashes':inputs(src),'next':'Run existing apply_usb_service_opening.py with this exact --cap and distinct output in gpio-audio-repair. Then explicit neck-owner cut. Never reload old USB full-cap mesh after this step.'};core.atomic_json(D/'cap-new-amp-before-final-openings.json',report);print(json.dumps(report))

def hardware(delta):
 core.guarded_import();f=K/'cap-eight-screw-heads-four-nuts-world.stl';base=load(f);old_heads=None;new_screws=None;new_rows=json.loads(ROTATED.read_text())['newAmpHoleBottomMm']
 for old,new in zip(old_rows(),new_rows):
  a=[*old['xyMm'],old['startZmm']-1.57]
  old_head=core.mf.Manifold.cylinder(1.7,2.5,circular_segments=48).translate([a[0],a[1],a[2]-1.7])
  old_heads=old_head if old_heads is None else (old_heads+old_head).as_original()
  b=[new[i]+delta[i] for i in range(3)];b[2]-=1.57
  screw=core.mf.Manifold.cylinder(8,1.25,circular_segments=48).translate(b)+core.mf.Manifold.cylinder(1.7,2.5,circular_segments=48).translate([b[0],b[1],b[2]-1.7])
  new_screws=screw if new_screws is None else (new_screws+screw).as_original();del old_head,screw;gc.collect()
 kept=(base-old_heads).as_original();removed=base^old_heads;assert len(removed.decompose())==2
 new=(kept+new_screws).as_original();output=D/'hardware-current-amp-world.stl';core.export(new,output);core.export(new_screws,D/'amp-new-two-screws-world.stl')
 report={'integrationReady':False,'deltaWorldMm':delta,'removedOldHeadGeometry':describe_solid(removed),'retainedHardwareVolumeMm3':vol(kept),'outputSha256':core.sha(output),'inputHashes':inputs([f]),'boundary':'Retains all original non-amp hardware; replaces only exact two original cylindrical amp heads. New amp screws now explicitly include8mm shafts. Thread/pilot contacts require matched-interface checks; all external collisions remain failures.'}
 core.atomic_json(D/'hardware-current-amp.json',report);print(json.dumps({k:v for k,v in report.items() if k!='inputHashes'}))

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['classify','retire','post','assemble','hardware','describe']);p.add_argument('--delta',type=float,nargs=3,default=[16,0,3]);p.add_argument('--post',type=int,default=0);a=p.parse_args()
 if a.mode=='describe':print(json.dumps({'base':str(BASE),'oldAmpPosts':old_rows(),'modes':'classify -> retire -> post0 -> post1 -> assemble -> existing USB cut -> explicit neck cut','cadImports':False},indent=2));return
 if a.mode=='classify':classify(a.delta)
 elif a.mode=='retire':retire()
 elif a.mode=='post':new_post(a.post,a.delta)
 elif a.mode=='assemble':assemble()
 elif a.mode=='hardware':hardware(a.delta)
if __name__=='__main__':main()
