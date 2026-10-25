"""Produce numerical summaries and privacy audits for combined-tactic API episodes."""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path

from gemma_pressure_prompts import ROOT, FAMILIES
from gemma_report import summarize, episodes
from gemma_pressure_audit import audit
from collusion.runs import start_run, write_json_atomic


def cells(parent):
    result = {}
    for cell in json.loads((parent / 'cells.json').read_text()):
        directory = ROOT / 'runs' / cell
        settings = json.loads((directory / 'meta.json').read_text())['settings']
        summary = summarize(directory)
        costs = Decimal(0)
        calls, errors, models = Counter(), Counter(), Counter()
        audits = []
        for path, ep in episodes(directory):
            audits.append({'path': str(path.relative_to(ROOT)), **audit(ep)})
            for request in ep['requests']:
                if request.get('error'):
                    errors[request['actor'] + '/' + request['error']['type']] += 1
                response = request.get('response') or {}
                if response:
                    models[request['actor'] + '/' + str(response.get('model'))] += 1
                    meta = response.get('screen_serving_metadata') or {}
                    calls[request['actor'] + '/' + str(response.get('provider')) + '/' +
                          str(meta.get('endpoint_precision_candidates', []))] += 1
                    costs += Decimal(str((response.get('usage') or {}).get('cost') or 0))
        valid_read = [r for r in summary['episodes'] if r['valid'] and r['read']]
        summary.update(source_run=cell, valid_read=len(valid_read),
                       give_in_rate_after_read=(summary['gave_in_after_read'] / len(valid_read)
                                               if valid_read else None),
                       response_cost_usd=str(costs), request_errors=dict(errors),
                       calls_by_actor_provider_catalog_precision=dict(calls),
                       calls_by_actor_served_model=dict(models), privacy_audits=audits,
                       failures_by_actor_cause=dict(Counter(
                           str(r['failure_actor']) + '/' + str(r['stop_reason'])
                           for r in summary['episodes'] if r['status'] != 'complete')))
        result[settings['family'] + '/' + settings['condition']] = summary
    return result


def main(args):
    parent = ROOT / 'runs' / args.run
    lineage = [args.run, *([args.plain_run] if args.plain_run else [])]
    qwen = {}
    for family in FAMILIES:
        for condition in ('recruiting', 'control'):
            prefix = ('20261024-2103-e01-deploy-token-v2' if family == 'deploy-token-v2'
                      else f'20261024-2338-e01-spray-{family}')
            name = f'{prefix}-consequence-{condition}-32b-scaleup'
            lineage.append(name)
            qwen[family + '/' + condition] = {'source_run': name, **summarize(ROOT / 'runs' / name)}
    run = start_run('e03-gemma-pressure-metrics', experiment='E03', settings=vars(args),
                    parents=lineage, tags=['combined-tactics', 'numerical-summary'])
    ledgers = []
    for value in [str(parent / 'budget.json'), *args.budget]:
        path = Path(value).resolve()
        ledger = json.loads(path.read_text())
        ledgers.append({'path': str(path.relative_to(ROOT)),
                        'billed': ledger.get('reported_cost_usd', ledger.get('billed', '0')),
                        'charged_or_reserved': ledger.get('charged_or_reserved_usd',
                                                         ledger.get('charged_or_reserved', '0'))})
    result = {'combined_tactics': cells(parent), 'qwen_plain': qwen,
              'gemma_plain': cells(ROOT / 'runs' / args.plain_run) if args.plain_run else None,
              'cost_ledgers': ledgers,
              'total_billed_usd': str(sum(Decimal(x['billed']) for x in ledgers)),
              'total_charged_or_reserved_usd': str(sum(Decimal(x['charged_or_reserved']) for x in ledgers))}
    write_json_atomic(run.dir / 'metrics.json', result)
    run.result(cells=len(result['combined_tactics']))
    run.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--plain-run')
    parser.add_argument('--budget', action='append', default=[])
    main(parser.parse_args())
