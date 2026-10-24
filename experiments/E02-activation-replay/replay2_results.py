"""Record verified replay2 fidelity, throughput and the two stopped apps' billing."""
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def main():
    clients=['20261025-0121-e02-replay2-modal-client','20261025-0126-e02-replay2-modal-client']
    validations=['20261025-0126-e02-main-replay-validation','20261025-0336-e02-main-replay-validation']
    run=start_run('e02-replay2-results',experiment='E02',parents=clients+validations,settings={'approved_cap_usd':12,'noncompute_allowance_usd':.50,'billing_snapshot_may_lag':True})
    try:
        client=[json.loads((ROOT/'runs'/name/'summary.json').read_text()) for name in clients];parts=[json.loads((ROOT/'runs'/name/'summary.json').read_text()) for name in validations]
        assert all(c['app_stopped'] and c['error'] is None for c in client);assert all(p['manifest_hashes_match'] for p in parts)
        app_ids={c['app_id'] for c in client}
        billing=json.loads(subprocess.run(['modal','billing','report','--for','today','--resolution','h','--show-resources','--json'],check=True,capture_output=True,text=True).stdout)
        selected=[r for r in billing if r.get('object_id') in app_ids];(run.dir/'billing.json').write_text(json.dumps(selected,indent=2))
        reply=sum(p['reply_tokens'] for p in parts);prompt=sum(p['prompt_tokens'] for p in parts);decoder=sum(p['decoder_seconds'] for p in parts);processing=sum(p['processing_seconds'] for p in parts);wall=sum(c['client_wall_seconds'] for c in client)
        result=dict(requests=sum(p['requests'] for p in parts),prompt_tokens=prompt,reply_tokens=reply,
            weighted_nll=sum(p['weighted_nll']*p['reply_tokens'] for p in parts)/reply,weighted_top5=sum(p['weighted_top5']*p['reply_tokens'] for p in parts)/reply,
            decoder_seconds=decoder,processing_seconds=processing,client_wall_seconds=wall,prompt_tokens_per_decoder_second=prompt/decoder,input_tokens_per_decoder_second=(prompt+reply)/decoder,prompt_tokens_per_processing_second=prompt/processing,prompt_tokens_per_client_wall_second=prompt/wall,
            billed_by_app={app:sum(float(r['cost']) for r in selected if r['object_id']==app) for app in sorted(app_ids)},billed_app_total_usd=sum(float(r['cost']) for r in selected),
            conservative_compute_upper_usd=sum(c['conservative_compute_upper_usd'] for c in client),noncompute_allowance_usd=.50,
            conservative_total_upper_usd=sum(c['conservative_compute_upper_usd'] for c in client)+.50,cap_usd=12,all_apps_stopped=True,billing_may_lag=True,
            artifact_bytes=sum(p['artifact_bytes'] for p in parts),real_episodes=268,shared_history_prompts=23,model='Qwen/Qwen3-32B',revision='9216db5781bf21249d130ec9da846c4624c16137',precision='bf16',layers=64)
        assert result['conservative_total_upper_usd']<12 and result['billed_app_total_usd']<12
        (run.dir/'summary.json').write_text(json.dumps(result,indent=2));run.result(**result)
        text=f"""# Replay2 results

All **6,026 requests** passed manifest and artifact verification: 6,003 actual target calls from 268 complete episodes, plus 23 shared pre-peer branching states. Both Modal apps are stopped. Model: Qwen3-32B@{result['revision']}, bf16 A10080; all 64 decoder outputs at the true last prompt token. The replay used independent forward passes, with cached weights and no generation.

- Prompt tokens: {prompt:,}; scored reply tokens: {reply:,} (up to 64 per actual reply).
- Token-weighted reply NLL: **{result['weighted_nll']:.6f}**; top-five fraction: **{result['weighted_top5']:.6f}**. The 23 shared states have no actual next reply and correctly have missing-response diagnostics.
- Combined client wall time: {wall/60:.2f} minutes, including benchmark/main startup and cleanup. Decoder time: {decoder/60:.2f} minutes; per-request processing time: {processing/60:.2f} minutes.
- Throughput: {prompt/decoder:,.0f} prompt tokens/s of decoder time; {(prompt+reply)/decoder:,.0f} total input tokens/s of decoder time; {prompt/processing:,.0f} prompt tokens/s of request-processing time; {prompt/wall:,.0f} prompt tokens/s of client wall time.
- Billed app total at this snapshot: **USD {result['billed_app_total_usd']:.4f}** (billing can lag; see billing.json). Conservative benchmark + main compute upper bound plus USD0.50 for transfer/storage and other overhead: **USD {result['conservative_total_upper_usd']:.2f}**, below the approved USD12 cap.

Verification runs: `{validations[0]}`, `{validations[1]}`. Combined data: `20261025-0337-e05-replay2-data`. The download was deliberately resumed with 32 parallel reads to reduce small-file latency, preserving atomic completed files; this was a transport restart, not a GPU replay or failed integrity check.

HF prompt and input-token hashes match the frozen manifest. Equal provider/HF token counts and low reply NLL support fidelity but do not reveal or prove equality with the provider's private template, exact tokens or quantization. The extraction gate and outcome analyses are separate E05 runs.
"""
        (run.dir/'report.md').write_text(text);run.finish();print(json.dumps(result,indent=2));print('REPLAY2_RESULTS',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
