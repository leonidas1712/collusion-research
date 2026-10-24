"""Export predeclared pooled splits for E06 without fitting or scoring models."""
import json
import sys
import numpy as np
from data import ROOT
from replay2_core import selected_indices,outer_cases,SEEDS
from replay2_data import eligible_step,PLAN
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run


def main():
    source=ROOT/'runs'/PLAN;labels={e['episode_file']:e['label'] for e in json.loads((source/'episodes.json').read_text())};rows=[]
    run=start_run('e05-replay2-folds',experiment='E05',parents=[PLAN],settings={'no_model_fits':True,'variant':'pooled','seeds':SEEDS,'split_unit':'family','recipe':'replay2_core.outer_cases'})
    try:
        for i,line in enumerate((source/'all.jsonl').read_text().splitlines()):
            m=json.loads(line);label=labels.get(m['episode_file'],{})
            rows.append(dict(index=i,episode=m['episode_key'],request_idx=m['request_idx'],request_sha256=m['request_sha256'],prompt_sha256=m['prompt_sha256'],family=m['family_id'],scenario=m['scenario'],condition=m['condition'],round=m['round'],n_tokens=m['n_tokens'],eligible=eligible_step(m),label=int(bool(label.get('objective_success'))),kind=(label.get('semantic_judge') or {}).get('labels',{}).get('first_publication_kind')))
        eligible=selected_indices(rows,'pooled');notes=[]
        for seed in SEEDS:
            for fold,other,test,note in outer_cases(rows,eligible,seed):
                train=other[[rows[i]['condition']=='recruiting' for i in other]];cal=other[[rows[i]['condition'] in ('control','alone') for i in other]]
                record=dict(seed=seed,fold=fold,**note)
                for name,indices in [('train',train),('calibration',cal),('test',test)]:
                    record[name+'_indices']=indices.tolist();record[name+'_episodes']=sorted({rows[i]['episode'] for i in indices});record[name+'_families']=sorted({rows[i]['family'] for i in indices})
                assert not set(record['test_families'])&(set(record['train_families'])|set(record['calibration_families']))
                notes.append(record)
        write_json(run.dir/'folds.json',notes);(run.dir/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows));np.save(run.dir/'eligible.npy',eligible)
        run.result(eligible_rows=len(eligible),folds=len(notes),no_fits=True);run.finish();print('FOLDS_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
