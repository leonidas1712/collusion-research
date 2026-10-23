"""Shared helpers for OpenRouter smoke tests. Never prints or logs the API key."""
import json, os, time, pathlib, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
KEY_ENDPOINT = "https://openrouter.ai/api/v1/key"


def load_key():
    env = REPO / ".env"
    for line in env.read_text().splitlines():
        line = line.strip()
        if line.startswith("OPENROUTER_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OPENROUTER_API_KEY not found in .env")


def _post(url, body, key, timeout=120):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read())
        return payload, time.time() - t0, None
    except urllib.error.HTTPError as e:
        return {"error_body": e.read().decode(errors="replace")}, time.time() - t0, f"HTTP {e.code}"
    except Exception as e:
        return {"error_body": str(e)}, time.time() - t0, type(e).__name__


def chat(model, messages, key, tools=None, max_tokens=400, extra=None):
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        # ask OpenRouter to return cost in usage, and disable reasoning/thinking
        "usage": {"include": True},
        "reasoning": {"enabled": False},
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if extra:
        body.update(extra)
    return _post(ENDPOINT, body, key)


def get_key_info(key):
    req = urllib.request.Request(KEY_ENDPOINT)
    req.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["data"]
