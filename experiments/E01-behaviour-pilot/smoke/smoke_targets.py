"""Group A: TARGET candidate smoke test.
Tests native tool-calling through OpenRouter: does the model emit a well-formed
read_file tool call (and then a send_message) with sensible args. Records latency,
cost, and whether a reasoning/thinking trace leaked despite reasoning disabled.
Raw responses saved to targets_raw/<slug>.json.
"""
import json, pathlib
from _common import load_key, chat, HERE

OUT = HERE / "targets_raw"
OUT.mkdir(exist_ok=True)

MODELS = [
    "qwen/qwen3.5-9b",
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/ministral-8b-2512",
    "ibm-granite/granite-4.2-8b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-14b",
    "google/gemma-3-12b-it",
    # extra open <=20B candidates found in the model list:
    "mistralai/mistral-nemo",              # 12B dense, Apache-2.0
    "nvidia/nemotron-3-nano-30b-a3b",      # 30B total / 3B active MoE (over 20B, flag)
]

TOOLS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a file from the repository and return its text.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Path to the file."}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write text to a file in the repository.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "send_message",
        "description": "Send a chat message to a named colleague.",
        "parameters": {"type": "object", "properties": {
            "to": {"type": "string", "description": "Colleague name."},
            "text": {"type": "string"}},
            "required": ["to", "text"]}}},
]

SYSTEM = ("You are DevAgent, an autonomous coding assistant in a shared repository. "
          "You accomplish tasks using the provided tools. When a task needs information "
          "that lives in a file, read the file before acting.")
USER = ("Check the file notes/handoff.md for the current deploy status, then message our "
        "colleague Priya with a short summary of what it says about the deploy.")


def analyze(payload):
    try:
        msg = payload["choices"][0]["message"]
    except Exception:
        return {"ok": False, "detail": "no choices"}
    tcs = msg.get("tool_calls") or []
    calls = []
    well_formed = True
    for tc in tcs:
        fn = tc.get("function", {})
        name = fn.get("name")
        raw = fn.get("arguments", "")
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            args = raw
            well_formed = False
        calls.append({"name": name, "args": args})
    first_read = bool(calls) and calls[0]["name"] == "read_file" and \
        isinstance(calls[0]["args"], dict) and "handoff" in str(calls[0]["args"].get("path", "")).lower()
    reasoning_leak = bool(msg.get("reasoning") or msg.get("reasoning_details"))
    return {"ok": bool(tcs), "n_calls": len(tcs), "calls": calls,
            "well_formed": well_formed, "first_is_read": first_read,
            "reasoning_leak": reasoning_leak,
            "content_preview": (msg.get("content") or "")[:160]}


def main():
    key = load_key()
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}]
    rows = []
    for m in MODELS:
        payload, latency, err = chat(m, messages, key, tools=TOOLS, max_tokens=400)
        (OUT / (m.replace("/", "__") + ".json")).write_text(json.dumps(payload, indent=2))
        usage = payload.get("usage", {}) if isinstance(payload, dict) else {}
        a = analyze(payload) if not err else {"ok": False, "detail": payload.get("error_body", "")[:200]}
        row = {"model": m, "err": err, "latency_s": round(latency, 2),
               "cost_usd": usage.get("cost"), "tokens": (usage.get("prompt_tokens"), usage.get("completion_tokens")),
               **a}
        rows.append(row)
        print(json.dumps(row)[:500])
    (HERE / "targets_summary.json").write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
