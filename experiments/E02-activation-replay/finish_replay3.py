"""Download a completed replay3, verify it, and assemble caches without outcome fitting."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run


def main(args):
    os.environ['PATH'] = str(ROOT / '.venv/bin') + os.pathsep + os.environ['PATH']
    run = start_run('e02-replay3-completion', experiment='E02', parents=[args.plan, args.client], settings=vars(args))
    e02 = ROOT / 'experiments/E02-activation-replay'
    e05 = ROOT / 'experiments/E05-probes'
    products = {}

    def command(name, argv, marker=None):
        print('START', name, flush=True)
        result = subprocess.run(list(map(str, argv)), cwd=ROOT, capture_output=True, text=True)
        (run.dir / f'{name}.stdout.txt').write_text(result.stdout)
        (run.dir / f'{name}.stderr.txt').write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f'{name} failed ({result.returncode}); see saved stdout/stderr')
        if marker:
            matches = [line.split()[-1] for line in result.stdout.splitlines() if line.startswith(marker)]
            assert len(matches) == 1, (name, matches)
            products[name] = matches[0]
            (run.dir / 'products.json').write_text(json.dumps(products, indent=2))
        print('DONE', name, products.get(name, ''), flush=True)
        return result.stdout

    try:
        client_path = ROOT / 'runs' / args.client / 'summary.json'
        deadline = time.monotonic() + 125 * 60
        while not client_path.exists():
            if time.monotonic() > deadline:
                raise TimeoutError('Main client did not finish within 125 minutes')
            time.sleep(5)
        client = json.loads(client_path.read_text())
        benchmark_client = json.loads((ROOT / 'runs' / args.benchmark_client / 'summary.json').read_text())
        assert client['app_stopped'] and client['error'] is None
        assert benchmark_client['app_stopped'] and benchmark_client['error'] is None
        upper = client['conservative_compute_upper_usd'] + benchmark_client['conservative_compute_upper_usd'] + .50
        assert upper < 7, upper
        remote = client['remote_path']
        main_id = Path(remote).name
        products['main_replay'] = main_id
        command('download', [ROOT / '.venv/bin/python', e02 / 'download_volume.py', remote, '--workers', '32'])
        command('validation', [e02 / '.venv/bin/python', e02 / 'verify_main.py', ROOT / 'runs' / main_id,
                               '--manifest', ROOT / 'runs' / args.plan / 'remaining.jsonl'], '2026')
        command('new_data', [e05 / '.venv/bin/python', e05 / 'replay3_data.py', args.benchmark, main_id,
                             '--plans', args.plan], 'DATA_RUN')
        command('exposure_gate', [e05 / '.venv/bin/python', e05 / 'replay3_positive_control.py', products['new_data']], 'CONTROL_RUN')
        gate = json.loads((ROOT / 'runs' / products['exposure_gate'] / 'summary.json').read_text())
        assert gate['gate_passed'] and gate['gate_auc'] >= .95
        command('combined_data', [e05 / '.venv/bin/python', e05 / 'replay3_data.py',
                                  '20261024-1721-e02-activation-replay', '20261024-1727-e02-activation-replay',
                                  args.benchmark, main_id, '--plans', '20261025-0119-e02-replay2-plan', args.plan], 'DATA_RUN')
        command('prefix_check', [e05 / '.venv/bin/python', e05 / 'verify_replay3_prefix.py', products['combined_data'], products['new_data']], 'PREFIX_RUN')
        billing = json.loads(command('billing', ['modal', 'billing', 'report', '--for', 'today', '--resolution', 'h', '--show-resources', '--json']))
        app_ids = {client['app_id'], benchmark_client['app_id']}
        billing = [row for row in billing if row.get('object_id') in app_ids]
        (run.dir / 'billing.json').write_text(json.dumps(billing, indent=2))
        summaries = [json.loads((ROOT / 'runs' / name / 'summary.json').read_text()) for name in [args.benchmark_validation, products['validation']]]
        replies = sum(s['reply_tokens'] for s in summaries)
        new_data = json.loads((ROOT / 'runs' / products['new_data'] / 'summary.json').read_text())
        combined = json.loads((ROOT / 'runs' / products['combined_data'] / 'summary.json').read_text())
        result = dict(products=products, new_data=new_data, combined_data=combined,
                      weighted_nll=sum(s['weighted_nll'] * s['reply_tokens'] for s in summaries) / replies,
                      weighted_top5=sum(s['weighted_top5'] * s['reply_tokens'] for s in summaries) / replies,
                      scored_reply_tokens=replies, exposure_gate_auc=gate['gate_auc'],
                      conservative_total_upper_usd=upper, billed_snapshot_usd=sum(float(r['cost']) for r in billing),
                      cap_usd=7, all_apps_stopped=True, billing_may_lag=True)
        (run.dir / 'summary.json').write_text(json.dumps(result, indent=2))
        report = f"""# Replay3 results

Replayed {new_data['rows']:,} target requests from {new_data['real_episodes']} complete balanced-batch episodes through pinned Qwen3-32B bf16 on A100-80GB, saving all 64 decoder layers at the last prompt token. Both Modal apps are stopped.

- Integrity: every request, prompt, token and episode hash matched its frozen manifest; all arrays were finite and correctly shaped.
- Reply fidelity: token-weighted NLL {result['weighted_nll']:.6f}; top-five fraction {result['weighted_top5']:.6f} over {replies:,} scored tokens.
- Layer-32 exposure gate: family-held-out AUROC {gate['gate_auc']:.6f}, above the fixed 0.95 gate. No outcome or near-term probes were fitted or evaluated.
- New data: {new_data['eligible_rows']:,} eligible steps from {new_data['eligible_episodes']} episodes. Cache: `runs/{products['new_data']}`.
- Combined data: {combined['rows']:,} rows, {combined['eligible_rows']:,} eligible steps. Cache: `runs/{products['combined_data']}`. The old 6,026-row prefix is unchanged in metadata, order and features; new rows are appended and reindexed.
- Cost snapshot: USD {result['billed_snapshot_usd']:.4f}; conservative compute bound plus USD0.50 overhead: USD {upper:.2f}, below the USD7 cap. Billing can lag.

Plan: `runs/{args.plan}`. Benchmark validation: `runs/{args.benchmark_validation}`. Main validation: `runs/{products['validation']}`. Exposure gate: `runs/{products['exposure_gate']}`. Prefix verification: `runs/{products['prefix_check']}`.

These are HF reconstructions, not proof of equality with the provider's private tokenization, template, kernels or quantization. Outcome analysis of the confirmation set is reserved for the frozen confirmatory plan.
"""
        (run.dir / 'report.md').write_text(report)
        run.result(**result)
        run.finish()
        print('COMPLETION_RUN', run.id, flush=True)
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', required=True)
    parser.add_argument('--client', required=True)
    parser.add_argument('--benchmark', default='20261025-0041-e02-activation-replay')
    parser.add_argument('--benchmark-client', default='20261025-0841-e02-replay3-modal-client')
    parser.add_argument('--benchmark-validation', default='20261025-0853-e02-main-replay-validation')
    main(parser.parse_args())
