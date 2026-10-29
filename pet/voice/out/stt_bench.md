# STT benchmark 2026-10-29 04:04

Host: xiangzhengdeMacBook-Pro.local (arm64), 4 threads, 20 synthetic clips (macOS say: Samantha en, Tingting zh). Error rate: WER for English, CER for Chinese.

- **local:sense-voice** (load 2.04 s): en 10.7% error, 7/10 exact, latency median 0.186 s max 0.415 s; zh 6.2% error, 8/10 exact, latency median 0.114 s max 0.226 s; all 8.3% error, 15/20 exact, latency median 0.147 s max 0.415 s
- **local:whisper-base** (load 1.43 s): en 3.6% error, 9/10 exact, latency median 0.524 s max 2.317 s; zh 75.0% error, 3/10 exact, latency median 0.293 s max 0.354 s; all 41.7% error, 12/20 exact, latency median 0.312 s max 2.317 s
- **elevenlabs**: 401 invalid_api_key (tried en01); not scored.
- **chain:listen+local:sense-voice**: en 10.7% error, 7/10 exact, latency median 0.136 s max 0.413 s; zh 15.6% error, 8/10 exact, latency median 0.171 s max 0.384 s; all 13.3% error, 15/20 exact, latency median 0.136 s max 0.413 s

Chosen local default: **sense-voice** (lowest overall error 8.3% at median 0.147 s; local:whisper-base 41.7% / 0.312 s)

## Per clip (chosen model)

- ERR en01 0.41 s  ref `Fetch the orange block.`  hyp `Fedch the orange block.`
- ok  en02 0.10 s  ref `Come here.`  hyp `Come here.`
- ok  en03 0.24 s  ref `Sit down.`  hyp `Sit down.`
- ok  en04 0.17 s  ref `Stop.`  hyp `Stop.`
- ok  en05 0.17 s  ref `Stay out of the bedroom.`  hyp `Stay out of the bedroom.`
- ERR en06 0.09 s  ref `Good duck.`  hyp `Good dog.`
- ok  en07 0.26 s  ref `Look at me.`  hyp `Look at me.`
- ok  en08 0.20 s  ref `Turn around.`  hyp `Turn around.`
- ERR en09 0.11 s  ref `Open your beak.`  hyp `Open your be.`
- ok  en10 0.41 s  ref `Walk forward a little.`  hyp `Walk forward a little.`
- ERR zh01 0.14 s  ref `把橙色方块叼来。`  hyp `把橙色方块雕来。`
- ok  zh02 0.05 s  ref `过来。`  hyp `过来。`
- ok  zh03 0.04 s  ref `坐下。`  hyp `坐下。`
- ok  zh04 0.16 s  ref `停。`  hyp `停。`
- ERR zh05 0.10 s  ref `别进卧室。`  hyp `边进卧室。`
- ok  zh06 0.12 s  ref `好鸭子。`  hyp `好鸭子。`
- ok  zh07 0.15 s  ref `看着我。`  hyp `看着我。`
- ok  zh08 0.05 s  ref `转个身。`  hyp `转个身。`
- ok  zh09 0.11 s  ref `张嘴。`  hyp `张嘴。`
- ok  zh10 0.23 s  ref `往前走一点。`  hyp `往前走一点。`
