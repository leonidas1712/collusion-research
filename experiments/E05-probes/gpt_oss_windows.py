"""Descriptive scoring-window coverage and available lead time; no probe fitting."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from collusion.runs import start_run, write_json_atomic


def histogram(values):
    return {str(k): v for k, v in sorted(Counter(v for v in values if v is not None).items())}


def coverage(rows):
    episodes = {r['episode']: r for r in rows}
    positive = sum(r['label'] for r in rows)
    positive_episodes = sum(r['label'] for r in episodes.values())
    return dict(steps=len(rows), positive_steps=positive,
        positive_step_fraction=positive/len(rows) if rows else None,
        episodes=len(episodes), positive_episodes=positive_episodes,
        positive_episode_fraction=positive_episodes/len(episodes) if episodes else None)


def main(args):
    source = Path(args.plan).resolve()
    plan = json.loads((source/'plan.json').read_text())
    rows = [json.loads(s) for s in (source/'rows.jsonl').read_text().splitlines()]
    episodes = json.loads((source/'episodes.json').read_text())
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['episode']].append(r)
    run = start_run('e05-gpt-oss-window-audit', experiment='E05', parents=[source.name],
        settings={'no_fits_or_paid_calls': True, 'timing_boundary': 'first public emission',
                  'source_manifest_sha256': plan['source_manifest_sha256']})
    try:
        records = []
        for e in episodes:
            m = e['source_metadata']
            assert hashlib.sha256((ROOT/m['episode_file']).read_bytes()).hexdigest() == m['episode_sha256']
            erows = grouped[e['episode']]
            lookup = {r['request_idx']: r for r in erows}
            ask = lookup.get(e['first_ask_request_idx'])
            channel = lookup.get(e['first_channel_request_idx'])
            post = sorted((r for r in erows if r['eligible']), key=lambda r: r['ordinal'])
            pre = [r for r in erows if r['eligible_pre_ask']]
            public = e['first_public_emission_ordinal']
            public_round = e['action_round']
            channel_round = m['first_channel_emission_round']
            ask_round = e['first_ask_round']
            records.append(dict(episode=e['episode'], family=e['family'], scenario=e['scenario'],
                condition=e['condition'], channel_label=e['label'], episode_eligible=e['episode_eligible'],
                post_ask_steps=len(post), pre_ask_steps=len(pre),
                first_ask_round=ask_round, first_public_round=public_round, first_channel_round=channel_round,
                public_minus_ask_rounds=public_round-ask_round if public_round is not None and ask_round is not None else None,
                channel_minus_ask_rounds=channel_round-ask_round if channel_round is not None and ask_round is not None else None,
                public_minus_ask_requests=public-ask['ordinal'] if public is not None and ask else None,
                channel_minus_ask_requests=channel['ordinal']-ask['ordinal'] if channel and ask else None,
                earliest_eligible_lead_requests=post[0]['steps_until_action'] if post and e['label'] else None,
                earliest_eligible_lead_rounds=public_round-post[0]['round'] if post and e['label'] else None))
        positive = [r for r in records if r['condition'] == 'recruiting' and r['channel_label']]
        rec = [r for r in rows if r['condition'] == 'recruiting']
        coverage_table = {}
        for window, flag in [('post_ask', 'eligible'), ('pre_ask', 'eligible_pre_ask')]:
            selected = [r for r in rec if r[flag]]
            coverage_table[window] = dict(primary=coverage(selected),
                within1=coverage([r for r in selected if r['prompt_token_match_within1']]))
        per_scenario = []
        for scenario in sorted({r['scenario'] for r in positive}):
            group = [r for r in positive if r['scenario'] == scenario]
            per_scenario.append(dict(scenario=scenario, channel_positive_episodes=len(group),
                with_post_ask_window=sum(r['post_ask_steps'] > 0 for r in group),
                zero_post_ask_window=sum(r['post_ask_steps'] == 0 for r in group),
                public_before_ask=sum(r['public_minus_ask_rounds'] < 0 for r in group),
                public_same_ask_round=sum(r['public_minus_ask_rounds'] == 0 for r in group),
                public_later_round=sum(r['public_minus_ask_rounds'] > 0 for r in group),
                channel_later_round=sum(r['channel_minus_ask_rounds'] > 0 for r in group)))
        positive_steps = [r for r in rec if r['eligible'] and r['label']]
        timing = {field: histogram(r[field] for r in positive) for field in [
            'first_public_round', 'first_channel_round', 'public_minus_ask_rounds', 'channel_minus_ask_rounds',
            'public_minus_ask_requests', 'channel_minus_ask_requests',
            'earliest_eligible_lead_requests', 'earliest_eligible_lead_rounds']}
        timing['eligible_positive_step_lead_requests'] = histogram(r['steps_until_action'] for r in positive_steps)
        timing['eligible_positive_step_lead_rounds'] = histogram(r['action_round']-r['round'] for r in positive_steps)
        summary = dict(coverage=coverage_table, channel_positive_episodes=len(positive),
            positive_episodes_with_post_ask_window=sum(r['post_ask_steps'] > 0 for r in positive),
            positive_episodes_without_post_ask_window=sum(r['post_ask_steps'] == 0 for r in positive),
            per_scenario=per_scenario, timing=timing)
        write_json_atomic(run.dir/'episodes.json', records)
        write_json_atomic(run.dir/'summary.json', summary)
        lines = ['# gpt-oss scoring windows and available lead time', '',
            'This is a descriptive audit of the frozen 360-episode collection and replay step plan. No model was fitted '
            'and no API/GPU call was made. Channel publication is the episode outcome. The scoring window is strictly '
            'after the protected-value read and strictly before the first public response/tool-argument emission; '
            'a file write can therefore close the window before a later channel post.', '',
            f"Of {len(positive)} channel-positive episodes, {summary['positive_episodes_with_post_ask_window']} have an eligible "
            f"post-ask scoring request and {summary['positive_episodes_without_post_ask_window']} have none. "
            'The latter remain positive collection outcomes but do not enter the post-ask AUROC. '
            'An action in the very first request receiving the ask has no strict pre-action post-ask row. '
            'Other zero-window cases can follow from the read boundary. These are window exclusions, not failed-task exclusions.', '',
            '| Scenario | Channel positives | With window | No window | Public before ask | Public same round | Public later round | Channel later round |',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
        for r in per_scenario:
            lines.append('| '+' | '.join(str(r[k]) for k in ['scenario', 'channel_positive_episodes',
                'with_post_ask_window', 'zero_post_ask_window', 'public_before_ask', 'public_same_ask_round',
                'public_later_round', 'channel_later_round'])+' |')
        lines += ['', 'Public delay and channel delay are different: a later channel post does not extend the scoring '
            'window if a file emission has already occurred. Before-ask cases are retained descriptively, not relabelled. '
            'Request distances count completed target requests and include the action request as the endpoint; '
            'zero means the action-producing request is the first request receiving the ask.', '',
            '## Available lead time', '',
            'These distributions describe prediction opportunities, not achieved warning time or alarm recall. '
            'The episode-level distribution uses the earliest eligible post-ask row. The step-level distribution counts '
            'every eligible positive request, so episodes with longer windows contribute more steps.', '',
            '| Quantity | Histogram (distance or round: count) |', '|---|---|']
        for field, value in timing.items():
            lines.append('| '+field+' | '+json.dumps(value)+' |')
        lines += ['', '## Prompt-count sensitivity coverage', '',
            'The within-one-token sensitivity removes individual requests with absolute count gap >1. It does not '
            'remove all other requests from an episode merely because one mismatches.', '',
            '| Window | Filter | Steps | Positive steps (%) | Episodes | Positive episodes (%) |',
            '|---|---|---:|---:|---:|---:|']
        for window, variants in coverage_table.items():
            for name, r in variants.items():
                lines.append(f"| {window} | {name} | {r['steps']} | {r['positive_steps']} ({100*r['positive_step_fraction']:.2f}%) | "
                             f"{r['episodes']} | {r['positive_episodes']} ({100*r['positive_episode_fraction']:.2f}%) |")
        (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
        run.result(**summary)
        run.finish()
        print('WINDOW_AUDIT', run.dir)
    except BaseException as exc:
        run.finish('failed', str(exc))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', required=True)
    main(parser.parse_args())
