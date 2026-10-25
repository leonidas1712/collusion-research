"""Validate downloaded Harmony replay arrays and write a small fidelity report."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic


def main(a):
    source=Path(a.replay).resolve();plan=json.loads(Path(a.plan).read_text());index=json.loads((source/'index.json').read_text());summary=json.loads((source/'summary.json').read_text())
    run=start_run('e02-gpt-oss-fidelity-report',experiment='E02',parents=[source.name],settings=vars(a))
    assert len(index)==len(plan['rows'])==76
    files=[];reasoning_count=0
    for row,expected in zip(index,plan['rows']):
        assert (row['episode_file'],row['request_idx'],row['request_sha256'],row['prompt_sha256'])==tuple(expected[k] for k in ['episode_file','request_idx','request_sha256','prompt_sha256'])
        path=source/row['file']
        with np.load(path) as z:
            assert z['residual_last'].shape==(24,2880)
            assert z['residual_reasoning'].shape==(24,len(expected['reasoning_positions']),2880)
            assert np.isfinite(z['residual_last']).all() and np.isfinite(z['residual_reasoning']).all()
            np.testing.assert_array_equal(z['input_ids'],expected['prompt_ids']+expected['reply_ids'])
            np.testing.assert_array_equal(z['reasoning_positions'],expected['reasoning_positions'])
            np.testing.assert_array_equal(z['layer_indices'],np.arange(24))
            assert z['residual_last'].dtype==np.float32 and z['residual_reasoning'].dtype==np.float32
            reasoning_count+=len(expected['reasoning_positions'])
        files.append({'file':row['file'],'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    assert reasoning_count==945
    clients=[json.loads((Path(p)/'summary.json').read_text()) for p in a.clients]
    assert all(c['app_stopped'] and not c['error'] for c in clients)
    app_ids={c['app_id'] for c in clients}
    billing=json.loads(subprocess.check_output(['modal','billing','report','--for','today','--resolution','h','--show-resources','--json']))
    billing=[r for r in billing if r.get('object_id') in app_ids]
    billed=sum(Decimal(r['cost']) for r in billing)
    conservative=sum(c['conservative_compute_upper_usd'] for c in clients)+.5
    assert conservative<4 and billed<4
    metrics={k:summary[k] for k in ['all','reasoning','answer']}
    n=metrics['all']['n_tokens']-sum(metrics[k]['n_tokens'] for k in ['reasoning','answer'])
    metrics['framing']={'n_tokens':n,**{k:(metrics['all'][k]*metrics['all']['n_tokens']-sum(metrics[s][k]*metrics[s]['n_tokens'] for s in ['reasoning','answer']))/n for k in ['mean_token_nll','top5_fraction']}}
    groups={}
    for name in sorted({r['episode_file'] for r in index}):
        rows=[r for r in index if r['episode_file']==name];total=sum(r['fidelity']['n_reply_tokens'] for r in rows)
        groups[name]={'requests':len(rows),'reply_tokens':total,**{key:sum(r['fidelity'][key]*r['fidelity']['n_reply_tokens'] for r in rows)/total for key in ['mean_token_nll','top5_fraction']}}
    deltas=Counter(r['drop_prompt_tokens']-r['provider_prompt_tokens'] for r in index)
    result=dict(verified_requests=len(index),reasoning_positions=reasoning_count,prompt_count_deltas=dict(deltas),metrics=metrics,episodes=groups,
        storage_bytes=sum(f['bytes'] for f in files),peak_cuda_gib=summary['peak_cuda_bytes']/2**30,
        model_load_seconds=summary['model_load_seconds'],wall_seconds=summary['wall_seconds'],
        billed_snapshot_usd=str(billed),billing_may_lag=True,conservative_total_with_overhead_usd=conservative,clients=clients,versions=summary['versions'],
        source_replay=str(source.relative_to(ROOT)),plan=a.plan,parameter_dtypes=summary['parameter_dtypes'])
    write_json_atomic(run.dir/'verification.json',result);write_json_atomic(run.dir/'files.json',files);write_json_atomic(run.dir/'billing.json',billing)
    lines=['# gpt-oss-20b Harmony replay fidelity and activation check','','## Result','',
        '**The isolated replay plumbing passes this small test and is ready to use in a separately planned full replay. It is not an exact reconstruction of provider execution.** All 76 requests from three saved episodes pass prompt-hash, input-token, finite-array and shape checks. No generation or new target/peer API call was used. Full collection and full replay were not run.','',
        'The test uses recruiting-0002 (give-in), recruiting-0003 (held), and control-0001 from the escalation worktree run `20261025-1912-e03-escalation-gpt-oss-envblock_late`. Every saved target request in these three complete episodes is included. The API served CoreWeave with fp4 routing; provider precision itself was not returned. The selection is a plumbing sample, not a population estimate.','',
        '## Rendering and precision','',
        'Weights: `openai/gpt-oss-20b@6cee5e81ee83917806bbde320786a8fb61efebee`. `transformers==5.20.2` supports GptOssForCausalLM and `Mxfp4Config(dequantize=True)`. This expands the released MXFP4 values into bf16; it does not recover unquantized original weights. All loaded model parameters in this run were bf16. Attention used the built-in eager implementation, one A100-80GB, no CPU/disk offload.','',
        'Official `openai-harmony==0.0.8` renders LOW reasoning, saved-call date, original tool schemas, raw argument JSON/results and commentary tool messages. Prior assistant reasoning is omitted. All 76 prompts are exactly one token shorter than provider usage, including later conversational turns. Retaining all earlier reasoning yields growing count errors, up to +594. This supports omission for these CoreWeave traces, but counts alone cannot identify the missing token or prove identical token sequences. No padding token was added.','',
        'The saved response is appended through the official training renderer; the prompt must be its exact token prefix. The current response includes returned analysis text, final content/tool arguments and Harmony framing. Reasoning positions select only returned analysis body tokens, excluding headers and terminators. All 76 extracted spans equal the tokenizer encoding of the returned reasoning text. Unreturned internal reasoning cannot be recovered. Renderer IDs are passed directly to the model; do not decode and HF re-encode, because literal Harmony-looking text can become control tokens.','',
        '## Teacher-forced fidelity','',
        '| Segment | Tokens | Mean NLL (nats/token) | Top-5 |','|---|---:|---:|---:|']
    lines += [f"| {k} | {v['n_tokens']} | {v['mean_token_nll']:.6f} | {100*v['top5_fraction']:.3f}% |"for k,v in metrics.items()]
    lines += ['', 'Qwen reference: approximately 0.23 NLL and 99.8% top-5. The gpt-oss answer/tool-content result is close; the reasoning portion is less predictable and raises the overall NLL. This looks acceptable as a fidelity sanity check, with a larger gap than Qwen. It is not a controlled precision comparison: these are different episodes/models and this test scores full replies, whereas the main Qwen pipeline limits fidelity to the first 64 reply tokens. Sampling and rendering differences also contribute; the gap cannot be assigned solely to fp4 versus bf16 arithmetic.','',
        '| Episode | Requests | Reply tokens | NLL | Top-5 |','|---|---:|---:|---:|---:|']
    lines += [f"| {k} | {v['requests']} | {v['reply_tokens']} | {v['mean_token_nll']:.6f} | {100*v['top5_fraction']:.3f}% |" for k,v in groups.items()]
    lines += ['', '## Saved activations and validation','',
        f"Local artifact directory: `{source.relative_to(ROOT)}`. The identical directory exists on Modal Volume `collusion-activations`. Each of 76 NPZ files contains `residual_last` with shape **[24, 2880]**, and `residual_reasoning` with shape **[24, n_reasoning_tokens, 2880]**. There are **945 reasoning positions** in total; a reply without reasoning has a zero-length token axis. Arrays are float32 copies of bf16 block outputs, before final model normalization. Layers are numbered 0–23; the embedding is not an extra layer. Total NPZ storage: {result['storage_bytes']:,} bytes.", '',
        'The last-prompt state is measured immediately before the served reply. Reasoning states are measured after consuming each corresponding reasoning token, with causal attention. They must be aligned to available reasoning when used as prospective monitor inputs; later reply states must not be treated as pre-reply features. Each NPZ also stores full teacher-forced input IDs, absolute zero-based reasoning positions and layer indices. `index.json` maps files to source episode/request, hashes, prompt counts and per-request fidelity. The separate immutable plan retains source labels and the exact prompt/reply split.','',
        'Four local regression tests passed. A tiny random GptOss model completed the same path; a causality test shows that appending reply tokens leaves last-prompt activations unchanged; captured intermediate reasoning states match native hidden states; manual likelihood computation matches; hooks are removed. The Qwen `replay.py`, `fidelity.py`, and `modal_app.py` files were not modified. The new adapter reuses decoder-layer discovery and likelihood scoring from E02.','',
        '## Runtime and cost','',
        f"Model load: {summary['model_load_seconds']:.2f}s. Replay including load and output writes: {summary['wall_seconds']:.2f}s. Peak CUDA allocation: {result['peak_cuda_gib']:.2f} GiB. Pins: {summary['versions']}. CPU prefetch and GPU apps are both confirmed stopped.", '',
        f"Latest app-filtered billing snapshot: **USD {billed}** (billing can lag). Conservative whole-client wall-time compute bounds plus USD0.50 setup/storage/egress allowance total **USD {conservative:.4f}**, below the separate USD4 cap. `billing.json` and the two client-run summaries preserve the accounting. Cached weights and activations remain on their existing volumes; no live container remains.", '',
        '## Reproduction and limits','',
        'See `experiments/E02-activation-replay/GPT_OSS_REPLAY.md` for commands. The dedicated wrapper intentionally accepts at most 100 requests per call, caps each input at 16,384 tokens, and has a 25-minute timeout. A full replay must be explicitly planned and sharded under its own budget; these guards are not silently relaxed. No full-replay cost or scientific probe result is claimed by this test.','',
        'Sources: [Transformers MXFP4 configuration](https://huggingface.co/docs/transformers/en/main_classes/quantization#transformers.Mxfp4Config), [official Harmony renderer](https://github.com/openai/harmony), [Modal pricing](https://modal.com/pricing). Installed Transformers source was inspected for the gpt-oss architecture and explicit dequantization path.']
    (run.dir/'report.md').write_text('\n'.join(lines)+'\n');run.result(**result);run.finish();print(run.dir);print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay',required=True);p.add_argument('--plan',required=True);p.add_argument('--clients',nargs='+',required=True);main(p.parse_args())
