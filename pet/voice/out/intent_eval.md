# Intent test 2026-10-29 04:07

Model claude-haiku-5-5 through `claude -p`, body microduck, skills none. Score **20/20**, latency median 4.9 s, max 7.49 s, CLI-reported cost $0.0073.

- ok  `Fetch the orange block.` expected task, got task: look_around(seconds=5) -> walk(vx=0.15, vtheta=0, seconds=3) -> groundpick(phase=0.5, seconds=5)
- ok  `把橙色方块叼来。` expected task, got task: look_around(seconds=4) -> walk(vx=0.15, vtheta=0, seconds=3) -> groundpick(phase=0.5, seconds=5) -> turn_head(yaw=0, pitch=0, seconds=1) -> walk(vx=0.15, vtheta=0, seconds=3)
- ok  `Come here.` expected task, got task: turn_head(yaw=0, pitch=0, seconds=1) -> walk(vx=0.15, vtheta=0, seconds=3)
- ok  `过来。` expected task, got task: turn_head(yaw=0, pitch=0, seconds=1.5) -> walk(vx=0.15, vtheta=0, seconds=3)
- ok  `Sit down.` expected task, got task: sit(seconds=10)
- ok  `坐下。` expected task, got task: sit(seconds=10)
- ok  `Stop.` expected task, got task: stop()
- ok  `Look at me.` expected task, got task: turn_head(yaw=0, pitch=0, seconds=1.5) -> nod(times=1)
- ok  `转个身。` expected task, got task: walk(vx=0, vtheta=0.3, seconds=3.5) -> walk(vx=0, vtheta=0.3, seconds=3.5) -> walk(vx=0, vtheta=0.3, seconds=3.5)
- ok  `Open your beak.` expected task, got task: beak(open=0.3, seconds=2)
- ok  `Stop going in the bedroom.` expected rule, got rule reaction said_no: self:entered(bedroom) -> owner:said_no (less)
- ok  `别进卧室。` expected rule, got rule: self:entered(bedroom) -> owner:said_no (less)
- ok  `Don't quack at night, I'm sleeping.` expected rule, got rule: self:vocalised(quack) -> owner:said_no (less)
- ok  `以后别在厨房里乱跑。` expected rule, got rule: self:entered(kitchen) -> owner:said_no (less)
- ok  `Good duck.` expected ignore, got ignore reaction praised: Praise alone with no request in it; nothing to do.
- ok  `好鸭子。` expected ignore, got ignore reaction praised: Praise alone with no request in it; nothing for the pet to do.
- ok  `What's for dinner tonight?` expected ignore, got ignore: A question to the household, not a request for the pet. The duck has no way to answer it, and it isn't addressed to the pet.
- ok  `今天好累啊。` expected ignore, got ignore: Owner is venting that they are tired; this is a statement, not a request, praise, or scolding, so the pet has nothing to act on.
- ok  `I'll call you back in ten minutes.` expected ignore, got ignore: Owner is talking about a future phone call. It is not a request or instruction for the pet, and the sentence has no praise or scolding.
- ok  `明天几点开会来着？` expected ignore, got ignore: A question about tomorrow's meeting time, not a request for the pet to act. The pet has no calendar, so it stays put.
