"""The intention-layer prompt. The system part is fixed per body (cacheable); the user part is the moment."""
from __future__ import annotations

from .body import BodyCard

SYSTEM_TEMPLATE = """You are the intention layer of a small companion pet robot that never speaks. Every 10-30 seconds you choose what the pet does next, as a short sequence of the body's actions.

The pet should feel alive: follow its drives and mood, react to what just happened, use what it remembers (rules, diary, plan), and keep varying what it does. A dumb choice is fine; doing the same thing again and again is not. Look at the recent behaviour and pick something that fits but differs, unless continuing is clearly right (sleeping, waiting at the door for the owner).

Body: {name}. Senses: {senses}. {mobility}
Actions (only these, numeric params inside the ranges, posture preconditions must hold at that step; an action's 'then posture' changes the posture for the next steps):
{actions}
{skills}
Conditions use this grammar: standing, sitting, lying, owner_visible, owner_home, stranger_present, touched (each may be prefixed with "not "), or battery/tired/bored/miss_owner/curious/hour followed by < <= > >= and a number.

Answer with exactly one JSON object and nothing else:
{{"intention_text": "<first person, under 15 words, what and why>", "steps": [{{"primitive": "<action or skill>", "params": {{"<param>": <number>}}}}], "duration_s": <5-30, total seconds>, "abort_if": ["<condition>"], "mood_note": "<two or three words>"}}
1-6 steps. Steps run in order and must fit in duration_s."""


def system_prompt(body: BodyCard, skills: dict) -> str:
    senses = ", ".join(sorted(k for k in body.sensor_kinds if k)) or "none"
    if body.can_locomote:
        mobility = "It can walk around the home."
    else:
        mobility = (f"It cannot move from its place ({body.fixed_location or 'fixed'}): it never goes anywhere, it "
                    "only turns, gestures and looks, and intention_text must say only that. It perceives nothing "
                    "outside its senses.")
    if body.failed:
        mobility += f" Failed joints: {', '.join(body.failed)}."
    actions = "\n".join(f"- {a}" for a in body.describe_primitives())
    sk = ""
    if skills:
        lines = [f"- {n}: {' -> '.join(s['primitive'] for s in v['steps'])}"
                 + (f" (only if {', '.join(v.get('guards', []))})" if v.get("guards") else "")
                 for n, v in skills.items()]
        sk = "Skills (call like an action, no params):\n" + "\n".join(lines) + "\n"
    return SYSTEM_TEMPLATE.format(name=body.name, senses=senses, mobility=mobility, actions=actions, skills=sk)


def user_prompt(ctx: dict) -> str:
    """ctx is built by Mind.context(); every value is already short text."""
    lines = [f"Time {ctx['clock']} ({ctx['period']}). Posture: {ctx['posture']}. Location: {ctx['room']}.",
             f"World: {ctx['world']}",
             f"Drives 0-1: {ctx['drives']}. Mood: {ctx['mood']}."]
    lines.append("Recent events (oldest first): " + ("; ".join(ctx["events"]) or "nothing new"))
    lines.append("Your last 5 min: " + ("; ".join(ctx["behaviour"]) or "nothing yet"))
    if ctx.get("situation"):
        lines.append("Your situation: " + ctx["situation"])
    if ctx.get("interrupted"):
        lines.append(f"Interrupted: {ctx['interrupted']}")
    if ctx.get("plan"):
        lines.append("Today's plan: " + "; ".join(ctx["plan"]))
    if ctx.get("rules"):
        lines.append("What you have learned: " + "; ".join(ctx["rules"]))
    if ctx.get("personality"):
        lines.append("Personality: " + ctx["personality"])
    if ctx.get("diary"):
        lines.append("Memories: " + "; ".join(ctx["diary"]))
    if ctx.get("error"):
        lines.append(f"Your previous answer was rejected: {ctx['error']} Answer again with valid JSON.")
    lines.append("What does the pet do next?")
    return "\n".join(lines)
