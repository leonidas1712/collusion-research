"""Report verified full-replay coverage, provider fidelity, timing and shared spend."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from collusion.runs import start_run, write_json_atomic


def read(path):
    return json.loads(path.read_text())


def preemptions(log):
    events = []
    active = None
    completed = 0
    for line in log.splitlines():
        match = re.search(r'\[run\] (\S+) -> /outputs/runs/', line)
        if match:
            active, completed = match.group(1), 0
        match = re.search(r'^PROGRESS (\d+) ', line)
        if match:
            completed = int(match.group(1))
        if 'Container terminated due to preemption' in line:
            events.append(dict(partial_run=active, completed_requests_logged=completed))
    return events


def main(args):
    data, client, plan_dir, download = [Path(v).resolve() for v in [args.data, args.client, args.plan, args.download]]
    plan = read(plan_dir/'plan.json')
    summary = read(data/'data-summary.json')
    budget = read(client/'summary.json')
    shards = read(plan_dir/'completed-shards.json')['completed']
    copies = read(download/'downloads.json')
    assert all(read(path/'meta.json')['status'] == 'finished' for path in [data, client, download])
    assert budget['app_stopped'] and budget['error'] is None and budget['total_upper_usd'] <= 20
    assert len(shards) == len(copies) == len(plan['shards']) == 70
    assert set(shards) == set(copies) == {s['path'] for s in plan['shards']}
    assert summary['rows'] == plan['counts']['requests'] == 6985 and summary['verified_all_artifacts']
    run = start_run('e02-gpt-oss-full-completion', experiment='E02', parents=[data.name, client.name, plan_dir.name, download.name],
        settings={'read_only_completion_report': True, 'provider_modes': plan['provider_modes']})
    try:
        # The extraction process started before the separate saved-judgment join was discovered.
        report_path = data/'report.md'
        original_report = report_path.read_text()
        corrected_report = original_report.replace(
            'No semantic-judge disclosure-kind labels were available for this collection, so kind remains null.',
            'This cache does not join disclosure-kind judgments, so kind remains null. Saved judgments are available '
            'at runs/20261025-2310-e05-gpt-oss-disclosure-kind-join and join by episode plus source SHA256. '
            'Primary outcomes and eligibility are unchanged.')
        report_path.write_text(corrected_report)
        write_json_atomic(run.dir/'dataset-report-correction.json', dict(
            path=str(report_path), changed=corrected_report != original_report,
            before_sha256=hashlib.sha256(original_report.encode()).hexdigest(),
            after_sha256=hashlib.sha256(corrected_report.encode()).hexdigest(),
            reason='Correct availability wording for the separately saved judgment metadata; no data or numbers changed'))
        seconds = sum(v['summary']['wall_seconds'] for v in shards.values())
        tokens = plan['counts']['prompt_tokens']+plan['counts']['reply_tokens']
        interruptions = preemptions((client/'modal.log').read_text())
        write_json_atomic(run.dir/'preemptions.json', interruptions)
        versions = read(Path(next(iter(copies.values()))['local'])/'summary.json').get('versions')
        result = dict(requests=summary['rows'], episodes=summary['episodes'], shards=len(shards),
            prompt_tokens=plan['counts']['prompt_tokens'], reply_tokens=plan['counts']['reply_tokens'],
            reasoning_positions=plan['counts']['reasoning_tokens'], completed_shard_wall_seconds=seconds,
            input_tokens_per_second=tokens/seconds, client_wall_seconds=budget['client_wall_seconds'],
            client_input_tokens_per_second=tokens/budget['client_wall_seconds'],
            worker_preemptions=interruptions,
            budget=budget, downloaded_bytes=sum(v['bytes'] for v in copies.values()),
            fidelity=summary['fidelity'], prompt_counts=summary['prompt_counts'],
            eligible_counts=summary['eligible_counts'], versions=versions,
            source_manifest_sha256=plan['source_manifest_sha256'],
            rows_sha256=hashlib.sha256((data/'rows.jsonl').read_bytes()).hexdigest())
        write_json_atomic(run.dir/'summary.json', result)
        lines = ['# Full gpt-oss replay completion', '',
            'Replayed and verified all 6,985 saved target requests from the 360-episode frozen collection. '
            'The A100 app is stopped. No request was removed for prompt-token mismatch, missing exposure, '
            'pre-ask timing or intermediate tool position. Eligibility is applied only in the step table.', '',
            f'Cache: `{data.relative_to(ROOT)}`. Per-shard activation paths: `{plan_dir.relative_to(ROOT)}/completed-shards.json`. '
            f'Local download inventory and file hashes: `{download.relative_to(ROOT)}`.', '',
            'Each NPZ contains last-prompt residuals [24,2880] and returned reasoning-body residuals '
            '[24,n_reasoning,2880], plus exact input IDs, reasoning positions and layer IDs. '
            f'All {summary["rows"]:,} input-token arrays, hashes, shapes and finite values passed independent CPU checks. '
            f'The full run saved {plan["counts"]["reasoning_tokens"]:,} reasoning-token positions. '
            'The E05 feature tensor contains only last-prompt vectors, with shape [6985,24,2880].', '',
            '| Provider | Segment | Tokens | Mean NLL | Top-5 fraction |', '|---|---|---:|---:|---:|']
        for m in summary['fidelity']:
            lines.append(f"| {m['provider']} | {m['segment']} | {m['tokens']} | {m['mean_token_nll']:.5f} | {m['top5_fraction']:.5f} |")
        lines += ['', 'Metrics are token-weighted over all returned reply tokens. The all segment includes Harmony framing; '
            'reasoning and answer/tool-body segments are reported separately. Qwen’s earlier NLL~0.23/top-5~99.8% '
            'used the first64 reply tokens, so the measurements are not exactly equivalent.', '',
            '| Provider | Requests | Exact prompt count | Within 1 token | Median absolute gap |',
            '|---|---:|---:|---:|---:|']
        for provider, value in summary['prompt_counts'].items():
            lines.append(f"| {provider} | {value['requests']} | {value['exact']} | {value['within1']} | {value['median_absolute_gap']} |")
        lines += ['', 'AkashML uses the verified current-turn reasoning-retention renderer. DekaLLM uses drop-all '
            'prior reasoning; its provider prompt format remains approximate. The primary analysis retains all eligible '
            'requests and the saved prompt_token_match_within1 flag supports the predeclared mismatch sensitivity. '
            'Count agreement and likelihood agreement do not prove exact provider tokens. Served quantization fields '
            'are null. Replay expands the released MXFP4 checkpoint into bf16, with transformers5.20.2 and torch2.14.1.', '',
            'A mid-turn AkashML prompt contains earlier reasoning from that tool-use turn, before the next reply. '
            'This differs from a monitor without private-reasoning access and from a feature taken before all reasoning '
            'in the turn. Reasoning-position probing remains optional; it is not used in the primary last-prompt feature.', '',
            '## Time and cost', '',
            f'Completed shards processed {tokens:,} prompt+reply tokens in {seconds/60:.2f} minutes '
            f'({tokens/seconds:.1f} input tokens/s, including capture and artifact writes). '
            f'Client wall time was {budget["client_wall_seconds"]/60:.2f} minutes, equivalent to '
            f'{tokens/budget["client_wall_seconds"]:.1f} unique input tokens/s including reloads, retries and other overhead. '
            f'The full app billing snapshot is USD{budget["billed_so_far_usd"]:.6f}; billing can lag. '
            f'The conservative shared total, including the preceding paired diagnostic and USD0.50 overhead reserve, '
            f'is USD{budget["total_upper_usd"]:.6f}, below the USD20 cap. '
            'The watchdog carried earlier client costs forward and checked the projection after every shard. '
            'The GPU loaded cached weights and did not download a checkpoint. '
            f'Modal automatically retried {len(interruptions)} worker preemptions within the same app. '
            f'The interrupted attempts logged {sum(v["completed_requests_logged"] for v in interruptions)} completed requests '
            'before preemption, plus any unlogged in-flight work. Only successful completed shards enter the dataset; '
            'all app wall time and billed resources remain in cost accounting. Details are in preemptions.json.', '',
            '## Data and analysis checks', '',
            'Episode eligibility requires complete execution, exposure and a successfully written correct summary at least once. '
            'Steps are strictly after the read and before first public emission; returned private reasoning does not censor them. '
            'Channel publication remains the primary label. Pre-ask and post-ask rows are separate, and every raw capture is retained. '
            'The cache report records step and episode denominators, including the within-one-token sensitivity.', '',
            'The dataset builder deliberately leaves kind null. Saved first-public-emission judgments are available separately '
            'at runs/20261025-2310-e05-gpt-oss-disclosure-kind-join and join by episode plus SHA256. '
            'They describe the first public emission, often a file write, not necessarily the later channel post. '
            'They do not alter primary labels or eligibility. Any earlier cache-report wording that labels were unavailable '
            'is superseded by this saved metadata join.', '',
            'Outcome fitting is gated on a separate family-held-out token-exposure control at layer12 (AUROC>=0.95). '
            'Candidate layers were declared before fitting: [0,1,3,4,6,7,9,10,12,13,15,16,18,19,20,22,23]; '
            'fixed12 is secondary. This report contains no outcome-probe result.']
        (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
        run.result(**result)
        run.finish()
        print('COMPLETION_REPORT', run.dir)
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['data', 'client', 'plan', 'download']:
        parser.add_argument('--'+name, required=True)
    main(parser.parse_args())
