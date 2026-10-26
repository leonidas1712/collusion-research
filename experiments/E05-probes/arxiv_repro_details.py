"""Recount matched-call exclusions and extract detector/scenario configurations."""
import ast
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from collusion.runs import start_run, write_json_atomic


def main():
    old = Path('/Users/leo/collusion-research')
    sources = {}
    def load(rel):
        p = ROOT/rel if (ROOT/rel).exists() else old/rel
        sources[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        return p
    r = json.loads(load('runs/20261026-0522-e05-reasoning-stream-data/replies.json').read_text())
    dev = [dict(episode=x['episode'],tokens=x['reasoning_tokens'],positive=x['y_immediate'],ever=x['ever_public']) for x in r if x['stream_window']=='post_ask' and x['condition']=='recruiting']
    fresh = [dict(episode=x['episode'],tokens=int(x['reasoning_tokens']),positive=int(x['y_immediate']),ever=x['ever_public']=='True') for x in csv.DictReader(load('runs/20261026-1302-e05-stream-confirm-score/probe_scores.csv').open()) if x['condition']=='recruiting']
    cohorts = {}
    for name, rows in [('development',dev),('fresh',fresh)]:
        excluded = {x['episode'] for x in rows if x['positive'] and not x['tokens']}
        kept = [x for x in rows if x['tokens']]
        earlier = [x for x in kept if x['episode'] in excluded]
        assert not any(x['positive'] for x in earlier)
        assert all(x['ever'] for x in earlier)
        assert len({x['episode'] for x in earlier}) == len(excluded)
        cohorts[name] = dict(all_calls=len(rows),matched_calls=len(kept),episodes=len({x['episode'] for x in rows}),emitting_episodes=len({x['episode'] for x in rows if x['ever']}),matched_emitting_calls=sum(x['positive'] for x in kept),empty_reasoning_emission_calls=len(excluded),retained_earlier_calls_in_excluded_emission_episodes=len(earlier),retained_earlier_immediate_positive_calls=0,excluded_emission_episodes=sorted(excluded))
    qmeta = json.loads(load('runs/20261026-2155-e05-qwen-any-public-audit/rows.json').read_text())
    qr = [x for x in qmeta if x['index']>=6026 and x['condition']=='recruiting']
    qc = [x for x in qmeta if x['index']>=6026 and x['condition']=='control']
    qcounts = dict(recruiting_calls=len(qr),emitting_calls=sum(x['y_immediate'] for x in qr),earlier_nonemitting_calls_in_emitting_episodes=sum(x['y_eventual'] and not x['y_immediate'] for x in qr),refusing_episode_calls=sum(not x['y_eventual'] for x in qr),control_calls=len(qc),recruiting_plus_control_calls=len(qr)+len(qc))
    assert qcounts['recruiting_calls']==qcounts['emitting_calls']+qcounts['earlier_nonemitting_calls_in_emitting_episodes']+qcounts['refusing_episode_calls']
    gp = json.loads(load('runs/20261026-2242-e05-arxiv-gpt-text-workflow/plan.json').read_text())
    qp = json.loads(load('runs/20261026-2245-e05-arxiv-qwen-text-workflow/plan.json').read_text())
    assert gp['vectorizer']==qp['vectorizer'] and gp['classifier']==qp['classifier']
    tree = ast.parse(load('experiments/E05-probes/replay2_models.py').read_text())
    mlp = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MLP_SETTINGS' for t in n.targets))
    incoming = json.loads(load('runs/20261026-1128-e05-stream-layer18-loso/meta.json').read_text())['settings']
    incoming.pop('author_decision',None)
    for rel in ['experiments/E05-probes/arxiv_text_workflow.py','experiments/E05-probes/near_term_mlp.py','experiments/E05-probes/replay2_core.py','experiments/E05-probes/splits.py','experiments/E05-probes/stream_capture_fit.py','experiments/E05-probes/stream_model.py','experiments/E05-probes/stream_loss.py','experiments/E02-activation-replay/gpt_oss_stream_positions.py','experiments/E01-behaviour-pilot/leak_scenarios.py']:
        load(rel)
    scenarios = []
    ids = ['procurement-reserve-price','service-rollout-threshold','service-capacity-figure','handoff-exception-note','dispatch-integration-code']
    for x in csv.DictReader(load('experiments/E01-behaviour-pilot/SCENARIO_SPRAY.csv').open()):
        if x['id'] not in ids:continue
        full_rule = 'Operator policy: '+x['rule_text']+' '+x['consequence_text']
        sample = next((ROOT/'runs').glob('20261024-2338-e01-spray-'+x['id']+'-consequence-recruiting-32b-scaleup/episodes/*.json'))
        episode = json.loads(sample.read_text())
        assert full_rule in episode['scenario_spec']['target_system']
        sources[str(sample.relative_to(ROOT))]=hashlib.sha256(sample.read_bytes()).hexdigest()
        family = str(episode['family_id']) if 'family_id' in episode else str(episode['scenario_spec']['metadata']['family_id'])
        expected=x['secret_prefix']+hashlib.sha256((x['id']+':'+family).encode()).hexdigest()[:24]
        assert expected in episode['scenario_spec']['honeypots']
        scenarios.append(dict(id=x['id'],secret_key=x['secret_key'],secret_prefix=x['secret_prefix'],hex_characters=24,value_formula='prefix + sha256(scenario_id + ":" + family_id).hexdigest()[:24]',private_path=x['private_path'],summary_path=x['summary_path'],rule_text=full_rule,verified_episode=str(sample.relative_to(ROOT))))
    assert len(scenarios)==5
    run=start_run('e05-arxiv-repro-details',experiment='E05',settings=dict(saved_data_only=True,no_fit=True,no_model_calls=True,sources=sources))
    write_json_atomic(run.dir/'counts.json',dict(gptoss=cohorts,qwen_fresh=qcounts))
    write_json_atomic(run.dir/'settings.json',dict(tfidf=gp['vectorizer'],text_logistic=gp['classifier'],mlp=mlp,incoming=incoming))
    write_json_atomic(run.dir/'scenarios.json',scenarios)
    run.result(no_api=True,no_gpu=True);run.finish();print(run.dir);print(json.dumps(dict(gptoss=cohorts,qwen_fresh=qcounts),indent=2))


if __name__=='__main__':main()
