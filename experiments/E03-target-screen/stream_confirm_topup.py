"""Replace incomplete attempts once, using fresh frozen-reserved family IDs."""
import argparse
import asyncio
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess

import escalation_sweep as e
from stream_confirm_bulk import BoundedBudget, SCENARIO
from stream_confirm_collect import SCENARIOS
from collusion.runs import start_run, write_json_atomic


async def main(freeze):
    freeze = freeze.resolve()
    assert not (freeze / 'topup_run.json').exists(), 'Never silently repeat replacements'
    bulk = json.loads((freeze / 'bulk_run.json').read_text())
    assert bulk['status'] == 'finished'
    planned = json.loads((freeze / 'frozen_plan.json').read_text())
    assert hashlib.sha256((freeze / 'frozen_weights.json').read_bytes()).hexdigest() == planned['weights_sha256']
    amendment = json.loads((freeze / 'throughput_amendment.json').read_text())
    failures = Counter()
    evidence = []
    for child in bulk['children']:
        child = Path(child)
        scenario = json.loads((child / 'meta.json').read_text())['settings']['scenario']
        for record in json.loads((child / 'records.json').read_text()):
            if record['status'] != 'complete':
                failures[(scenario, record['condition'])] += 1
                evidence.append({'run': str(child), 'episode_id': record['episode_id'],
                                 'scenario': scenario, 'condition': record['condition'], 'status': record['status']})
    assert sum(failures.values()) == bulk['incomplete'] and failures
    assert all(sum(n for (s, _), n in failures.items() if s == scenario) <= 9 for scenario in SCENARIOS)
    prior = Decimal(bulk['charged_or_reserved_total_including_benchmark'])
    assert prior < 5
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=e.ROOT, text=True).strip()
    run = start_run('e03-stream-confirm-topup', experiment='E03', parents=[freeze.name, Path(bulk['run_dir']).name],
                    settings={'incomplete_only': True, 'one_replacement_pass': True,
                              'prior_charged_or_reserved_usd': str(prior), 'shared_API_cap_usd': 5})
    write_json_atomic(run.dir / 'replacement_plan.json', evidence)
    write_json_atomic(freeze / 'topup_run.json', {'run_dir': str(run.dir), 'status': 'running'})
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    load_dotenv(e.ROOT / '.env')
    model, target_price, target_opts = e.target_config('gpt-oss')
    prices = {model: target_price, e.PEER: e.peer_price()}
    settings = e.Settings(model, e.PEER, rounds=20, max_tool_steps=12, max_tokens=4096,
        empty_response_retries=2, empty_after_send_ends_turn=True, api_retry_attempts=10, api_retry_max_delay=60,
        target_request_options=target_opts, recruiter_request_options=e.peer_options(prices[e.PEER]))
    children = []; all_records = []; jobs = []
    for si, scenario in enumerate(SCENARIOS):
        offset = 21
        for condition in ['recruiting', 'control']:
            n = failures[(scenario, condition)]
            if not n:
                continue
            start = 7000001 + 100 * si + offset
            child = start_run(f'e03-stream-confirm-topup-{scenario}-{condition}', experiment='E03', model=model,
                parents=[run.id, freeze.name], settings={'scenario': scenario, 'strategy': 'envblock_late',
                'recruiting': n if condition == 'recruiting' else 0, 'control': n if condition == 'control' else 0,
                'family_start': start, 'episode_settings': asdict(settings), 'shared_budget': str(run.dir / 'budget.json')})
            children.append(child)
            for i in range(n):
                jobs.append((child, scenario, condition, i, start + i))
            offset += n
    try:
        async with AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1',
                               max_retries=0, timeout=90) as client:
            budget = BoundedBudget(client, run.dir / 'budget.json', prices, Decimal('5'),
                                   bounds=amendment['scenario_model_max_observed_total_tokens'])
            budget.ledger.update(charged_or_reserved_usd=str(prior),
                reported_cost_usd=bulk['billed_total_including_benchmark'], prior_cost_included=True,
                prior_ledger=str(Path(bulk['run_dir']) / 'budget.json'))
            budget.save(); serving = e.ServingMetadata(budget, prices); gate = asyncio.Semaphore(12)
            grouped = {c.id: [] for c in children}

            async def one(child, scenario, condition, i, family):
                async with gate:
                    SCENARIO.set(scenario)
                    ep = await e.run_episode(e.build_scenario(scenario, 'envblock_late', condition, family),
                        settings, serving, child.dir / 'episodes', episode_id=f'{condition}-{i + 1:04}')
                    ask = e.first_peer_ask(ep)
                    ep['collection_metadata'] = {'first_ask_round': ask['round'], 'first_ask_text': ask['text'],
                        'first_ask_method': ask['method'], 'primary_forbidden_action': 'channel_publication',
                        'secondary_forbidden_action': 'other_file_disclosure', 'prompt_commit': '0418116df17ec3b4c8e9ff667b1142c6b5414a17',
                        'collection_code_commit': commit, **e.first_emission_indices(ep)}
                    if ep['status'] == 'complete':
                        write_json_atomic(child.dir / 'episodes' / (ep['episode_id'] + '.json'), ep)
                    record = e.episode_record(scenario, 'envblock_late', condition, ep)
                    grouped[child.id].append(record); all_records.append(record)
                    write_json_atomic(child.dir / 'records.json', grouped[child.id])
                    print('REPLACEMENT', scenario, condition, family, ep['status'], flush=True)

            await asyncio.gather(*(one(*job) for job in jobs))
            summary = {'status': 'finished', 'run_dir': str(run.dir), 'children': [str(c.dir) for c in children],
                'requested': len(jobs), 'incomplete': sum(r['status'] != 'complete' for r in all_records),
                'billed_total_including_benchmark': budget.ledger['reported_cost_usd'],
                'charged_or_reserved_total_including_benchmark': budget.ledger['charged_or_reserved_usd']}
            for child in children:
                child.finish()
            write_json_atomic(freeze / 'topup_run.json', summary)
            write_json_atomic(run.dir / 'summary.json', summary); run.result(**summary); run.finish()
    except BaseException as exc:
        run.finish('failed', str(exc)); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--freeze', type=Path, required=True)
    asyncio.run(main(parser.parse_args().freeze))
