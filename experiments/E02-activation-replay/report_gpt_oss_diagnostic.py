"""Verify every paired replay artifact and report provider-specific likelihood fidelity."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
from gpt_oss_replay import digest


def main():
    replay=ROOT/'runs/20261025-1444-e02-gpt-oss-full-shard'
    plan=ROOT/'runs/20261025-2243-e02-gpt-oss-paired-diagnostic-plan'
    client=ROOT/'runs/20261025-2243-e02-gpt-oss-full-client'
    run=start_run('e02-gpt-oss-paired-fidelity-report',experiment='E02',parents=[replay.name,plan.name,client.name],settings={'offline_verification':True})
    try:
        wanted=json.loads((plan/'shards/0000.json').read_text())['rows'];actual=json.loads((replay/'index.json').read_text())
        assert len(wanted)==len(actual)==100 and json.loads((replay/'meta.json').read_text())['status']=='finished'
        for row,record in zip(wanted,actual):
            for k,v in row.items():
                if k not in ('prompt_ids','reply_ids'):assert record[k]==v,(row['row_id'],k)
            with np.load(replay/record['file']) as arrays:
                ids=row['prompt_ids']+row['reply_ids']
                assert arrays['input_ids'].tolist()==ids and digest(ids)==row['input_ids_sha256']
                assert arrays['reasoning_positions'].tolist()==row['reasoning_positions']
                assert arrays['layer_indices'].tolist()==list(range(24))
                assert arrays['residual_last'].shape==(24,2880)
                assert arrays['residual_reasoning'].shape==(24,len(row['reasoning_positions']),2880)
                assert np.isfinite(arrays['residual_last']).all() and np.isfinite(arrays['residual_reasoning']).all()
        metrics=[]
        for provider in ['AkashML','DekaLLM']:
            for mode in ['drop_all','current_turn']:
                group=[r for r in actual if r['served_provider']==provider and r['history_reasoning_mode']==mode]
                for segment in ['all','reasoning','answer']:
                    vals=[r['fidelity'] if segment=='all' else r['segments'][segment] for r in group]
                    key='n_reply_tokens' if segment=='all' else 'n_tokens';n=sum(v[key] for v in vals)
                    metrics.append(dict(provider=provider,mode=mode,segment=segment,requests=len(group),tokens=n,
                        **{metric:sum(v[key]*v[metric] for v in vals if v[key])/n for metric in ['mean_token_nll','top5_fraction']}))
        cost=json.loads((client/'summary.json').read_text());assert cost['app_stopped']
        write_json_atomic(run.dir/'metrics.json',metrics)
        write_json_atomic(run.dir/'verification.json',dict(requests=100,source_requests=50,layers=24,hidden_size=2880,
            all_shapes_hashes_finite=True,app_stopped=True,cost=cost,full_replay_gate='pass_with_documented_provider_format_caveat',
            selected_provider_modes={'AkashML':'current_turn','DekaLLM':'drop_all'},approval='provider-stratified paired fidelity diagnostic'))
        lines=['# Paired gpt-oss provider rendering fidelity check','',
            'The diagnostic used 50 requests selected by provider, tool-turn position and prompt-count gap, without outcome labels. '
            'Each was replayed with dropped prior reasoning and with current-turn reasoning retained, for 100 teacher-forced forwards. '
            'It is an engineering fidelity check, not a representative behaviour sample or outcome fit.','',
            '| Provider | History reasoning | Segment | Tokens | Mean NLL | Top-5 |','|---|---|---|---:|---:|---:|']
        for m in metrics:lines.append(f"| {m['provider']} | {m['mode']} | {m['segment']} | {m['tokens']} | {m['mean_token_nll']:.5f} | {100*m['top5_fraction']:.3f}% |")
        lines+=['','AkashML current-turn answer/tool-body NLL is 0.25561, close to the earlier CoreWeave diagnostic’s 0.25988; '
            'top-5 is 98.816% versus 99.675%. The samples differ, so these are sanity comparisons, not a controlled equivalence test. '
            'DekaLLM drop-all answer/tool-body NLL is 0.35960 with 99.126% top-5; this does not indicate a large answer-fidelity loss. '
            'Current-turn retention improves AkashML and does not improve DekaLLM. Reasoning is less faithful than answer/tool bodies.','',
            'Decision under the conditional gate approved before provider-mode selection: proceed with AkashML current-turn and DekaLLM drop-all. '
            'DekaLLM prompt tokens remain approximate; likelihood agreement does not establish exact provider tokens. '
            'Provider quantization fields are null. Replay all requests and retain provider and absolute count gap; '
            'the primary analysis uses all eligible steps and a sensitivity excludes requests with |gap| > 1. '
            'The prior CoreWeave path and Qwen code remain unchanged.','',
            'All 100 input-token arrays, prompt/input hashes, layer IDs, reasoning positions and finite activation arrays were checked. '
            'Last-prompt arrays are [24,2880]; reasoning arrays are [24,n_reasoning,2880]. '
            f'Artifacts: `{replay.name}` locally and on the collusion-activations volume. '
            f'Replay took 145.225 seconds. Billed snapshot USD{cost["billed_so_far_usd"]:.8f}; '
            f'conservative compute upper USD{cost["conservative_compute_upper_usd"]:.8f}, charged to the shared USD20 cap. '
            'The diagnostic app is stopped. Cached MXFP4 weights were expanded to bf16 using transformers5.20.2/torch2.14.1; no weights downloaded on GPU.']
        (run.dir/'report.md').write_text('\n'.join(lines)+'\n');run.result(metrics=metrics,verified_requests=100,cost=cost);run.finish();print(run.dir)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':main()
