import json, numpy as np, trimesh, sys
W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
A='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/a7z-head/'
F='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/face-a7z/'
names={'head_cap':W+'head_cap.stl','head_cap_a7z':A+'head_cap_a7z-world.stl','head_bottom':W+'head_bottom.stl','face_panel':W+'face_panel.stl',
 'face_panel_a7z':F+'face_panel_a7z.stl','eye_trim':W+'eye_trim.stl','camera_13m214':F+'camera_13m214.stl','camera_board':W+'camera_board.stl',
 'antenna':W+'antenna.stl','antenna_coax':W+'antenna_coax.stl','clip_cap':W+'clip_cap.stl','clip_head':W+'clip_head.stl','amplifier':W+'amplifier.stl','speaker':W+'speaker.stl','speaker_retainer':W+'speaker_retainer.stl',
 'touch_pad_l1':W+'touch_pad_l1.stl','touch_pad_r1':W+'touch_pad_r1.stl','touch_pad_l2':W+'touch_pad_l2.stl','touch_pad_r2':W+'touch_pad_r2.stl','touch_pad_m':W+'touch_pad_m.stl','touch_xiao':W+'touch_xiao.stl',
 'a7z_pcb':A+'a7z_parts/a7z_pcb.stl','soc':A+'a7z_parts/soc_a733.stl','ram':A+'a7z_parts/ram.stl','wifi':A+'a7z_parts/wifi_module_fcu760k.stl','fan_conn':A+'a7z_parts/fan_connector.stl','usb_c_power':A+'a7z_parts/usb_c_power.stl','usb_c_otg':A+'a7z_parts/usb_c_otg_dp.stl','hdmi':A+'a7z_parts/micro_hdmi.stl','ribbon':A+'a7z_parts/camera_ribbon_a7z_end.stl','camera_ribbon':W+'camera_ribbon.stl','jaw_frame':W+'jaw_frame.stl'}
out={}
for k,p in names.items():
    try:
        m=trimesh.load(p)
        b=m.bounds; out[k]={'min':b[0].round(1).tolist(),'max':b[1].round(1).tolist(),'centroid':m.centroid.round(1).tolist(),'volume':round(float(m.volume),1) if m.is_volume else None}
        print(f"{k:16s} x {b[0][0]:6.1f}..{b[1][0]:6.1f}  y {b[0][1]:6.1f}..{b[1][1]:6.1f}  z {b[0][2]:6.1f}..{b[1][2]:6.1f}  vol {out[k]['volume']}")
    except Exception as e:
        print(k,'ERR',e)
json.dump(out,open(sys.argv[1],'w'),indent=1)
# same-cap check: is world/head_cap.stl identical to a7z-head/head_cap_a7z-world.stl?
import hashlib
for p in (W+'head_cap.stl',A+'head_cap_a7z-world.stl',W+'eye_trim.stl',F+'eye_trim_a7z.stl',W+'face_panel.stl',F+'face_panel_a7z.stl',W+'face_panel-v18.stl'):
    print(hashlib.sha256(open(p,'rb').read()).hexdigest()[:12], p.split('/')[-2:], )
