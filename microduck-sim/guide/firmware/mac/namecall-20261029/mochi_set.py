"""Clips for tuning and judging the "Mochi" keyword spotter (namecall.py --name mochi): macOS `say` voices only, the
audio stays outside git (--out). Mono 16-bit 48 kHz wavs plus manifest.json with each clip's kind, voice, text, and
the speech start and end inside the clip (energy, 40 dB under the clip's peak).

  /usr/bin/python3 mochi_set.py --out DIR            # about 4 minutes on the M1 Pro; nothing here needs numpy

Kinds:
  pos         "Mochi" in English voices and Chinese voices (Chinese voices read the Latin name, so their accent is
              the synthesiser's), alone and in short phrases; mochi_last marks clips where the name is the last word
              (the latency from the end of the name is measured on those)
  pos_zh      Chinese spellings of the sound (莫奇, 摩奇) in Chinese voices: what a Chinese speaker's "Mochi" may sound like
  neg_word    other words and short phrases, English and Chinese, chosen to sound like the name (motion, Mickey, much,
              mocha, moshi moshi, 年糕, 默契, 抹茶, 米奇, 墨迹 ...) and everyday ones (我去, 没事, come here ...)
  speech      long paragraphs of everyday speech (written for this file, no name in them), English and Chinese, for
              the false-alarm rate per hour
The duck's own calls and claps are not made here: kws_mochi_eval.py takes the calls from pet/express (the same
recordings and variants the robot plays) and synthesises claps.
"""
import argparse
import json
import os
import subprocess
import sys
import wave
from array import array

EN_VOICES = ["Samantha", "Daniel (English (UK))", "Karen", "Moira (English (Ireland))", "Rishi (English (India))",
             "Tessa (English (South Africa))", "Fred", "Eddy (English (US))", "Flo (English (UK))", "Reed (English (US))",
             "Sandy (English (UK))", "Shelley (English (US))", "Grandma (English (US))", "Grandpa (English (UK))",
             "Rocko (English (US))", "Aman", "Kathy", "Ralph"]
ZH_VOICES = ["Tingting (Chinese (China mainland))", "Meijia", "Sinji", "Eddy (Chinese (China mainland))",
             "Flo (Chinese (China mainland))", "Reed (Chinese (Taiwan))", "Sandy (Chinese (China mainland))",
             "Shelley (Chinese (Taiwan))", "Grandpa (Chinese (China mainland))", "Rocko (Chinese (China mainland))"]

POS_EN = [("Mochi", True), ("Mochi!", True), ("Mochi?", True), ("Hey Mochi", True), ("Come here, Mochi", True),
          ("Mochi, come here", False), ("Mochi, look at me", False)]
POS_ZH = [("Mochi", True), ("Mochi!", True), ("Mochi，过来", False), ("过来，Mochi", True), ("嘿，Mochi", True)]
POS_ZH_PHON = [("莫奇", True), ("莫奇！", True), ("摩奇，过来", False)]
RATES = (None, 140, 220)          # say's default rate, slow, fast (rates only for the bare name)

NEG_EN = ["motion", "Mickey", "much", "mocha", "macho", "mojo", "Moji", "monkey", "Michelle", "moshi moshi", "kimchi",
          "sushi", "peachy", "matcha", "Mo", "mostly", "mommy", "nachos", "my cheese", "more cheese", "Hey Siri",
          "Alexa", "OK Google", "good morning", "come here", "look at me", "hey you", "what's that", "go to sleep",
          "good boy", "much better", "no cheating", "mojito", "Moe's cheesy fries", "touch it"]
NEG_ZH = ["年糕", "我去", "没事", "默契", "抹茶", "米奇", "墨迹", "摸摸", "猫咪", "过来", "你好", "吃饭了吗", "魔术", "麻薯",
          "模式", "好的", "走吧", "小鸭子", "没事吧", "我去吃饭"]
NEG_EN_VOICES = EN_VOICES[::2]
NEG_ZH_VOICES = ZH_VOICES[::2]

SPEECH_EN = """The weather today is mild with a light wind from the west, and the forecast says rain after six.
I left the keys on the kitchen table next to the blue cup. Could you check whether the printer on the fourth floor has paper?
We moved the meeting to Thursday because half of the team is travelling. The bus was late again so I walked the last mile.
My sister started a new job at a bakery downtown and she loves the early mornings. Please remember to water the plants on the balcony.
The motion sensor in the hallway keeps turning the light on at night. Mickey said he would bring the cables tomorrow.
That is much better than the first version, but the handle is still too loose. I would like a mocha with oat milk, please.
The library closes at nine on weekdays and at five on Sunday. He was a little too macho about lifting the heavy box alone.
Let us try the soldering again with a cleaner tip and some fresh flux. The robot fell over twice, so we lowered the gains.
Do you want to get noodles or dumplings for dinner tonight? I think the battery needs another hour on the charger.
The children played in the park until the street lights came on. She wrote the numbers on a sticky note and lost it.
Our neighbour has a small dog that barks at every delivery truck. The train to Philadelphia leaves from platform three.
If the camera cable snags again, route it behind the shoulder bracket. I finished the report, but the charts still need labels.
The soup needs more salt and maybe a little pepper. We counted forty two screws, two short of the list.
Turn left at the bakery and the post office is on your right. The concert was loud, crowded, and absolutely wonderful.
I am going to the hardware store, do you need anything? The kitten fell asleep on the warm laptop again.
Most of the snow melted by noon, but the steps are still slippery. Thank you for waiting, the doctor will see you now.
Could you hand me the small screwdriver with the red handle? The project review is moved to next Monday morning.
He keeps a notebook full of sketches of birds and bridges. My phone battery dies faster since the last update.
We should paint the fence before the weather turns cold. The museum has a new exhibit about early flying machines.
Moshi moshi is how people answer the phone in Japanese. Kimchi and sushi were both on the lunch menu today.
I need a moment to think about it before I say yes. The coffee machine is broken so we are drinking tea all week.
Put the heavy books on the bottom shelf and the photos on top. Are you coming to the barbecue on Saturday afternoon?
The lecture covered motion planning, sensor noise, and a little bit of control theory. Much of the code is older than the robot.
Let me know when the package arrives, it should be here by Friday. The garden looks lovely after all that rain.""".split("\n")

SPEECH_ZH = """今天天气不错，下午可能会有点小雨。我把钥匙放在厨房的桌子上了。
你帮我看一下四楼的打印机还有没有纸。会议改到星期四了，因为一半的人在出差。
公交车又晚点了，我只好走了最后一段路。我姐姐在市中心的一家面包店找了新工作。
请记得给阳台上的花浇水。走廊里的感应灯晚上老是自己亮。这个版本比第一个好多了，不过把手还是有点松。
图书馆工作日晚上九点关门，星期天五点关门。我们再焊一次吧，烙铁头要先清理干净。
机器人摔倒了两次，所以我们把增益调低了。今天晚上你想吃面条还是饺子？
电池还需要再充一个小时。孩子们在公园里玩到路灯亮起来才回家。我去超市买点东西，你要带什么吗？
没事，慢慢来，不着急。我们俩配合得很有默契。这个蛋糕上面撒了一层抹茶粉。
过年的时候家里会做年糕。小朋友最喜欢米奇和唐老鸭。你别墨迹了，快点出门吧。
猫咪在笔记本电脑上睡着了。隔壁的小狗看见快递车就叫。去费城的火车从三号站台出发。
汤里再加一点盐，可能还要一点胡椒。我们数了一下，螺丝一共四十二颗，比清单少两颗。
在面包店那里左转，邮局就在右边。音乐会又吵又挤，但是特别好听。
麻薯是用糯米做的，软软的很好吃。这个魔术太厉害了，我完全没看出来。
你先把重的书放在最下面一层，照片放在最上面。周六下午你来不来烧烤？
快递应该星期五之前到，到了告诉我一声。下了这么多雨，花园看起来特别漂亮。
我想先想一想再回答你。咖啡机坏了，我们这个星期都喝茶。""".split("\n")
SPEECH_EN_VOICES = ["Samantha", "Daniel (English (UK))", "Karen", "Rishi (English (India))", "Fred",
                    "Shelley (English (US))", "Grandpa (English (UK))"]
SPEECH_ZH_VOICES = ["Tingting (Chinese (China mainland))", "Meijia", "Sinji", "Reed (Chinese (Taiwan))"]


def say(text, voice, path, rate=None):
    cmd = ["say", "-v", voice, "--data-format=LEI16@48000", "-o", path]
    if rate:
        cmd += ["-r", str(rate)]
    subprocess.run(cmd + [text], check=True)


def speech_span(path, rel_db=40.0):
    """(start, end) seconds of the part within rel_db of the clip's loudest 10 ms frame."""
    with wave.open(path) as w:
        fs, n = w.getframerate(), w.getnframes()
        x = array("h", w.readframes(n))
    hop = fs // 100
    e = [sum(v * v for v in x[i:i + hop]) / hop for i in range(0, len(x) - hop + 1, hop)]
    top = max(e) if e else 0
    if top <= 0:
        return 0.0, 0.0
    on = [i for i, v in enumerate(e) if v >= top * 10 ** (-rel_db / 10)]
    return round(on[0] * hop / fs, 3), round((on[-1] + 1) * hop / fs, 3)


def slug(s):
    return "".join(c if c.isalnum() else "_" for c in s.split(" (")[0])[:24]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = []

    def add(kind, text, voice, rate=None, mochi_last=None, group=None):
        name = f"{kind}_{len(rows):04d}_{slug(voice)}_{rate or 'd'}.wav"
        p = os.path.join(a.out, name)
        if not os.path.exists(p):
            say(text, voice, p, rate)
        s, e = speech_span(p)
        rows.append(dict(file=name, kind=kind, text=text, voice=voice, accent="zh" if voice in ZH_VOICES else "en",
                         rate=rate, mochi_last=mochi_last, group=group, speech_start=s, speech_end=e))
        sys.stdout.write(".")
        sys.stdout.flush()

    for vi, v in enumerate(EN_VOICES):
        for text, last in POS_EN:
            for r in (RATES if text == "Mochi" else (None,)):
                add("pos", text, v, r, last, "tune" if vi % 2 == 0 else "test")
    for vi, v in enumerate(ZH_VOICES):
        for text, last in POS_ZH:
            for r in (RATES if text == "Mochi" else (None,)):
                add("pos", text, v, r, last, "tune" if vi % 2 == 0 else "test")
        for text, last in POS_ZH_PHON:
            add("pos_zh", text, v, None, last, "tune" if vi % 2 == 0 else "test")
    for v in NEG_EN_VOICES:
        for text in NEG_EN:
            add("neg_word", text, v)
    for v in NEG_ZH_VOICES:
        for text in NEG_ZH:
            add("neg_word", text, v)
    for i, v in enumerate(SPEECH_EN_VOICES):
        lines = SPEECH_EN[i % 3::1] if i % 2 == 0 else SPEECH_EN[::-1]
        add("speech", " ".join(l.strip() for l in lines if l.strip()), v)
    for i, v in enumerate(SPEECH_ZH_VOICES):
        lines = SPEECH_ZH if i % 2 == 0 else SPEECH_ZH[::-1]
        add("speech", "".join(l.strip() for l in lines if l.strip()), v)
    json.dump(rows, open(os.path.join(a.out, "manifest.json"), "w"), ensure_ascii=False, indent=0)
    print(f"\n{len(rows)} clips in {a.out}")


if __name__ == "__main__":
    main()
