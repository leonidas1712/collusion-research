"""Offline rendering distributions and outcome-stratified matched-window coverage."""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic


def distribution(rows,mode):
    gaps=np.asarray([r['tokens'][mode]-r['provider_tokens'] for r in rows]);absolute=np.abs(gaps)
    cumulative={str(limit):dict(n=int(np.sum(absolute<=limit)),fraction=float(np.mean(absolute<=limit))) for limit in [1,5,20,50]}
    return dict(n=len(rows),cumulative=cumulative,median_absolute=float(np.median(absolute)),p90_absolute=float(np.percentile(absolute,90)),
        beyond50=int(np.sum(absolute>50)),min_gap=int(gaps.min()),max_gap=int(gaps.max()),
        bins={'within1':int(np.sum(absolute<=1)),'2_to_5':int(np.sum((absolute>1)&(absolute<=5))),
              '6_to_20':int(np.sum((absolute>5)&(absolute<=20))),'21_to_50':int(np.sum((absolute>20)&(absolute<=50))),
              'beyond50':int(np.sum(absolute>50))})


def main():
    audit=ROOT/'runs/20261025-2229-e02-gpt-oss-provider-template-audit'
    plan=ROOT/'runs/20261025-2226-e02-gpt-oss-full-plan'
    rows=json.loads((audit/'rows.json').read_text());planned=[json.loads(s) for s in (plan/'rows.jsonl').read_text().splitlines()]
    metadata=json.loads((plan/'episodes.json').read_text());cache={}
    run=start_run('e02-gpt-oss-rendering-gate',experiment='E02',parents=[audit.name,plan.name],settings={
        'offline_only':True,'no_token_stream_fix':True,'matching_tolerance':1,
        'primary_window':'ever-correct complete exposed; strictly post-read/pre-public emission; post-ask',
        'input_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [audit/'rows.json',plan/'rows.jsonl',plan/'episodes.json']}})
    try:
        by_key={(r['episode'],r['request_idx']):r for r in rows};assert len(by_key)==len(planned)==6985
        for row in planned:
            r=by_key[row['episode'],row['request_idx']]
            assert r['tokens']['drop_all']==row['n_tokens'] and r['provider_tokens']==row['provider_prompt_tokens']
            if row['episode'] not in cache:
                raw=Path(row['source_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['episode_sha256']
                cache[row['episode']]=json.loads(raw)
            msgs=cache[row['episode']]['requests'][row['request_idx']]['request']['messages']
            last_user=max((i for i,m in enumerate(msgs) if m['role']=='user'),default=-1)
            r['intra_turn']=any(m['role']=='tool' for m in msgs[last_user+1:])
        tables=[]
        for provider in ['AkashML','DekaLLM']:
            for scope in ['all','intra_turn','not_intra_turn']:
                group=[r for r in rows if r['provider']==provider and (scope=='all' or r['intra_turn']==(scope=='intra_turn'))]
                for mode in ['drop_all','current_turn']:
                    tables.append(dict(provider=provider,scope=scope,mode=mode,**distribution(group,mode)))
        episode_results=[];details=[]
        for window in ['eligible','window_eligible']:
            grouped=defaultdict(list)
            for r in planned:
                if r['condition']=='recruiting' and r[window]:grouped[r['episode']].append(by_key[r['episode'],r['request_idx']])
            for ep in metadata:
                if ep['condition']!='recruiting':continue
                subset=grouped[ep['episode']]
                item=dict(window=window,episode=ep['episode'],outcome='gave_in' if ep['label'] else 'held',
                          eligible_requests=len(subset),ever_correct=ep['ever_correct_summary'],exposed=ep['exposed'])
                for mode in ['drop_all','current_turn']:
                    item[mode+'_all_matched']=bool(subset) and all(abs(r['tokens'][mode]-r['provider_tokens'])<=1 for r in subset)
                    item[mode+'_unmatched_requests']=sum(abs(r['tokens'][mode]-r['provider_tokens'])>1 for r in subset)
                details.append(item)
            for outcome in ['gave_in','held']:
                group=[r for r in details if r['window']==window and r['outcome']==outcome]
                for mode in ['drop_all','current_turn']:
                    episode_results.append(dict(window=window,outcome=outcome,mode=mode,total_episodes=len(group),
                        with_eligible_requests=sum(r['eligible_requests']>0 for r in group),
                        zero_eligible_requests=sum(r['eligible_requests']==0 for r in group),
                        all_requests_matched=sum(r[mode+'_all_matched'] for r in group),
                        any_request_unmatched=sum(r['eligible_requests']>0 and not r[mode+'_all_matched'] for r in group),
                        eligible_requests=sum(r['eligible_requests'] for r in group),
                        unmatched_requests=sum(r[mode+'_unmatched_requests'] for r in group)))
        write_json_atomic(run.dir/'distributions.json',tables);write_json_atomic(run.dir/'episode-coverage.json',episode_results)
        write_json_atomic(run.dir/'episode-details.json',details)
        lines=['# gpt-oss rendering gate: offline token-count audit','',
            'No GPU has been launched and no outcome fit was run. The original validated CoreWeave renderer drops all prior reasoning. '
            'This collection instead uses AkashML (6,672 requests) and DekaLLM (313). '
            'The alternative keeps only assistant reasoning after the most recent user/peer message, i.e. during the current tool-use turn. '
            'It is evaluated on copied inputs without changing saved episodes or the production rendering mode. '
            'All 6,985 target requests are included; gap = rendered minus provider prompt tokens.','',
            '## Gap size by provider and rendering','',
            '| Provider | Rendering | N | Within ±1 | Within ±5 | Within ±20 | Within ±50 | Beyond ±50 | Median absolute | P90 absolute |',
            '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        def fmt(d,t):
            v=d['cumulative'][str(t)];return f"{v['n']} ({100*v['fraction']:.1f}%)"
        for d in tables:
            if d['scope']=='all':lines.append(f"| {d['provider']} | {d['mode']} | {d['n']} | {fmt(d,1)} | {fmt(d,5)} | {fmt(d,20)} | {fmt(d,50)} | {d['beyond50']} | {d['median_absolute']:g} | {d['p90_absolute']:g} |")
        lines+=['','Threshold columns are cumulative. Exclusive bins and signed ranges are in distributions.json.','',
            '## Intra-turn concentration','',
            'Intra-turn means a tool-result message occurs after the latest user message in the exact saved target input.','',
            '| Provider | Request group | Rendering | N | Within ±1 | Median absolute | P90 absolute |',
            '|---|---|---|---:|---:|---:|---:|']
        for d in tables:
            if d['scope']!='all':lines.append(f"| {d['provider']} | {d['scope']} | {d['mode']} | {d['n']} | {fmt(d,1)} | {d['median_absolute']:g} | {d['p90_absolute']:g} |")
        lines+=['','## Recruiting episode impact','',
            'Primary outcomes are channel-positive versus channel-negative (the latter includes file-only leaks). '
            'The main table uses eligible post-ask requests. Episodes with zero eligible requests are reported separately and never counted as trivially matched. '
            'The JSON also gives the broader post-read/pre-public window including pre-ask requests.','',
            '| Outcome | Rendering | All episodes | Has eligible requests | Zero-window | Every eligible request within ±1 | At least one mismatch |',
            '|---|---|---:|---:|---:|---:|---:|']
        for r in episode_results:
            if r['window']=='eligible':lines.append(f"| {r['outcome']} | {r['mode']} | {r['total_episodes']} | {r['with_eligible_requests']} | {r['zero_eligible_requests']} | {r['all_requests_matched']} | {r['any_request_unmatched']} |")
        lines+=['','## Proposed gate (requires author decision before GPU)','',
            'Do not select episodes by whether every request matches: this is a post-collection filter whose outcome mix is shown above. '
            'For AkashML, freeze current-turn reasoning retention as a separate provider path, based on this input-only audit, and retain the original CoreWeave path unchanged. '
            'DekaLLM remains unresolved: dropping all reasoning fits better than current-turn retention, and basic JSON tool-argument reserialization did not recover its counts '
            '(runs/20261025-2233-e02-gpt-oss-tool-format-audit). Do not silently treat it as token-exact.','',
            'Suggested next gate is a small paired teacher-forced fidelity diagnostic, charged to the existing USD20 replay cap, with requests selected by provider, '
            'intra-turn status and gap band without using outcomes. Compare AkashML current-turn versus drop-all and the best documented DekaLLM candidate; '
            'report answer/tool-body and reasoning NLL/top-5 separately. The author should decide whether approximate DekaLLM replay is acceptable '
            'before full collection replay. No token padding, prompt edits, outcome-based renderer selection, or new API calls are proposed.']
        (run.dir/'report.md').write_text('\n'.join(lines)+'\n');run.result(distributions=tables,episode_coverage=episode_results);run.finish();print(run.dir)
        for d in tables:
            if d['scope']=='all':print(d['provider'],d['mode'],{k:d[k] for k in ['n','cumulative','beyond50','median_absolute','p90_absolute']})
        for r in episode_results:
            if r['window']=='eligible':print(r)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':main()
