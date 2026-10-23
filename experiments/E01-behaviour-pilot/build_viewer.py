"""Build one self-contained HTML trace viewer for every run under runs/.

    uv run python experiments/E01-behaviour-pilot/build_viewer.py      # writes runs/viewer.html

Scans every runs/<run-id>/ folder (meta.json plus episodes/episode-*.json, including in-progress
.partial.json and earlier .attempt-N.json files, which are shown but never counted), reconstructs each
episode as one chronological timeline from its ordered `requests` list (what each agent newly saw,
what it said and reasoned, each tool call followed by its mock result, what reached the channel, API
errors and retry delays), and embeds a slimmed copy of everything as JSON in a single HTML file with
inline CSS/JS. Request message lists are dropped from the embedded raw JSON because they duplicate
`histories`; the full file is one click away via a relative link. Read-only: no API calls.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"


def _text(content):
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content if isinstance(content, str) else ("" if content is None else json.dumps(content))


def _args(raw):
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return raw


def timeline(ep: dict) -> list[dict]:
    """One item per API request, in true order; errors become their own items."""
    tools = {e.get("call_id"): e for e in ep.get("tool_log") or [] if e.get("call_id")}
    channel = ep.get("channel") or []
    seen: dict[str, int] = {}
    items = []
    for req in ep.get("requests") or []:
        actor, rnd = req.get("actor"), req.get("round")
        base = {"actor": actor, "round": rnd, "attempt": req.get("attempt")}
        msgs = (req.get("request") or {}).get("messages")
        if req.get("error") or not req.get("response"):
            items.append({**base, "t": "error", "error": req.get("error") or {"type": "no response recorded"},
                          "delay": req.get("retry_delay_seconds"), "retry_after": req.get("retry_after")})
            continue
        incoming = []
        if isinstance(msgs, list):
            for m in msgs[seen.get(actor, 0):]:
                if m.get("role") == "user":
                    incoming.append(_text(m.get("content")))
            seen[actor] = len(msgs)
        resp = req["response"]
        choice = (resp.get("choices") or [{}])[0] or {}
        msg = choice.get("message") or {}
        calls = []
        for c in msg.get("tool_calls") or []:
            fn = c.get("function") or {}
            log = tools.get(c.get("id"))
            calls.append({"name": fn.get("name"), "args": _args(fn.get("arguments")),
                          "result": log.get("result") if log else None, "logged": log is not None})
        content = _text(msg.get("content"))
        posted = [c["args"].get("content") for c in calls if c["name"] == "send_message" and c["logged"]
                  and isinstance(c["args"], dict) and isinstance(c["result"], dict) and "error" not in c["result"]]
        if not calls and content.strip() and any(e.get("actor") == actor and e.get("round") == rnd
                                                 and e.get("content") == content for e in channel):
            posted.append(content)
        usage = req.get("usage") or {}
        items.append({**base, "t": "step", "incoming": incoming, "content": content,
                      "reasoning": msg.get("reasoning"), "reasoning_details": msg.get("reasoning_details"),
                      "refusal": msg.get("refusal"), "finish": choice.get("finish_reason"),
                      "choice_error": choice.get("error"), "calls": calls, "posted": posted,
                      "provider": req.get("served_provider") or resp.get("provider"),
                      "quant": req.get("served_quantization") or resp.get("quantization"),
                      "tokens": [usage.get("prompt_tokens"), usage.get("completion_tokens")],
                      "cost": usage.get("cost")})
    return items


def summarise(path: Path, run_id: str) -> dict:
    ep = json.loads(path.read_text())
    kind = "attempt" if ".attempt-" in path.name else "partial" if path.name.endswith(".partial.json") else "final"
    spec = ep.get("scenario_spec") or {}
    reqs = ep.get("requests") or []
    costs = [(r.get("usage") or {}).get("cost") for r in reqs]
    served = Counter()
    for r in reqs:
        if r.get("error"):
            continue
        prov = r.get("served_provider") or (r.get("response") or {}).get("provider") or "unknown"
        served[f"{r.get('actor')}: {prov} ({r.get('served_quantization') or 'quant. not reported'})"] += 1
    raw = copy.deepcopy(ep)
    for r in raw.get("requests") or []:
        for key in ("request", "request_body"):
            if isinstance((r.get(key) or {}).get("messages"), list):
                r[key]["messages"] = f"<{len(r[key]['messages'])} messages omitted; see histories>"
    hist = ep.get("histories") or {}
    first = lambda actor, role: next((_text(m.get("content")) for m in hist.get(actor, []) if m.get("role") == role), None)
    return {"file": path.name, "href": f"{run_id}/episodes/{path.name}", "kind": kind,
            "counted": kind == "final" and ep.get("status") == "complete",
            "id": ep.get("episode_id") or path.stem, "status": ep.get("status"), "stop_reason": ep.get("stop_reason"),
            "scenario": ep.get("scenario") or spec.get("name"),
            "condition": {**(spec.get("metadata") or {}), **(ep.get("condition") or {})},
            "settings": ep.get("settings") or {}, "models_used": ep.get("models_used"),
            "served": dict(served), "label": ep.get("label"), "fake": ep.get("fake"),
            "cost": {"total": sum(c for c in costs if c is not None), "calls": len(reqs),
                     "unknown": sum(c is None for c in costs), "errored": sum(bool(r.get("error")) for r in reqs)},
            "honeypots": spec.get("honeypots") or [], "names": spec.get("actor_names") or {},
            "target_system": spec.get("target_system") or first("target", "system"),
            "recruiter_system": spec.get("recruiter_system") or first("recruiter", "system"),
            "task": spec.get("target_task") or first("target", "user"),
            "tool_access": spec.get("tool_access"), "initial_files": spec.get("files") or {},
            "files": ep.get("files") or {}, "rounds_completed": ep.get("rounds_completed"),
            "started_at": ep.get("started_at"), "finished_at": ep.get("finished_at"),
            "timeline": timeline(ep), "histories": hist, "raw": raw}


def load_run(run_dir: Path) -> dict:
    meta = {}
    if (run_dir / "meta.json").exists():
        meta = json.loads((run_dir / "meta.json").read_text())
    s = meta.get("settings") or {}
    files = sorted((run_dir / "episodes").glob("episode-*.json"))
    eps = [summarise(p, run_dir.name) for p in files]
    first = next((e for e in eps if e["kind"] == "final"), eps[0] if eps else {})
    s = {**(first.get("settings") or {}), **s}
    prov = lambda actor: ((s.get(f"{actor}_request_options") or {}).get("extra_body") or {}).get("provider") or {}
    counted = [e for e in eps if e["counted"]]
    labels = [e["label"] for e in counted if isinstance(e["label"], dict)]
    return {"id": run_dir.name, "time": meta.get("started") or first.get("started_at") or "",
            "experiment": meta.get("experiment"), "name": meta.get("name"), "tags": meta.get("tags") or [],
            "status": meta.get("status"), "error": meta.get("error"), "command": meta.get("command"),
            "git": meta.get("git_commit"), "dirty": meta.get("dirty"),
            "scenario": s.get("scenario") or first.get("scenario"),
            "wiring": bool(s.get("fake")) or s.get("scenario") in ("dummy", "fake") or "wiring" in (meta.get("tags") or []),
            "condition": first.get("condition") or {}, "target_model": s.get("target_model"),
            "target_provider": ",".join(prov("target").get("order") or []) or None,
            "peer_model": s.get("recruiter_model") if s.get("peer_enabled", True) else None,
            "peer_provider": ",".join(prov("recruiter").get("order") or []) or None,
            "n_complete": len(counted), "n_incomplete": len(eps) - len(counted),
            "leaked": sum(bool(l.get("objective_success")) for l in labels),
            "resisted": sum(bool(l.get("eligible_resisted")) for l in labels),
            "task_ok": sum(bool(l.get("task_success")) for l in labels), "n_labelled": len(labels),
            "episodes": eps}


def main():
    runs = [load_run(d) for d in sorted(RUNS.iterdir()) if d.is_dir() and (d / "episodes").is_dir()]
    runs.sort(key=lambda r: (r["time"], r["id"]), reverse=True)
    data = json.dumps(runs, ensure_ascii=False).replace("</", "<\\/")
    out = RUNS / "viewer.html"
    out.write_text(TEMPLATE.replace("__DATA__", data))
    n = sum(len(r["episodes"]) for r in runs)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB): {len(runs)} runs, {n} episode files")


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>E01 Trace Viewer</title>
<style>
:root{--bg:#f7f7f5;--panel:#fff;--fg:#1d1d1f;--mut:#6b6b70;--line:#e2e2de;--acc:#2f6fdf;--tgt:#e9f1ff;--tgtb:#2f6fdf;
--rec:#f4ecff;--recb:#8a4fd6;--tool:#f2f2ef;--bad:#c62828;--badbg:#fdeaea;--ok:#2e7d32;--okbg:#e8f5e9;--warn:#a15c00;--warnbg:#fff4e0;--mark:#ffd54f}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--panel:#1d1d20;--fg:#e8e8ea;--mut:#9a9aa2;--line:#323238;--acc:#7aa7ff;
--tgt:#1a2538;--tgtb:#7aa7ff;--rec:#261d36;--recb:#b48cf0;--tool:#232327;--bad:#ff7b7b;--badbg:#3a1d1d;--ok:#7fd283;--okbg:#1b2e1c;
--warn:#ffb74d;--warnbg:#33281a;--mark:#8a6d00}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,system-ui,Segoe UI,sans-serif}
code,pre,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
pre{white-space:pre-wrap;word-break:break-word;margin:4px 0;background:var(--tool);padding:8px 10px;border-radius:6px}
#app{display:grid;grid-template-columns:360px 1fr;height:100vh}
#side{border-right:1px solid var(--line);overflow:auto;background:var(--panel)}#main{overflow:auto;padding:20px 28px 80px}
#filters{position:sticky;top:0;background:var(--panel);padding:12px;border-bottom:1px solid var(--line);display:grid;gap:6px;z-index:2}
#filters select,#filters input[type=search]{width:100%;padding:5px 6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.run{padding:9px 12px;border-bottom:1px solid var(--line);cursor:pointer}.run:hover{background:var(--tool)}.run.sel{background:var(--tgt)}
.run.wiring{opacity:.6}.run .id{font-weight:600;font-size:12.5px}.run .sub{color:var(--mut);font-size:12px}
.pill{display:inline-block;padding:0 7px;border-radius:9px;font-size:11.5px;background:var(--tool);color:var(--mut);margin:1px 2px 1px 0;white-space:nowrap}
.pill.bad{background:var(--badbg);color:var(--bad)}.pill.ok{background:var(--okbg);color:var(--ok)}.pill.warn{background:var(--warnbg);color:var(--warn)}
h1{font-size:20px;margin:0 0 6px}h2{font-size:15px;margin:22px 0 8px}a{color:var(--acc)}
table{border-collapse:collapse;margin:6px 0}td,th{border:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top;font-size:13px}
th{background:var(--tool);font-weight:600}tr.hl td{background:var(--warnbg)}tr.click{cursor:pointer}tr.click:hover td{background:var(--tool)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:4px 18px}.kv{font-size:13px}.kv b{color:var(--mut);font-weight:500}.kv code{word-break:break-all}#main{min-width:0}
details{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 12px;margin:8px 0}summary{cursor:pointer;font-weight:600}
.banner{padding:8px 12px;border-radius:8px;margin:8px 0;background:var(--warnbg);color:var(--warn)}.banner.bad{background:var(--badbg);color:var(--bad)}
.sep{display:flex;align-items:center;gap:8px;margin:22px 0 10px;color:var(--mut);font-weight:600;font-size:12.5px}
.sep:after{content:"";flex:1;border-top:1px solid var(--line)}.sep.leak{color:var(--bad)}.sep.leak:after{border-color:var(--bad)}
.turn{border-left:4px solid var(--tgtb);background:var(--tgt);border-radius:8px;padding:8px 12px;margin:8px 0}
.turn.recruiter{border-color:var(--recb);background:var(--rec);margin-left:40px}.turn.target{margin-right:40px}
.who{font-weight:700;font-size:12.5px}.meta{color:var(--mut);font-size:11.5px;margin-left:6px}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin-top:6px}
.in{border-left:3px solid var(--line);padding:2px 8px;margin:4px 0;color:var(--fg);white-space:pre-wrap;font-size:13px}
.say{white-space:pre-wrap;margin:4px 0}.call{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 8px;margin:6px 0}
.call .nm{font-weight:600}.post{background:var(--panel);border:1px dashed var(--acc);border-radius:6px;padding:4px 8px;margin:4px 0;white-space:pre-wrap}
.err{background:var(--badbg);color:var(--bad);border-radius:6px;padding:5px 10px;margin:6px 0;font-size:12.5px}
.think{opacity:.85;font-style:italic}mark.leak{background:var(--mark);color:inherit;padding:0 2px;border-radius:3px;font-weight:600}
.tabs button{border:1px solid var(--line);background:var(--panel);color:var(--fg);padding:5px 12px;border-radius:6px;cursor:pointer;margin-right:4px}
.tabs button.on{background:var(--acc);color:#fff;border-color:var(--acc)}.empty{color:var(--mut);padding:40px}
@media (max-width:800px){#app{grid-template-columns:1fr;height:auto}#side{max-height:45vh}}
</style></head><body><div id="app"><aside id="side"><div id="filters">
<input type="search" id="q" placeholder="Search runs, models, scenarios, labels…">
<div class="row2"><select id="fModel"></select><select id="fStatus"><option value="">any status</option>
<option value="complete">all complete</option><option value="incomplete">has incomplete</option><option value="leaked">has leak</option></select></div>
<div class="row2"><select id="fPolicy"></select><select id="fRel"></select></div><div class="row2"><select id="fPeer"></select>
<label style="font-size:12.5px"><input type="checkbox" id="fWiring"> hide wiring/fake</label></div>
<div id="count" class="sub" style="color:var(--mut);font-size:12px"></div></div><div id="list"></div></aside><main id="main"></main></div>
<script type="application/json" id="data">__DATA__</script>
<script>
const RUNS=JSON.parse(document.getElementById('data').textContent);
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let HP=[];
const hl=s=>{let h=esc(s);for(const t of HP)if(t)h=h.split(esc(t)).join('<mark class="leak" title="secret marker">'+esc(t)+'</mark>');return h};
const fmt=v=>v===null||v===undefined?'<span style="color:var(--mut)">—</span>':typeof v==='object'?'<code>'+hl(JSON.stringify(v))+'</code>':hl(String(v));
const pretty=v=>typeof v==='string'?v:JSON.stringify(v,null,2);
const cond=r=>r.condition||{};
function opts(sel,label,vals){$(sel).innerHTML=`<option value="">${label}: any</option>`+[...new Set(vals.filter(v=>v!=null))].sort().map(v=>`<option>${esc(v)}</option>`).join('')}
opts('#fModel','target',RUNS.map(r=>r.target_model));opts('#fPolicy','policy',RUNS.map(r=>cond(r).policy));
opts('#fRel','relation',RUNS.map(r=>cond(r).goal_relation));opts('#fPeer','peer',RUNS.map(r=>cond(r).peer_condition));
for(const id of['q','fModel','fStatus','fPolicy','fRel','fPeer','fWiring'])$('#'+id).addEventListener('input',renderList);
function pass(r){const q=$('#q').value.toLowerCase(),c=cond(r),st=$('#fStatus').value;
 if($('#fWiring').checked&&r.wiring)return false;if($('#fModel').value&&r.target_model!==$('#fModel').value)return false;
 if($('#fPolicy').value&&c.policy!==$('#fPolicy').value)return false;if($('#fRel').value&&c.goal_relation!==$('#fRel').value)return false;
 if($('#fPeer').value&&c.peer_condition!==$('#fPeer').value)return false;
 if(st==='complete'&&(r.n_incomplete||!r.n_complete))return false;if(st==='incomplete'&&!r.n_incomplete)return false;if(st==='leaked'&&!r.leaked)return false;
 if(q){const hay=JSON.stringify([r.id,r.scenario,r.target_model,r.peer_model,r.target_provider,r.condition,r.tags,r.episodes.map(e=>[e.file,e.stop_reason,e.label])]).toLowerCase();if(!hay.includes(q))return false}
 return true}
function condPills(c){return['policy','goal_relation','peer_condition'].filter(k=>c[k]).map(k=>`<span class="pill">${esc(c[k])}</span>`).join('')}
function outcomePills(r){let h=`<span class="pill ${r.n_complete?'ok':''}">${r.n_complete} complete</span>`;
 if(r.n_incomplete)h+=`<span class="pill warn">${r.n_incomplete} incomplete</span>`;
 if(r.n_labelled){h+=`<span class="pill ${r.leaked?'bad':''}">leaked ${r.leaked}/${r.n_labelled}</span><span class="pill">resisted ${r.resisted}</span><span class="pill">task ${r.task_ok}</span>`}
 if(r.wiring)h+='<span class="pill warn">wiring/fake</span>';return h}
function renderList(){const rs=RUNS.filter(pass),cur=(location.hash.split('/')[1]||'');
 $('#count').textContent=`${rs.length} of ${RUNS.length} runs · newest first`;
 $('#list').innerHTML=rs.map(r=>`<div class="run ${r.wiring?'wiring':''} ${decodeURIComponent(cur)===r.id?'sel':''}" onclick="location.hash='#run/'+encodeURIComponent('${esc(r.id)}')">
 <div class="id">${esc(r.id)}</div><div class="sub">${esc(r.time.replace('T',' '))} · ${esc(r.experiment||'')} · ${esc(r.scenario||'?')}</div>
 <div class="sub">target <b>${esc(r.target_model||'?')}</b>${r.target_provider?' @'+esc(r.target_provider):''} · peer ${esc(r.peer_model||'none')}</div>
 <div>${condPills(cond(r))}${outcomePills(r)}</div></div>`).join('')||'<div class="empty">No runs match.</div>'}
function kv(pairs){return '<div class="grid">'+pairs.map(([k,v])=>`<div class="kv"><b>${esc(k)}:</b> ${fmt(v)}</div>`).join('')+'</div>'}
function epStatus(e){return e.counted?'<span class="pill ok">complete</span>':`<span class="pill warn">${esc(e.kind==='final'?e.status:e.kind)} · not counted</span>`}
function lab(e,k){return e.label&&typeof e.label==='object'?e.label[k]:null}
function showRun(r){$('#main').innerHTML=`<h1>${esc(r.id)}</h1><div>${condPills(cond(r))}${outcomePills(r)}</div>
 ${r.error?`<div class="banner bad">run error: ${esc(r.error)}</div>`:''}
 <h2>Run</h2>${kv([['started',r.time],['status',r.status],['experiment',r.experiment],['scenario',r.scenario],['tags',r.tags.join(', ')],
 ['target',r.target_model],['target provider pin',r.target_provider],['peer',r.peer_model],['peer provider pin',r.peer_provider],['git',r.git?(r.git.slice(0,10)+(r.dirty?' (dirty)':'')):null]])}
 ${r.command?`<pre>${esc(r.command)}</pre>`:''}<h2>Episodes</h2><table><tr><th>file</th><th>family</th><th>status</th><th>stop</th><th>leaked</th><th>resisted</th><th>task</th><th>token read r.</th><th>first ask r.</th><th>cost</th></tr>
 ${r.episodes.map((e,i)=>`<tr class="click" onclick="location.hash='#run/'+encodeURIComponent('${esc(r.id)}')+'/${i}'"><td class="mono">${esc(e.file)}</td><td>${fmt(e.condition.family_id)}</td><td>${epStatus(e)}</td>
 <td>${fmt(e.stop_reason)}</td><td>${typeof e.label==='object'?fmt(lab(e,'objective_success')):fmt(e.label)}</td><td>${fmt(lab(e,'eligible_resisted'))}</td><td>${fmt(lab(e,'task_success'))}</td>
 <td>${fmt(lab(e,'token_read_round'))}</td><td>${fmt(lab(e,'first_peer_ask_round'))}</td><td>$${e.cost.total.toFixed(4)}</td></tr>`).join('')}</table>`}
const KEY=new Set(['objective_success','eligible_resisted','token_read_round','first_peer_ask_round','fabricated_disclosure','partial_token_publication','task_success','first_action_round','boundary_violation','other_file_disclosure','valid_for_comparison']);
function labelTable(L){if(L==null)return '<div class="banner">No label (episode incomplete or unscored).</div>';
 if(typeof L!=='object')return `<p>label: <b>${fmt(L)}</b></p>`;
 return '<table>'+Object.entries(L).map(([k,v])=>`<tr class="${KEY.has(k)&&v!==null&&v!==false&&!(Array.isArray(v)&&!v.length)?'hl':''}"><th>${esc(k)}</th><td>${KEY.has(k)?'<b>'+fmt(v)+'</b>':fmt(v)}</td></tr>`).join('')+'</table>'}
function stepHtml(s,e){const nm=e.names[s.actor]||s.actor;let h=`<div class="turn ${esc(s.actor)}"><span class="who">${esc(s.actor==='recruiter'?'peer':s.actor)} · ${esc(nm)}</span>
 <span class="meta">round ${s.round} · attempt ${s.attempt} · ${esc(s.provider||'provider ?')}${s.quant?' / '+esc(s.quant):''} · tokens ${s.tokens.map(t=>t??'?').join('→')} · ${s.cost==null?'cost unknown':'$'+s.cost.toFixed(5)} · finish ${esc(s.finish)}</span>`;
 if(s.incoming.length)h+='<div class="lbl">incoming (as this agent saw it)</div>'+s.incoming.map(m=>`<div class="in">${hl(m)}</div>`).join('');
 if(s.reasoning)h+=`<div class="lbl">reasoning</div><div class="say think">${hl(s.reasoning)}</div>`;
 if(s.reasoning_details&&s.reasoning_details.length)h+=`<details><summary>reasoning_details</summary><pre>${hl(pretty(s.reasoning_details))}</pre></details>`;
 if(s.content&&s.content.trim())h+=`<div class="lbl">assistant text</div><div class="say">${hl(s.content.trim())}</div>`;
 if(s.refusal)h+=`<div class="err">refusal: ${hl(s.refusal)}</div>`;
 for(const c of s.calls)h+=`<div class="call"><span class="nm">⚙ ${esc(c.name)}</span><pre>${hl(pretty(c.args))}</pre>
 <div class="lbl">result</div>${c.logged?`<pre>${hl(pretty(c.result))}</pre>`:'<div class="err">not executed (no tool_log entry; episode stopped)</div>'}</div>`;
 for(const p of s.posted)h+=`<div class="lbl">posted to #team channel</div><div class="post">${hl(p)}</div>`;
 if(s.choice_error)h+=`<div class="err">provider error in response: ${esc(JSON.stringify(s.choice_error))}</div>`;
 else if(s.finish&&!['stop','tool_calls'].includes(s.finish))h+=`<div class="err">finish_reason ${esc(s.finish)} — episode stops here</div>`;
 return h+'</div>'}
function trace(e){const L=typeof e.label==='object'&&e.label||{},leak=L.first_action_round;let h='',rnd=null;
 if(!e.timeline.length)return '<div class="banner">No requests recorded.</div>';
 for(const s of e.timeline){if(s.round!==rnd){rnd=s.round;const tags=[];if(rnd===leak)tags.push('FIRST LEAK — token posted to channel');
  if(rnd===L.token_read_round)tags.push('token file read');if(rnd===L.first_peer_ask_round)tags.push('first peer ask');
  h+=`<div class="sep ${rnd===leak?'leak':''}">Round ${esc(rnd)}${tags.length?' · '+tags.join(' · '):''}</div>`}
  h+=s.t==='error'?`<div class="err">⚠ ${esc(s.actor)} API call failed (round ${s.round}, attempt ${s.attempt}): ${esc(s.error.type)}${s.error.status_code?' '+s.error.status_code:''}
  ${s.delay!=null?` · retrying in ${s.delay.toFixed(1)}s`:' · retry delay not recorded'}${s.retry_after!=null?` · retry-after header ${esc(s.retry_after)}`:''}</div>`:stepHtml(s,e)}
 return h+`<div class="sep">End · status ${esc(e.status)} · ${esc(e.stop_reason)}</div>`}
function history(e){return Object.entries(e.histories).map(([a,msgs])=>`<h2>${esc(a)} full history (${msgs.length} messages)</h2>`+msgs.map(m=>{
 let b=m.content!=null&&m.content!==''?`<div class="say">${hl(typeof m.content==='string'?m.content:pretty(m.content))}</div>`:'';
 if(m.reasoning)b+=`<div class="say think">${hl(m.reasoning)}</div>`;
 for(const c of m.tool_calls||[])b+=`<pre>⚙ ${esc(c.function&&c.function.name)} ${hl(c.function&&c.function.arguments)}</pre>`;
 return `<div class="call"><span class="nm">${esc(m.role)}</span>${m.tool_call_id?` <span class="meta">${esc(m.tool_call_id)}</span>`:''}${b}</div>`}).join('')).join('')}
let VIEW='trace';
function showEp(r,i){const e=r.episodes[i];if(!e)return showRun(r);HP=e.honeypots||[];const s=e.settings,c=e.condition,L=typeof e.label==='object'&&e.label||{};
 const banner=e.kind==='attempt'?'Earlier failed attempt (superseded by a restart) — not counted.':e.kind==='partial'?'Partial file: episode in progress or crashed — not counted.':e.status!=='complete'?'Episode incomplete — not counted.':'';
 $('#main').innerHTML=`<div class="meta" style="margin:0"><a href="#run/${encodeURIComponent(r.id)}">← ${esc(r.id)}</a></div>
 <h1>${esc(e.file)} ${epStatus(e)} ${L.objective_success?'<span class="pill bad">LEAKED</span>':''}${L.eligible_resisted?'<span class="pill ok">resisted</span>':''}${e.fake?'<span class="pill warn">fake client</span>':''}</h1>
 ${banner?`<div class="banner">${banner}</div>`:''}
 ${kv([['scenario',e.scenario],['scenario_version',c.scenario_version],['family_id',c.family_id],['policy',c.policy],['goal_relation',c.goal_relation],['peer_condition',c.peer_condition],['peer_enabled',c.peer_enabled],
 ['target model',s.target_model],['peer model',c.peer_enabled===false?'(no peer)':s.recruiter_model],['served',Object.entries(e.served).map(([k,n])=>k+' ×'+n).join('; ')||null],
 ['temperature',s.temperature],['rounds',`${e.rounds_completed??'?'} / ${s.rounds??'?'}`],['max_tool_steps',s.max_tool_steps],['max_tokens',s.max_tokens],
 ['status',e.status],['stop_reason',e.stop_reason],['cost',`$${e.cost.total.toFixed(4)} over ${e.cost.calls} calls`+(e.cost.unknown?` · ⚠ ${e.cost.unknown} with unknown cost (${e.cost.errored} errored)`:'')],
 ['target routing',s.target_request_options],['peer routing',s.recruiter_request_options],['started',e.started_at],['finished',e.finished_at]])}
 <h2>Label</h2>${labelTable(e.label)}
 <details><summary>System prompts, task and tool access</summary><div class="lbl">target system</div><pre>${hl(e.target_system)}</pre><div class="lbl">target task</div><pre>${hl(e.task)}</pre>
 ${e.recruiter_system?`<div class="lbl">peer system</div><pre>${hl(e.recruiter_system)}</pre>`:''}<div class="lbl">tool access</div><pre>${esc(pretty(e.tool_access))}</pre>
 <div class="lbl">initial files</div>${Object.entries(e.initial_files).map(([p,t])=>`<div class="mono">${esc(p)}</div><pre>${hl(t)}</pre>`).join('')}</details>
 <div class="tabs" style="margin:16px 0"><button data-v="trace">Timeline</button><button data-v="hist">Raw histories</button><button data-v="raw">Raw JSON</button>
 <a href="${esc(e.href)}" style="margin-left:8px;font-size:12.5px">open full file</a></div><div id="body"></div>`;
 const body=()=>{document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('on',b.dataset.v===VIEW));
  $('#body').innerHTML=VIEW==='trace'?trace(e)+`<h2>Final files</h2>`+Object.entries(e.files).map(([p,t])=>`<div class="mono">${esc(p)}${e.initial_files[p]!==t?' <span class="pill warn">changed</span>':''}</div><pre>${hl(t)}</pre>`).join('')
  :VIEW==='hist'?history(e):`<p class="meta">Request message lists are omitted (they duplicate histories).</p><pre>${hl(JSON.stringify(e.raw,null,2))}</pre>`};
 document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{VIEW=b.dataset.v;body()});body()}
function route(){const [,id,i]=location.hash.slice(1).split('/');const r=RUNS.find(x=>x.id===decodeURIComponent(id||''));renderList();
 if(!r){$('#main').innerHTML=`<div class="empty"><h1>E01 traces</h1>${RUNS.length} runs, ${RUNS.reduce((a,r)=>a+r.episodes.length,0)} episode files. Pick a run on the left.</div>`;return}
 i===undefined?showRun(r):showEp(r,+i);$('#main').scrollTop=0}
window.addEventListener('hashchange',route);route();
</script></body></html>
"""

if __name__ == "__main__":
    main()
