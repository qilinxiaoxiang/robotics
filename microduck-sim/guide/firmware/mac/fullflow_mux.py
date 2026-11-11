"""Add the sound track to a fullflow_sim.py video: the owner's two lines (macOS `say`, voice Samantha), the duck's
answer (one simulator chirp, Pollen's duck1/chirp_a.wav, which the robot's call set is built from) and a closing
"Good job, Mochi!", each placed at its event time from the run's events JSON (video time = sim time).

  python3 fullflow_mux.py VIDEO.mp4 EVENTS.json OUT.mp4
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHIRP = os.path.join(HERE, "..", "..", "..", "microduck-simulator", "app", "public", "assets", "voices", "duck1",
                     "chirp_a.wav")


def main(video, events, out):
    ev = {e["ev"]: e["t"] for e in json.load(open(events))["events"]}
    tmp = tempfile.mkdtemp(prefix="fullflow_mux_")
    lines = [("mochi", "Mochi!", ev["call"]), ("cmd", "Mochi, go find the orange ball!", ev["command"])]
    if "beak_open" in ev:
        lines.append(("good", "Good job, Mochi!", ev["beak_open"] + 1.0))
    inputs, filters = [], []
    for k, (name, text, t) in enumerate(lines):
        path = os.path.join(tmp, name + ".aiff")
        subprocess.run(["say", "-v", "Samantha", "-o", path, text], check=True)
        inputs += ["-i", path]
        filters.append(f"[{k + 1}:a]aresample=44100,adelay={int(t * 1000)}|{int(t * 1000)},volume=1.6[a{k}]")
    n = len(lines)
    inputs += ["-i", CHIRP]
    q = ev["quack"] + 0.15
    filters.append(f"[{n + 1}:a]aresample=44100,adelay={int(q * 1000)}|{int(q * 1000)},volume=2.5[a{n}]")
    mix = "".join(f"[a{k}]" for k in range(n + 1))
    filters.append(f"{mix}amix=inputs={n + 1}:normalize=0,apad[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video] + inputs +
                   ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", out], check=True)
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
