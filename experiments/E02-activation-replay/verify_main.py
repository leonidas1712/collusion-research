"""Validate downloaded replay artifacts against the approved request manifest."""
import argparse
import json
from collections import Counter
from pathlib import Path
import numpy as np
from replay import digest, start_run
from replay_manifest import load_manifest


def main(args):
    source=Path(args.run);manifest=Path(args.manifest)
    run=start_run('e02-main-replay-validation',experiment='E02',parents=[source.name,manifest.parent.name],settings=vars(args))
    try:
        expected={(r['run_id'],Path(r['episode_file']).name,r['request_idx']):r for r in load_manifest(manifest)}
        rows=[json.loads(line) for line in (source/'index.jsonl').read_text().splitlines()]
        seen=set();scored=[];statuses=Counter();serializations=Counter();bytes_total=0
        provenance=json.loads((source/'provenance.json').read_text())
        assert provenance['manifest_sha256']==digest(manifest.read_bytes())
        assert (source/'selection_manifest.jsonl').read_bytes()==manifest.read_bytes()
        layer_indices=provenance['selected_layers']
        assert layer_indices==list(range(64)) and provenance['hidden_size']==5120
        assert provenance['dtype']=='bfloat16' and not provenance['tiny_random']
        for row in rows:
            key=(row['run_id'],Path(row['episode_file']).name,row['request_idx'])
            assert key in expected and key not in seen;seen.add(key);planned=expected[key]
            assert row['manifest_verified'] and row['manifest']==planned
            for field in ('episode_sha256','request_sha256','prompt_sha256','input_ids_sha256','n_tokens',
                          'token_in_context','first_request_in_turn','acts_this_step','before_first_action'):
                assert row[field]==planned[field],(key,field)
            prompt=(source/row['prompt_file']).read_bytes();assert digest(prompt)==planned['prompt_sha256']
            path=source/row['artifact'];bytes_total+=path.stat().st_size
            with np.load(path) as data:
                assert list(data['layer_indices'])==layer_indices
                assert data['residual_last'].shape==(64,5120)
                assert np.isfinite(data['residual_last']).all() and np.any(data['residual_last'])
                assert digest(data['input_ids'].tolist())==planned['input_ids_sha256']
                assert len(data['input_ids'])==planned['n_tokens']
                reply_n=len(data['reply_ids']);assert reply_n<=64
            f=row['reply_fidelity'];statuses[f['status']]+=1
            if f['status']=='scored':
                assert f['n_reply_tokens']==reply_n>0
                assert np.isfinite(f['mean_token_nll']) and f['mean_token_nll']>=0
                assert 0<=f['top5_fraction']<=1
                scored.append(f);serializations[f['serialization']]+=1
            else:assert reply_n==0
        assert seen==set(expected),(len(seen),len(expected))
        n=sum(f['n_reply_tokens'] for f in scored)
        result=dict(requests=len(rows),episodes=len({k[:2] for k in seen}),manifest_hashes_match=True,
            artifact_bytes=bytes_total,statuses=dict(statuses),serialization=dict(serializations),
            prompt_tokens=sum(r['n_tokens'] for r in rows),reply_tokens=n,
            weighted_nll=sum(f['mean_token_nll']*f['n_reply_tokens'] for f in scored)/n,
            weighted_top5=sum(f['top5_fraction']*f['n_reply_tokens'] for f in scored)/n,
            request_nll_quantiles=dict(zip(['min','median','p95','max'],map(float,np.quantile([f['mean_token_nll'] for f in scored],[0,.5,.95,1])))),
            decoder_seconds=sum(r['activation_seconds'] for r in rows),processing_seconds=sum(r['total_seconds'] for r in rows))
        (run.dir/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));run.result(**result);run.finish();print(run.id)
    except BaseException as exc:
        run.finish('failed',str(exc));raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--manifest',default='runs/20261024-1803-e02-step-prefix-plan/steps.jsonl');main(p.parse_args())
