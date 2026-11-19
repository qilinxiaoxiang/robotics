#!/bin/zsh
# 1080p presentation renders of the three full-sequence clips of render_full_videos.sh: the same runs (same scenario,
# case, seed, fan point and flags), drawn by sim/render_hd.py. Each run's outcome row must equal the recorded row in
# sim/out/pack_visual/full_<scenario>.json, else the script stops (exit 3) before anything is cut from it.
# Run in the flight-20261110 folder on the Mac mini:
#   zsh sim/mini.sh run 'zsh sim/render_full_videos_hd.sh render'    the three clips (FPS=2 for a quick framing test)
#   zsh sim/mini.sh run 'zsh sim/render_full_videos_hd.sh post'      posters, combined cut, check frames
# Wall time per stage: sim/out/pack_visual_hd/stage_times.log
set -e
P=sim/out/pack_visual_hd
REC=sim/out/pack_visual
FF=/opt/homebrew/bin/ffmpeg
FPS=${FPS:-60}
CAP="Simulation (MuJoCo). Hardware not yet flown."
mkdir -p $P $P/frames
LOG=$P/stage_times.log
stamp() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1 wall_s=$2" | tee -a $LOG; }

B=(--case nominal --seed 0 --fan areswei --com-est true --ground-pitch level --takeoff-twr 1.6 --takeoff-ramp 0.1
   --legs handover --cam-follow --still-t -1)
HD=(--video-size 1920x1080 --video-fps $FPS --video-look studio --cam-smooth 0.35 --cam-fovy 30)

if [[ $1 == render ]]; then
  for s in ${=SCENARIOS:-hover table_up table_down}; do
    # hover: front three-quarter view, close. table scenarios: from the floor side (the table never hides the duck),
    # farther back so the table stays in frame.
    # hover looks 0.12 m below the trunk and a little from above, so the shadow on the floor (the height cue) stays in frame
    az=128; dist=1.5; el=-18; dz=-0.12
    [[ $s == table_* ]] && { az=52; dist=2.0; el=-11; dz=0 }
    t0=$(date +%s)
    timeout 1800 $PY sim/flight.py --scenario $s $B $HD --video-caption "$CAP" --cam-az $az --cam-el $el --cam-dist $dist --cam-dz $dz \
      --out $P/full_$s.json --video $P/full_$s.mp4 > $P/full_$s.log
    stamp "render full_$s fps=$FPS" $(( $(date +%s) - t0 ))
    $PY sim/outcome_match.py $REC/full_$s.json $P/full_$s.json | tee -a $LOG
  done
  echo RENDERDONE
fi

if [[ $1 == post ]]; then
  t0=$(date +%s)
  # combined cut: take-off and hover (hover clip, first 9 s), then the whole floor-to-table clip (flight, landing,
  # standing after the fans stop). Plain cut, no effects; the caption is already in the frames.
  $FF -y -loglevel error -i $P/full_hover.mp4 -i $P/full_table_up.mp4 -filter_complex \
    "[0:v]trim=0:9,setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1[v]" -map "[v]" \
    -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -r $FPS -movflags +faststart $P/combined_hover_then_table.mp4
  stamp "combined cut" $(( $(date +%s) - t0 ))
  t0=$(date +%s)
  # posters: one airborne frame per clip
  $FF -y -loglevel error -ss ${POSTER_HOVER:-5.0} -i $P/full_hover.mp4 -frames:v 1 -q:v 2 $P/full_hover_poster.jpg
  $FF -y -loglevel error -ss ${POSTER_UP:-7.0} -i $P/full_table_up.mp4 -frames:v 1 -q:v 2 $P/full_table_up_poster.jpg
  $FF -y -loglevel error -ss ${POSTER_DOWN:-5.0} -i $P/full_table_down.mp4 -frames:v 1 -q:v 2 $P/full_table_down_poster.jpg
  $FF -y -loglevel error -ss ${POSTER_COMBINED:-5.0} -i $P/combined_hover_then_table.mp4 -frames:v 1 -q:v 2 $P/combined_hover_then_table_poster.jpg
  # check frames: six per clip, evenly spaced, the last one near the end
  for c in full_hover full_table_up full_table_down combined_hover_then_table; do
    dur=$(/opt/homebrew/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 $P/$c.mp4)
    for i in 0 1 2 3 4 5; do
      ts=$(echo "$dur $i" | awk '{printf "%.2f", ($1 - 0.2) * $2 / 5}')
      $FF -y -loglevel error -ss $ts -i $P/$c.mp4 -frames:v 1 -q:v 3 $P/frames/${c}_f$i.jpg
    done
  done
  stamp "posters and check frames" $(( $(date +%s) - t0 ))
  for c in full_hover full_table_up full_table_down combined_hover_then_table; do
    /opt/homebrew/bin/ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name:format=duration,size \
      -of default=nw=1 $P/$c.mp4 | tr '\n' ' '; echo $c
  done
  echo POSTDONE
fi
