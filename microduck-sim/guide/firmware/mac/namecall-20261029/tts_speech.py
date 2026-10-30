"""Synthetic everyday speech (no name in it) in every voice that reads the synthetic "Mochi" positives of mochi_set.py,
for train_mochi.py --tts-speech: with these as negatives a synthetic voice alone cannot be the cue for Mochi. The
texts differ from mochi_set.py's SPEECH_EN / SPEECH_ZH, which stay the held-out false-wake test.

  python3 tts_speech.py --out <folder>     # about 15 min of speech, a manifest.json beside the clips
"""
import argparse
import json
import os
import random
import subprocess
from concurrent.futures import ThreadPoolExecutor

from mochi_set import EN_VOICES, ZH_VOICES, slug

TEXT_EN = """Can you pass me the charger, the one with the long cable?
I think we should leave a little earlier tomorrow because of the traffic.
The motor is getting warm, let it rest for a few minutes.
She ordered a matcha latte and a slice of cheesecake.
Who left the window open in the workshop last night?
My mom called and asked if we are coming home for the holidays.
The macro in the spreadsheet stopped working after the update.
We need more zip ties, the small black ones.
Hey, come over here and look at this, it finally works.
I am not sure, maybe we should ask the teaching assistant.
The robot is walking much more smoothly than yesterday.
Mickey Mouse was on the poster in the hallway.
Let me grab my jacket, it is getting cold outside.
How much did the new battery cost in the end?
Moving the sensor a bit higher should fix the reflection problem.
Okay, everyone, let us start the meeting, we have a lot to cover.
The microwave beeped three times but the food is still cold.
I really like the music they are playing in here.
Can you hear me? The connection keeps dropping.
Good morning, did you sleep well?
Mochas are too sweet for me, I prefer plain coffee.
We moved the printer to the corner next to the window.
That was a nice shot, do it again so I can film it.
My laptop fan is so loud during the training runs.
Let me know if you need help carrying the boxes.
The demo is at four, so we have about two hours left.
Mostly it works, but sometimes it turns the wrong way.
I will be right back, I am just getting some water.
Moshi, moshi, sorry, I thought you were someone else.
Nice job everyone, see you all next week.""".split("\n")

TEXT_ZH = """你帮我把充电器递一下，就是线比较长的那个。
明天我们早点出发吧，路上可能会堵车。
电机有点烫了，先让它休息几分钟。
她点了一杯抹茶拿铁和一块芝士蛋糕。
昨天晚上谁把实验室的窗户开着没关？
我妈打电话问我们放假回不回家。
螺丝不够了，再去拿一包黑色的扎带。
你过来看一下，终于跑通了。
我也不太确定，要不问一下助教吧。
机器人今天走得比昨天稳多了。
外面有点冷，我去拿一下外套。
新电池最后花了多少钱？
把传感器往上挪一点，反光的问题应该就好了。
好了大家，我们开始开会吧，今天事情挺多的。
微波炉响了三声，但是饭还是凉的。
这里放的音乐挺好听的。
你能听见吗？信号老是断。
早上好，昨天睡得怎么样？
摩卡太甜了，我还是喝美式吧。
打印机搬到窗户旁边那个角落了。
刚才那个动作挺好，再来一次我录下来。
训练的时候电脑风扇特别吵。
你要是搬箱子需要帮忙就叫我。
演示是四点，我们大概还有两个小时。
大部分时候没问题，就是偶尔会转错方向。
我马上回来，去接杯水。
不好意思，我还以为你是别人。
没关系，下次注意一点就行。
魔方你会玩吗？我只能拼一面。
大家辛苦了，下周见。""".split("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--lines", type=int, default=8, help="sentences per voice")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rnd = random.Random(0)
    jobs = []
    for v in EN_VOICES + ZH_VOICES:
        bank = TEXT_ZH if v in ZH_VOICES else TEXT_EN
        text = " ".join(rnd.sample(bank, a.lines))
        jobs.append((v, text, os.path.join(a.out, f"speech_train_{len(jobs):03d}_{slug(v)}.wav")))
    # a few English sentences in the Chinese voices too: the Chinese voices read the Latin "Mochi" in the positives
    for v in ZH_VOICES:
        jobs.append((v, " ".join(rnd.sample(TEXT_EN, 3)), os.path.join(a.out, f"speech_train_{len(jobs):03d}_{slug(v)}_en.wav")))

    def run(job):
        v, text, path = job
        if not os.path.exists(path):
            subprocess.run(["say", "-v", v, "--data-format=LEI16@48000", "-o", path, text], check=True)
        return dict(file=os.path.basename(path), voice=v, text=text)

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(run, jobs))
    json.dump(rows, open(os.path.join(a.out, "manifest.json"), "w"), ensure_ascii=False, indent=0)
    print(f"{len(rows)} clips in {a.out}")


if __name__ == "__main__":
    main()
