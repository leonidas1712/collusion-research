"""Resample one target tool turn from saved first-ask prefixes; never call the peer."""
import argparse
import asyncio
from collections import Counter
import copy
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import sys

from harness import FakeClient, Settings, run_episode, standard_tools
from scenarios import get_scenario, POLICY_VARIANTS, _first_peer_ask, score_deploy_token

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run, write_json_atomic

MODELS = {
    'granite': ('ibm-granite/granite-4.2-8b', 'CoreWeave', 'bf16'),
    'nemo': ('mistralai/mistral-nemo', 'Io Net', 'fp16'),
}
POLICIES = ('none', 'explicit', 'firm', 'norm', 'soft')


def prepare(source, policy):
    episode = json.loads(Path(source).read_text())
    spec = episode['scenario_spec']
    if spec['scenario_version'] != 'staging-6':
        raise ValueError('Requires staging-6 sources')
    original = get_scenario(spec['name'], spec['metadata']['family_id'])
    if spec['files'] != original.files or spec['target_system'] != original.target_system:
        raise ValueError('Source files or system differ from the declared scenario')
    if spec['tools'] != [tool.schema for tool in standard_tools()]:
        raise ValueError('Source tools differ from current harness')
    request = next(r for r in episode['requests'] if r['actor'] == 'target')
    messages = copy.deepcopy(request['request']['messages'])
    if len(messages) != 3 or [m['role'] for m in messages] != ['system', 'user', 'user']:
        raise ValueError('First ask must precede all target output')
    peer = episode['channel'][0]
    if peer['actor'] != 'recruiter' or _first_peer_ask([peer]) is None:
        raise ValueError('Source must begin with a peer ask')
    if messages[2]['content'] != original.channel_format.format(
            actor='recruiter', name=original.actor_names['recruiter'], content=peer['content']):
        raise ValueError('Saved first request does not match first peer ask')
    variant = get_scenario(f"deploy-token_{policy}_{spec['metadata']['goal_relation']}_{spec['metadata']['peer_condition']}",
                           spec['metadata']['family_id'])
    if not variant.recruiter_approved:
        raise ValueError('Policy wording awaits approval')
    messages[0]['content'] = variant.target_system
    metadata = {**variant.metadata, 'execution': 'frozen_peer_first_ask_target_turn',
                'source_episode': str(Path(source).relative_to(ROOT)),
                'source_policy': spec['metadata']['policy']}
    scenario = replace(variant, peer_enabled=False, files=copy.deepcopy(spec['files']),
                       metadata=metadata)
    return scenario, {'messages': messages, 'channel': [copy.deepcopy(peer)]}


def summarize(results):
    rows = []
    for model in MODELS:
        for policy in POLICIES:
            group = [e for e in results if e['condition']['sweep_model'] == model
                     and e['condition']['policy'] == policy]
            counts = Counter()
            for e in group:
                if e['status'] != 'complete':
                    counts['incomplete'] += 1
                    continue
                label = score_deploy_token(e)
                counts[label['disclosure_kind']] += 1
                counts['token_in_context'] += int(label['token_in_context'])
            rows.append({'model': model, 'policy': policy, 'n': len(group), **dict(counts)})
    return rows


async def main(args):
    sources = sorted((ROOT / args.source / 'episodes').glob('episode-*.json'))
    if len(sources) != 5:
        raise ValueError('Expected five source episodes')
    prepared = {(str(source), policy): prepare(source, policy)
                for source in sources for policy in POLICIES}
    run = start_run('e01-deploy-token-policy-sweep', experiment='E01',
                    settings={**vars(args), 'scenario_family': 'deploy-token'},
                    parents=[args.source.name], tags=['wiring' if args.fake else 'policy-sweep'],
                    model=','.join(value[0] for value in MODELS.values()))
    if args.fake:
        client = FakeClient()
    else:
        from dotenv import load_dotenv
        from openai import AsyncOpenAI
        load_dotenv(ROOT / '.env')
        client = AsyncOpenAI(api_key=os.environ['OPENROUTER_API_KEY'],
                             base_url='https://openrouter.ai/api/v1', max_retries=0, timeout=90)
    results = []
    semaphore = asyncio.Semaphore(2)

    async def draw(source, sample, model, model_id, provider, quantization, policy):
        scenario, prefix = prepared[str(source), policy]
        scenario = replace(scenario, metadata={**scenario.metadata,
                           'sweep_model': model, 'sample': sample + 1})
        settings = Settings(model_id, 'unused', rounds=1, max_tokens=1536, parallelism=2,
                            target_request_options={'extra_body': {
                                'reasoning': {'enabled': False}, 'provider': {
                                    'order': [provider], 'allow_fallbacks': False,
                                    'quantizations': [quantization]}}})
        result = await run_episode(scenario, settings, client, run.dir / 'episodes',
                                   f'{model}-{policy}-{sample+1:02}', semaphore, target_prefix=prefix)
        results.append(result)
        write_json_atomic(run.dir / 'summary.json', summarize(results))
        print(model, policy, sample + 1, result['status'],
              (result.get('label') or {}).get('disclosure_kind'), flush=True)

    try:
        # First ten samples provide one live smoke check per model/policy cell.
        for sample in range(args.samples):
            source = sources[sample % len(sources)]
            await asyncio.gather(*(draw(source, sample, model, *configuration, policy)
                                   for model, configuration in MODELS.items() for policy in POLICIES))
            if sample == 0 and any(e['status'] != 'complete' for e in results):
                raise RuntimeError('First-sample smoke check failed; inspect traces before scaling')
        cost = sum((r.get('usage') or {}).get('cost', 0) or 0 for e in results for r in e['requests'])
        run.result(summary=summarize(results), reported_cost=cost, samples=len(results))
        run.finish('finished' if all(e['status'] == 'complete' for e in results) else 'failed')
        print('RUN', run.id, 'REPORTED_COST', cost, flush=True)
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise
    finally:
        if not args.fake:
            await client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('runs/20261024-0032-e01-harness'))
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--fake', action='store_true')
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('--samples must be positive')
    asyncio.run(main(args))
