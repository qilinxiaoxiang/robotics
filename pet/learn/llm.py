"""One structured-JSON call to a language model, with token and cost accounting.

Backends, picked by `backend=` or PET_LLM_BACKEND (default "auto"):
  api     Anthropic Messages API through the `anthropic` SDK (needs ANTHROPIC_API_KEY or an
          `ant auth login` profile). Structured output via output_config.format json_schema.
          Opus/Sonnet calls carry the server-side refusal fallback (fallbacks="default").
  cli     The Claude Code CLI (`claude -p --json-schema`), which bills the owner's Claude
          subscription; tools, settings, hooks and MCP are all disabled so the pet's prompt
          is the whole context.
  ollama  A local Ollama server (PET_OLLAMA_URL, default http://localhost:11434), JSON format.
  auto    api if a key is present, else cli if the binary exists, else raise LLMUnavailable.

Every call appends one line to pet/learn/out/llm_costs.jsonl (or PET_LLM_COST_LOG).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

FRONTIER_MODEL = os.environ.get("PET_REFLECT_MODEL", "claude-opus-5-5")
SMALL_MODEL = os.environ.get("PET_SMALL_MODEL", "claude-haiku-5-5")

# USD per million tokens (Anthropic first-party list prices, read 2026-10-26 from the
# claude-api skill's model table, cached 2026-10-06). Haiku 5.5 price holds for prompts <= 100K.
PRICES = {
    "claude-opus-5-5": {"in": 4.00, "out": 20.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cache_read": 0.20},
    "claude-haiku-5-5": {"in": 0.10, "out": 0.50, "cache_read": 0.01},
    "claude-fable-5-1": {"in": 10.00, "out": 50.00, "cache_read": 0.25},
}

REPO = Path(__file__).resolve().parents[2]
COST_LOG = Path(os.environ.get("PET_LLM_COST_LOG", REPO / "pet" / "learn" / "out" / "llm_costs.jsonl"))


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class Usage:
    model: str
    backend: str
    purpose: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    cost_basis: str = "list price"
    seconds: float = 0.0


def price(model: str, inp: int, out: int, cache_read: int = 0, cache_write: int = 0) -> float:
    p = PRICES.get(model)
    if p is None:
        return 0.0
    return (inp * p["in"] + out * p["out"] + cache_read * p["cache_read"] + cache_write * p["in"] * 1.25) / 1e6


def _log(u: Usage, note: str = "") -> None:
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG.open("a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **asdict(u), "note": note}) + "\n")


def _has_api_credentials() -> bool:
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    return Path.home().joinpath(".config", "anthropic").exists()


def _cli_path() -> str | None:
    p = Path.home() / ".local" / "bin" / "claude"
    return str(p) if p.exists() else shutil.which("claude")


def available_backend(preferred: str | None = None) -> str | None:
    b = preferred or os.environ.get("PET_LLM_BACKEND", "auto")
    if b != "auto":
        return b
    if _has_api_credentials():
        return "api"
    if _cli_path():
        return "cli"
    return None


def call_json(system: str, user: str, schema: dict, *, model: str, purpose: str,
              backend: str | None = None, effort: str | None = None,
              max_tokens: int = 16000, budget_usd: float = 2.0) -> tuple[dict, Usage]:
    b = available_backend(backend)
    if b is None:
        raise LLMUnavailable("no ANTHROPIC_API_KEY, no ant profile and no claude CLI")
    t0 = time.time()
    if b == "api":
        data, u = _call_api(system, user, schema, model, purpose, effort, max_tokens)
    elif b == "cli":
        data, u = _call_cli(system, user, schema, model, purpose, effort, budget_usd)
    elif b == "ollama":
        data, u = _call_ollama(system, user, schema, model, purpose)
    else:
        raise ValueError(f"unknown backend {b}")
    u.seconds = round(time.time() - t0, 2)
    _log(u)
    return data, u


def _call_api(system, user, schema, model, purpose, effort, max_tokens):
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise LLMUnavailable("pip install anthropic") from e
    client = anthropic.Anthropic()
    kwargs = dict(
        model=model, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema},
                       **({"effort": effort} if effort else {})},
    )
    if model.startswith(("claude-opus-5", "claude-fable-5", "claude-sonnet-5-5")):
        resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    else:
        resp = client.messages.create(**kwargs)
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {getattr(resp, 'stop_details', None)}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("model hit max_tokens before finishing the JSON")
    text = next(b.text for b in resp.content if b.type == "text")
    u = resp.usage
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    used_model = getattr(resp, "model", model) or model
    usage = Usage(used_model, "api", purpose, u.input_tokens, u.output_tokens, cr, cw,
                  round(price(used_model, u.input_tokens, u.output_tokens, cr, cw), 5))
    return json.loads(text), usage


def _call_cli(system, user, schema, model, purpose, effort, budget_usd):
    exe = _cli_path()
    if not exe:
        raise LLMUnavailable("claude CLI not found")
    cmd = [exe, "-p", "--model", model, "--output-format", "json",
           "--json-schema", json.dumps(schema), "--system-prompt", system,
           "--tools", "", "--setting-sources", "", "--strict-mcp-config",
           "--disable-slash-commands", "--no-session-persistence",
           "--max-budget-usd", str(budget_usd)]
    if effort:
        cmd += ["--effort", effort]
    # Run from a neutral directory so no project CLAUDE.md is picked up.
    cwd = Path(os.environ.get("TMPDIR", "/tmp"))
    out = subprocess.run(cmd, input=user, capture_output=True, text=True, timeout=900, cwd=cwd)
    if out.returncode != 0 and not out.stdout.strip():
        raise RuntimeError(f"claude CLI failed: {out.stderr[-800:]}")
    res = json.loads(out.stdout)
    if res.get("is_error") or res.get("subtype") != "success":
        raise RuntimeError(f"claude CLI error: {res.get('subtype')} {str(res.get('result'))[:400]}")
    data = res.get("structured_output")
    if data is None:
        data = json.loads(res["result"])
    mu = (res.get("modelUsage") or {}).get(model) or {}
    u = res.get("usage") or {}
    usage = Usage(model, "cli", purpose,
                  int(mu.get("inputTokens", u.get("input_tokens", 0))),
                  int(mu.get("outputTokens", u.get("output_tokens", 0))),
                  int(mu.get("cacheReadInputTokens", u.get("cache_read_input_tokens", 0))),
                  int(mu.get("cacheCreationInputTokens", u.get("cache_creation_input_tokens", 0))),
                  round(float(res.get("total_cost_usd", 0.0)), 5),
                  "list-price equivalent reported by the CLI; billed to the subscription")
    return data, usage


def _call_ollama(system, user, schema, model, purpose):
    url = os.environ.get("PET_OLLAMA_URL", "http://localhost:11434") + "/api/chat"
    body = json.dumps({"model": model, "stream": False, "format": schema,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, body, {"Content-Type": "application/json"}), timeout=120) as r:
            res = json.loads(r.read())
    except OSError as e:
        raise LLMUnavailable(f"ollama not reachable at {url}: {e}") from e
    usage = Usage(model, "ollama", purpose, int(res.get("prompt_eval_count", 0)), int(res.get("eval_count", 0)),
                  cost_basis="local, no charge")
    return json.loads(res["message"]["content"]), usage


# A model function signature that tests and offline runs can replace.
ModelFn = Callable[..., tuple[dict, Usage]]
