#!/usr/bin/env python3
"""
AEGIS LLM backends. Every LLM call in the pipeline goes through `call()`, so
each call is logged (prompt hash, model, temperature actually applied, tokens,
cost, latency) to a JSONL file that the paper's cost and repetition numbers
are computed from.

Backends
  claude-cli   `claude -p` headless (uses the logged-in Claude Code account).
               No sampling control: temperature is NOT applied.
  anthropic    Anthropic Messages API (pip install anthropic; credentials from
               ANTHROPIC_API_KEY or an `ant auth login` profile). Temperature is
               applied only on models that accept it (Haiku 4.5 and older);
               Opus 5.5 / Sonnet 5.5 reject non-default sampling parameters.
  openai       Any OpenAI-compatible chat endpoint (vLLM, Ollama, llama.cpp
               server) for open-weight models: --base-url, model name.
               Temperature is applied.

The returned dict always says whether the requested temperature was applied,
so the stratified-temperature claim can be reported honestly per run.
"""
import hashlib
import json
import os
import subprocess
import time
import urllib.request

# models whose API rejects temperature (sampling parameters removed / non-default 400)
NO_TEMPERATURE = ("claude-opus-5", "claude-sonnet-5", "claude-fable-5", "claude-mythos-5",
                  "claude-opus-4-7", "claude-opus-4-8")
LOG_PATH = os.environ.get("AEGIS_LLM_LOG")


class LLMError(RuntimeError):
    pass


def _log(rec):
    path = LOG_PATH or os.environ.get("AEGIS_LLM_LOG")
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")


def _claude_cli(system, prompt, model, temperature, effort, timeout):
    cmd = ["claude", "-p", "--model", model, "--tools", "", "--system-prompt", system,
           "--output-format", "json", "--no-session-persistence", "--setting-sources", ""]
    if effort:
        cmd += ["--effort", effort]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        raise LLMError("claude-cli returned non-JSON (rc=%d): %s" % (r.returncode, (r.stderr or r.stdout)[-800:]))
    if d.get("is_error"):
        raise LLMError("claude-cli error: %s" % str(d.get("result"))[:800])
    u = d.get("usage", {})
    return {"text": d.get("result") or "", "temperature_applied": False,
            "tokens_in": (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
                         + (u.get("cache_creation_input_tokens") or 0),
            "tokens_out": u.get("output_tokens") or 0, "cost_usd": d.get("total_cost_usd")}


def _anthropic(system, prompt, model, temperature, effort, timeout):
    import anthropic
    client = anthropic.Anthropic(timeout=timeout)
    kw = {"model": model, "max_tokens": 64000, "system": system,
          "messages": [{"role": "user", "content": prompt}]}
    applied = False
    if model.startswith("claude-haiku-4-5"):
        kw["temperature"] = temperature
        applied = True
    elif not model.startswith(NO_TEMPERATURE):
        kw["temperature"] = temperature
        applied = True
    if model.startswith(("claude-opus-5", "claude-sonnet-5", "claude-fable-5")):
        kw["thinking"] = {"type": "adaptive"}
        if effort:
            kw["output_config"] = {"effort": effort}
    with client.messages.stream(**kw) as s:
        msg = s.get_final_message()
    if msg.stop_reason == "refusal":
        raise LLMError("refusal: %s" % getattr(msg, "stop_details", None))
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return {"text": text, "temperature_applied": applied, "tokens_in": msg.usage.input_tokens,
            "tokens_out": msg.usage.output_tokens, "cost_usd": None}


def _openai(system, prompt, model, temperature, effort, timeout, base_url):
    body = {"model": model, "temperature": temperature,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + os.environ.get("OPENAI_API_KEY", "none")})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        d = json.loads(resp.read())
    u = d.get("usage", {})
    return {"text": d["choices"][0]["message"]["content"], "temperature_applied": True,
            "tokens_in": u.get("prompt_tokens", 0), "tokens_out": u.get("completion_tokens", 0), "cost_usd": None}


def call(system, prompt, model, temperature=0.5, backend="claude-cli", effort=None, timeout=1800,
         base_url=None, tag=None, retries=2):
    """One LLM call. Returns {text, temperature_applied, tokens_in, tokens_out, cost_usd, latency_s}."""
    last = None
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            if backend == "claude-cli":
                out = _claude_cli(system, prompt, model, temperature, effort, timeout)
            elif backend == "anthropic":
                out = _anthropic(system, prompt, model, temperature, effort, timeout)
            elif backend == "openai":
                out = _openai(system, prompt, model, temperature, effort, timeout, base_url)
            else:
                raise LLMError("unknown backend %s" % backend)
            out["latency_s"] = round(time.time() - t0, 2)
            _log({"tag": tag, "backend": backend, "model": model, "temperature_requested": temperature,
                  "temperature_applied": out["temperature_applied"], "effort": effort,
                  "prompt_sha256": hashlib.sha256((system + "\n" + prompt).encode()).hexdigest()[:16],
                  "prompt_chars": len(system) + len(prompt), "tokens_in": out["tokens_in"],
                  "tokens_out": out["tokens_out"], "cost_usd": out["cost_usd"], "latency_s": out["latency_s"],
                  "attempt": attempt, "time": time.strftime("%Y-%m-%dT%H:%M:%S")})
            return out
        except (LLMError, subprocess.TimeoutExpired, OSError) as e:
            last = e
            if "limit" in str(e).lower() and "reset" in str(e).lower():
                break   # usage limit: retrying only burns time

            _log({"tag": tag, "backend": backend, "model": model, "error": str(e)[:500], "attempt": attempt})
            time.sleep(5 * (attempt + 1))
    raise LLMError("LLM call failed after %d attempts: %s" % (retries + 1, last))


def extract_json(text):
    """First top-level JSON object in a reply (fenced or bare)."""
    import re
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    cand = [m.group(1)] if m else []
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    cand.append(text[start:i + 1])
                    break
    for c in cand:
        try:
            return json.loads(c)
        except ValueError:
            continue
    raise LLMError("no JSON object in reply: %s" % text[:300])
