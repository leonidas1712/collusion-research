"""Audit actual channel-publication coverage in the matched gpt-oss call cohort."""
import json
from pathlib import Path
from lastprompt_percall import load, STREAM_DATA, DATA
from collusion.runs import start_run, write_json_atomic


def main():
    run = start_run('e05-channel-percall-feasibility', experiment='E05', parents=[STREAM_DATA.name, DATA.name], settings={'no_fits':True,'no_api':True,'no_gpu':True})
    rows, base, _, _ = load()
    matched = [r for r in rows if r['condition']=='recruiting' and r['stream_window']=='post_ask' and r['reasoning_tokens']>0]
    assert len(matched)==1995
    positives = [r for r in matched if r['request_idx']==r['first_channel_request_idx']]
    assert all(r['y_channel']==int(r['request_idx']==r['first_channel_request_idx']) for r in matched)
    channel_episodes = {r['episode']:r['first_channel_request_idx'] for r in matched if r['first_channel_request_idx'] is not None}
    available = {(r['episode'],r['request_idx']) for r in base}
    result = dict(matched_calls=len(matched), episodes=len({r['episode'] for r in matched}), any_public_positive_calls=sum(r['y_immediate'] for r in matched), first_channel_positive_calls=len(positives), eventual_channel_episodes=len(channel_episodes), first_channel_calls_in_broader_cache=sum((ep,ix) in available for ep,ix in channel_episodes.items()), positive_calls=[{k:r[k] for k in ['row_id','episode','scenario','request_idx','round']} for r in positives], verdict='Do not fit six-scenario nested LOSO on three positive calls; retaining identical calls cannot reproduce a full channel-publication endpoint.')
    write_json_atomic(run.dir/'counts.json',result)
    (run.dir/'report.md').write_text('''# Channel-only per-call feasibility

The matched gpt-oss cohort contains 1,995 calls from 238 recruiting episodes, including 121 first emissions by any public route. Only **3 calls** are first channel publications. The saved y_channel flag exactly matches request_idx == first_channel_request_idx.

Although 96 represented episodes eventually publish to the channel, their channel-publication calls mostly occur after the earlier file emission that ends this cohort. Labelling those earlier file calls as channel publications would be incorrect. Three positives, spread across only three scenarios, cannot support the requested six-scenario nested held-out-scenario fit. No fits were run.

All 96 first-channel calls from these represented episodes do exist in the broader saved last-prompt activation cache. A channel-only analysis could therefore use an expanded post-read window through the first channel publication without new GPU replay, but it would be a different cohort and would admit calls after an earlier file disclosure. It would require a declared window and eligibility rule rather than being a same-call harmonisation check.

Sources: runs/20261026-0522-e05-reasoning-stream-data/replies.json; runs/20261025-2305-e05-gpt-oss-full-data/rows.jsonl. counts.json records coverage and positive call identifiers. Script: experiments/E05-probes/channel_percall_feasibility.py.
''')
    run.result(**{k:v for k,v in result.items() if k!='positive_calls'})
    run.finish('complete')
    print(run.dir)


if __name__=='__main__':
    main()
