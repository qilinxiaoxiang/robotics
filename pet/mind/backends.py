"""Model backends for the intention layer. Each returns (text, usage) where usage holds input_tokens,
output_tokens, latency_s and, when known, the provider's own cost. Every call is appended to a CallLog.

- AnthropicBackend: Messages API, claude-haiku-5-5, official SDK, key from the usual Anthropic credential chain.
- ClaudeCliBackend: the same model through `claude -p` on the user's Claude subscription (no API key needed); the
  CLI adds its own ~0.7k tokens of framing, which the log records separately.
- OllamaBackend: a local model (Qwen 7B class) over Ollama's HTTP API, e.g. on the Mac mini.
- ScriptedBackend: canned answers for tests (never calls anything).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

HAIKU = "claude-haiku-5-5"
# Claude Haiku 5.5 list price, USD per million tokens (claude-api skill table, cached 2026-10-06).
HAIKU_IN_PER_MTOK, HAIKU_OUT_PER_MTOK = 0.10, 0.50


class BackendError(RuntimeError):
    pass


def api_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """What the call would cost on the API at Haiku 5.5 list price with no prompt caching."""
    return input_tokens * HAIKU_IN_PER_MTOK / 1e6 + output_tokens * HAIKU_OUT_PER_MTOK / 1e6


class CallLog:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else None
        self.calls: list[dict] = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("")

    def add(self, rec: dict):
        self.calls.append(rec)
        if self.path:
            with self.path.open("a") as f:
                f.write(json.dumps(rec) + "\n")

    def summary(self) -> dict:
        ok = [c for c in self.calls if c.get("ok")]
        lat = sorted(c["latency_s"] for c in self.calls if "latency_s" in c)
        tot = lambda k: sum(c.get(k, 0) or 0 for c in self.calls)
        return {"calls": len(self.calls), "ok": len(ok), "input_tokens": tot("input_tokens"),
                "output_tokens": tot("output_tokens"), "api_cost_usd": round(tot("api_cost_usd"), 5),
                "provider_cost_usd": round(tot("provider_cost_usd"), 5),
                "latency_p50_s": lat[len(lat) // 2] if lat else None,
                "latency_p90_s": lat[int(len(lat) * 0.9)] if lat else None}


class AnthropicBackend:
    name = "anthropic"

    def __init__(self, model=HAIKU, max_tokens=1024, effort="low"):
        import anthropic  # optional dependency; only needed for this backend
        self.client = anthropic.Anthropic()
        self.model, self.max_tokens, self.effort = model, max_tokens, effort

    def ask(self, system: str, user: str) -> tuple[str, dict]:
        t0 = time.monotonic()
        try:
            msg = self.client.messages.create(model=self.model, max_tokens=self.max_tokens, system=system,
                                              messages=[{"role": "user", "content": user}],
                                              output_config={"effort": self.effort})
        except Exception as e:  # network, auth, rate limit: the mind falls back
            raise BackendError(f"{type(e).__name__}: {e}") from e
        if msg.stop_reason == "refusal":
            raise BackendError("refusal")
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        u = msg.usage
        inp = (u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0) + \
              (getattr(u, "cache_creation_input_tokens", 0) or 0)
        return text, {"input_tokens": inp, "output_tokens": u.output_tokens, "latency_s": time.monotonic() - t0}


class ClaudeCliBackend:
    """claude -p with tools, settings and MCP off and our own system prompt: one model call, subscription billing."""
    name = "claude-cli"

    def __init__(self, model=HAIKU, effort="low", timeout_s=60):
        exe = shutil.which("claude")
        if not exe:
            raise BackendError("claude CLI not found")
        self.exe, self.model, self.effort, self.timeout_s = exe, model, effort, timeout_s

    def ask(self, system: str, user: str) -> tuple[str, dict]:
        cmd = [self.exe, "-p", "--model", self.model, "--effort", self.effort, "--tools", "", "--setting-sources", "",
               "--strict-mcp-config", "--no-session-persistence", "--output-format", "json",
               "--system-prompt", system, user]
        t0 = time.monotonic()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_s, cwd="/tmp",
                               env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "pet-mind"})
            d = json.loads(r.stdout)
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            raise BackendError(f"claude CLI: {e}") from e
        if d.get("is_error") or d.get("subtype") not in (None, "success"):
            raise BackendError(f"claude CLI: {str(d.get('result'))[:200]}")
        u = d.get("usage", {})
        inp = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + \
              (u.get("cache_creation_input_tokens") or 0)
        return d.get("result", ""), {"input_tokens": inp, "output_tokens": u.get("output_tokens") or 0,
                                     "latency_s": time.monotonic() - t0,
                                     "api_latency_s": (d.get("duration_api_ms") or 0) / 1000,
                                     "provider_cost_usd": d.get("total_cost_usd")}


class OllamaBackend:
    name = "ollama"

    def __init__(self, model="qwen2.5:7b-instruct", url=None, timeout_s=60):
        self.model = model
        self.url = (url or os.environ.get("PET_OLLAMA_URL", "http://mac-mini:11434")).rstrip("/")
        self.timeout_s = timeout_s

    def ask(self, system: str, user: str) -> tuple[str, dict]:
        body = json.dumps({"model": self.model, "stream": False, "format": "json", "options": {"temperature": 0.8},
                           "messages": [{"role": "system", "content": system},
                                        {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(self.url + "/api/chat", data=body, headers={"Content-Type": "application/json"})
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                d = json.loads(r.read())
        except (OSError, ValueError) as e:
            raise BackendError(f"ollama at {self.url}: {e}") from e
        return d.get("message", {}).get("content", ""), {
            "input_tokens": d.get("prompt_eval_count", 0), "output_tokens": d.get("eval_count", 0),
            "latency_s": time.monotonic() - t0, "provider_cost_usd": 0.0}


class ScriptedBackend:
    """Test double: returns the queued answers in order (a str, or an Exception to raise)."""
    name = "scripted"

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def ask(self, system: str, user: str) -> tuple[str, dict]:
        self.prompts.append((system, user))
        a = self.answers.pop(0) if self.answers else BackendError("no more answers")
        if isinstance(a, Exception):
            raise a
        return a, {"input_tokens": len((system + user).split()), "output_tokens": len(a.split()), "latency_s": 0.0}


def make_backend(name: str):
    if name in ("anthropic", "api"):
        return AnthropicBackend()
    if name in ("claude-cli", "cli"):
        return ClaudeCliBackend()
    if name == "ollama":
        return OllamaBackend()
    if name in ("fallback", "none", "offline"):
        return None
    raise ValueError(f"unknown backend {name}")


def parse_json_answer(text: str):
    """The first JSON object in the text (models sometimes wrap it in a code fence)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    start = t.find("{")
    if start < 0:
        raise ValueError("no JSON object in the answer")
    obj, _ = json.JSONDecoder().raw_decode(t[start:])
    return obj
