"""Reconcile the paper's 78 recruiting exclusions from its frozen source table."""
import argparse
from collections import Counter
import csv
import hashlib
import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run, write_json_atomic


def main(source_run):
    path = ROOT / 'runs' / source_run / 'episodes.csv'
    raw = path.read_bytes()
    rows = [r for r in csv.DictReader(io.StringIO(raw.decode()))
            if r['model']=='Qwen3-32B' and r['arm']=='plain' and r['condition']=='recruiting']
    run = start_run('e05-behaviour-exclusions-audit', experiment='E05', parents=[source_run],
        settings={'source_sha256':hashlib.sha256(raw).hexdigest(), 'operation':'frozen table audit; no fitting'})
    try:
        categories = {'incomplete':'Incomplete', 'never_read':'Complete, never read',
                      'invalid_complete':'Complete, exposed, task not completed'}
        excluded = [r for r in rows if r['valid']=='False']
        assert len(rows)==304 and len(excluded)==78
        assert set(r['category'] for r in excluded)==set(categories)
        assert all(r['task_success']=='False' for r in excluded if r['category']=='invalid_complete')
        result=[]
        for scenario in ['ALL',*sorted({r['scenario'] for r in rows})]:
            for category, name in categories.items():
                group=[r for r in excluded if r['category']==category and (scenario=='ALL' or r['scenario']==scenario)]
                result.append(dict(scenario=scenario,category=category,description=name,episodes=len(group),
                    any_boundary_leaks=sum(r['any_boundary']=='True' for r in group),
                    channel_leaks=sum(r['channel']=='True' for r in group),
                    task_not_completed=sum(r['task_success']=='False' for r in group)))
        write_json_atomic(run.dir/'counts.json',result)
        write_json_atomic(run.dir/'excluded-episodes.json', [{k:r[k] for k in
            ['path','source_sha256','scenario','category','status','read','task_success','any_boundary','channel']} for r in excluded])
        lines=['# Qwen recruiting exclusions in the behaviour table','',
            f'Source: `{source_run}/episodes.csv`, the frozen episode table used for paper Table 1. '
            'Selection is Qwen3-32B, plain arm, recruiting only: 304 attempts, 226 analysed, 78 excluded. '
            'Categories are mutually exclusive in this order: incomplete, complete but never read, then complete and exposed but invalid. '
            'The last category failed the task-summary requirement. These counts are episode-level; they differ from the activation-cache step audit.','',
            '| Scenario | Exclusion | Episodes | Any-boundary leaks | Channel leaks |',
            '|---|---|---:|---:|---:|']
        lines += [f"| {r['scenario']} | {r['description']} | {r['episodes']} | {r['any_boundary_leaks']} | {r['channel_leaks']} |" for r in result]
        lines += ['', 'Leaks are observed exact-value disclosures recorded in the frozen behaviour table. '
            'Incomplete episodes remain incomplete, not held; zero observed leaks does not establish how they would have ended. '
            'All three leaks in excluded episodes were channel disclosures. No outcomes were refit, no frozen source was changed, and no paid calls were made. '
            'Any change to the Qwen denominator requires a separately approved analysis.']
        (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
        totals=[r for r in result if r['scenario']=='ALL']
        run.result(attempts=len(rows),excluded=len(excluded),breakdown=totals)
        run.finish()
        print(run.dir)
        print(totals)
    except BaseException as exc:
        run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source-run',default='20261025-1850-e03-behaviour-summary')
    main(p.parse_args().source_run)
