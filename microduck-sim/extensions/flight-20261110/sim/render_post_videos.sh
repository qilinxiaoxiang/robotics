#!/bin/zsh
# Social-post set (LinkedIn 16:9, 小红书 3:4) next to the site renders of render_full_videos_hd.sh, which it never
# overwrites: every output here ends in _post or lives in sim/out/pack_visual_hd/post_parts/. Same runs as
# render_full_videos.sh; each run's outcome row must equal sim/out/pack_visual/full_<scenario>.json (else exit 3).
# Run in the flight-20261110 folder on the Mac mini:
#   zsh sim/mini.sh run 'zsh sim/render_post_videos.sh render'   closer floor-to-table clip and the labelled parts
#   zsh sim/mini.sh run 'zsh sim/render_post_videos.sh post'     cross-faded combined cuts, posters, motion check frames
# FPS=4 gives a quick framing test. Wall time per stage: sim/out/pack_visual_hd/stage_times_post.log
set -e
P=sim/out/pack_visual_hd
Q=$P/post_parts
REC=sim/out/pack_visual
FF=/opt/homebrew/bin/ffmpeg
FP=/opt/homebrew/bin/ffprobe
FPS=${FPS:-60}
CAP_EN="Simulation (MuJoCo). Hardware not yet flown."
CAP_ZH="仿真（MuJoCo），硬件还没飞"
HOVER_S=9          # seconds of the hover clip used in the combined cut
XF=0.5             # cross-fade, s
mkdir -p $Q $P/frames_post
LOG=$P/stage_times_post.log
stamp() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1 wall_s=$2" | tee -a $LOG; }

B=(--case nominal --seed 0 --fan areswei --com-est true --ground-pitch level --takeoff-twr 1.6 --takeoff-ramp 0.1
   --legs handover --cam-follow)
HD=(--video-fps $FPS --video-look studio --cam-smooth 0.35 --cam-fovy 30)
# cameras. hover: as the site clip. table: starts wide enough to show the table top, eases in while the duck climbs
# (1 s to 5 s), then holds close through the flight, landing and stand.
HOVER_169=(--cam-az 128 --cam-el -18 --cam-dist 1.5 --cam-dz -0.09 --cam-smooth 0.2)   # shorter lag: the take-off jump stays below the caption
HOVER_34=(--cam-az 128 --cam-el -18 --cam-dist 1.75 --cam-dz -0.14)
TABLE_169=(--cam-az 52 --cam-el -15 --cam-dist 2.4 --cam-dist-end 1.35 --cam-ease 1,5 --cam-dz 0.02)
TABLE_34=(--cam-az 52 --cam-el -15 --cam-dist 2.6 --cam-dist-end 1.9 --cam-ease 1,5 --cam-dz 0.0)

one() {   # one <scenario> <output stem> <flags...>: run, log wall time, check the outcome row
  local s=$1 o=$2; shift 2
  local t0=$(date +%s)
  timeout 1800 $PY sim/flight.py --scenario $s $B $HD "$@" --out $o.json --video $o.mp4 > $o.log
  stamp "render $o fps=$FPS" $(( $(date +%s) - t0 ))
  $PY sim/outcome_match.py $REC/full_$s.json $o.json | tee -a $LOG
}

if [[ $1 == render ]]; then
  one table_up $P/full_table_up_post --video-size 1920x1080 --video-caption "$CAP_EN" $TABLE_169
  one hover    $Q/hover_169 --video-size 1920x1080 --video-crf 12 --video-caption "$CAP_EN" --video-label "1. Take-off and hover" $HOVER_169
  one table_up $Q/table_up_169 --video-size 1920x1080 --video-crf 12 --video-caption "$CAP_EN" --video-label "2. Floor to table, land, stand" $TABLE_169
  one hover    $Q/hover_34 --video-size 1080x1440 --video-crf 12 --video-caption "$CAP_ZH" --video-label "1. 起飞并悬停" $HOVER_34
  one table_up $Q/table_up_34 --video-size 1080x1440 --video-crf 12 --video-caption "$CAP_ZH" --video-label "2. 飞上桌面、降落、站稳" $TABLE_34
  echo RENDERDONE
fi

combine() {   # combine <hover part> <table part> <output>: hover first HOVER_S s, cross-fade, whole table clip, silent audio
  local off=$(( HOVER_S - XF ))
  $FF -y -loglevel error -i $1 -i $2 -f lavfi -i anullsrc=r=44100:cl=stereo -filter_complex \
    "[0:v]trim=0:${HOVER_S},setpts=PTS-STARTPTS,fps=${FPS},settb=AVTB[a];[1:v]setpts=PTS-STARTPTS,fps=${FPS},settb=AVTB[b];[a][b]xfade=transition=fade:duration=${XF}:offset=${off}[v]" \
    -map "[v]" -map 2:a -shortest -c:v libx264 -crf ${CRF:-19} -preset slow -pix_fmt yuv420p -r $FPS \
    -c:a aac -b:a 48k -movflags +faststart $3
}

if [[ $1 == post ]]; then
  t0=$(date +%s)
  combine $Q/hover_169.mp4 $Q/table_up_169.mp4 $P/combined_post.mp4
  combine $Q/hover_34.mp4 $Q/table_up_34.mp4 $P/combined_post_3x4.mp4
  stamp "combined cuts" $(( $(date +%s) - t0 ))
  t0=$(date +%s)
  $FF -y -loglevel error -ss 7.0 -i $P/full_table_up_post.mp4 -frames:v 1 -q:v 2 $P/full_table_up_post_poster.jpg
  $FF -y -loglevel error -ss 5.0 -i $P/combined_post.mp4 -frames:v 1 -q:v 2 $P/combined_post_poster.jpg
  $FF -y -loglevel error -ss 5.0 -i $P/combined_post_3x4.mp4 -frames:v 1 -q:v 2 $P/combined_post_3x4_poster.jpg
  # motion check: a frame every 0.5 s through the whole of each clip (the transition is at 8.5 to 9 s of the combined
  # cuts, the touchdown about 10 s into the table part), as one contact sheet per clip plus single frames
  for c in full_table_up_post combined_post combined_post_3x4; do
    $FF -y -loglevel error -i $P/$c.mp4 -vf "fps=2,scale=480:-1,tile=8x7" -frames:v 1 -q:v 3 $P/frames_post/${c}_sheet_0p5s.jpg
    $FF -y -loglevel error -i $P/$c.mp4 -vf "fps=2" -q:v 3 $P/frames_post/${c}_%03d.jpg
  done
  stamp "posters and motion check frames" $(( $(date +%s) - t0 ))
  for c in full_table_up_post combined_post combined_post_3x4; do
    $FP -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt:format=duration,size -of default=nw=1 $P/$c.mp4 | tr '\n' ' '; echo $c
  done
  echo POSTDONE
fi
