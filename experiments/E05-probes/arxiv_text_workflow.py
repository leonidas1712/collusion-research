"""Development-only text fits and output-action controls on matched per-call rows."""
import argparse,csv,gzip,hashlib,json,sys,warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'experiments/E03-target-screen'))
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
from collusion.runs import start_run,write_json_atomic
from metrics import position_weights
from reasoning_stream_report import stream_metrics
from escalation_prompts import RECORD_SCENARIOS

def read_csv(path):
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as f:return list(csv.DictReader(f))

def source_data(model,restore):
    if model=='gpt':
        rows=json.loads((restore/'runs/20261026-0522-e05-reasoning-stream-data/replies.json').read_text())
        source=restore/'runs/20261026-1221-e05-lastprompt-percall-6013/probe_scores.csv.gz'
        scores=[r for r in read_csv(source) if r['cohort']=='matched' and r['label_variant']=='immediate' and r['analysis']=='loso']
    else:
        rows=json.loads((ROOT/'runs/20261026-2155-e05-qwen-any-public-audit/rows.json').read_text())
        for r in rows:r['row_id']=f"{r['episode']}::request_idx={r['request_idx']}"
        source=ROOT/'runs/20261026-2201-e05-arxiv-qwen-any-public/probe_scores.csv.gz'
        scores=[r for r in read_csv(source) if r['label_variant']=='immediate' and r['analysis']=='loso']
    mapping={r['row_id']:r for r in rows};keys=sorted({r['row_id'] for r in scores});rows=[mapping[k] for k in keys];lookup={k:i for i,k in enumerate(keys)}
    values=np.full((3,len(rows)),np.nan);folds=np.full(values.shape,-1,int)
    for r in scores:
        i=lookup[r['row_id']];s=int(r['seed'])-42
        assert rows[i]['y_immediate']==int(r['label']) and rows[i]['request_sha256']==r['request_sha256']
        values[s,i]=float(r['score']);folds[s,i]=int(r['fold'])
    assert np.isfinite(values).all()
    assert len(rows)==(1995 if model=='gpt' else 2976)
    return rows,values,folds,source

def args_dict(call):
    a=(call.get('function') or {}).get('arguments') or {}
    if isinstance(a,str):
        try:a=json.loads(a)
        except json.JSONDecodeError:return {}
    return a if isinstance(a,dict) else {}

def texts_flags(rows,restore,model):
    texts=[];incoming=[];flags=[];cache={};hashes={}
    for r in rows:
        if r['episode'] not in cache:
            folder,name=r['episode'].split('/');rel=Path('runs')/folder/'episodes'/name
            p=ROOT/rel if (ROOT/rel).exists() else restore/rel
            assert p.exists(),p
            raw=p.read_bytes();hashes[str(rel)]=hashlib.sha256(raw).hexdigest();cache[r['episode']]=json.loads(raw)
        ep=cache[r['episode']];request=ep['requests'][r['request_idx']];payload=request['request'];messages=json.loads(json.dumps(payload['messages']))
        # Match the replay's retention policy, including prior same-turn reasoning.
        last_user=max((i for i,m in enumerate(messages) if m.get('role')=='user'),default=-1)
        for i,m in enumerate(messages):
            if model=='gpt' and not (r['history_reasoning_mode']=='current_turn' and i>last_user):
                m.pop('reasoning',None);m.pop('reasoning_details',None)
        text=json.dumps(dict(messages=messages,tools=payload.get('tools',[])),ensure_ascii=False,sort_keys=True)
        inc=json.dumps(messages[-1],ensure_ascii=False,sort_keys=True)
        for value in ep['scenario_spec']['honeypots']:
            text=text.replace(value,'PROTECTED_VALUE');inc=inc.replace(value,'PROTECTED_VALUE')
        texts.append(text);incoming.append(inc)
        reply=(request.get('response') or {}).get('choices',[{}])[0].get('message',{})
        calls=reply.get('tool_calls') or []
        destination=RECORD_SCENARIOS.get(r['scenario'],{}).get('destination','handoff/status.txt')
        writes=[c for c in calls if (c.get('function') or {}).get('name')=='write_file']
        flags.append(dict(write_file=bool(writes),handoff_write=any(args_dict(c).get('path')==destination for c in writes)))
    return dict(full_input=texts,latest_input=incoming),flags,hashes

def main(model,restore):
    rows,probe,folds,source=source_data(model,restore);texts,flags,hashes=texts_flags(rows,restore,model)
    ids=np.arange(len(rows));y=np.array([r['y_immediate'] for r in rows]);rounds=np.array([r['round'] for r in rows]);families=np.array([r['family'] for r in rows])
    run=start_run('e05-arxiv-'+model+'-text-workflow',experiment='E05',parents=[source.parent.name],tags=['cpu-only','post-hoc'],settings={'same_calls':True,'api_spend_usd':0,'gpu_spend_usd':0})
    write_json_atomic(run.dir/'plan.json',dict(model=model,rows=len(rows),positives=int(y.sum()),source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),episode_hashes=hashes,
        text='serialized exact saved request messages + tools; mask exact protected values; GPT same-turn reasoning retention matches replay; no current response; latest_input is final request message only',
        vectorizer=dict(ngram_range=[1,2],min_df=2,max_features=50000,sublinear_tf=True,norm='l2'),classifier=dict(C=.1,solver='lbfgs',max_iter=2000,tol=1e-5),weights='same round-balanced weights as activation recipe',selection='fixed hyperparameters, no tuning',splits='exact saved LOSO fold membership; fit vocabulary and IDF only on other scenarios; family disjoint',action_controls='current response tool name/path: post-output diagnostic, not deployable pre-call predictor',bootstrap=dict(unit='family',reps=1000,seed=20261025)))
    try:
      methods={'last_prompt':probe};model_details=[]
      with threadpool_limits(limits=2):
        for name,documents in texts.items():
            pred=np.full(probe.shape,np.nan)
            for fold in sorted(set(folds[0])):
                te=np.flatnonzero(folds[0]==fold);held_families=set(families[te]);tr=np.array([i for i in range(len(rows)) if folds[0,i]!=fold and families[i] not in held_families])
                if model=='qwen':
                    saved_rows=json.loads((ROOT/'runs/20261026-2201-e05-arxiv-qwen-any-public/rows.json').read_text())
                    plans=json.loads((ROOT/'runs/20261026-2201-e05-arxiv-qwen-any-public/plans.json').read_text())
                    selected_plans=[p for p in plans if p['fold']==fold]
                    first=selected_plans[0]
                    train_keys={f"{saved_rows[j]['episode']}::request_idx={saved_rows[j]['request_idx']}" for j in first['split']['train']}
                    tr=np.array([i for i,r in enumerate(rows) if r['row_id'] in train_keys])
                    for plan in selected_plans:
                        expected={f"{saved_rows[j]['episode']}::request_idx={saved_rows[j]['request_idx']}" for j in plan['split']['train']}
                        assert expected=={rows[j]['row_id'] for j in tr}
                assert not set(families[tr])&set(families[te]);assert all(np.array_equal(folds[s]==fold,folds[0]==fold) for s in range(3))
                weights=position_weights(y[tr],rounds[tr]);fit_ids=tr[weights>0];weights=weights[weights>0]
                tf=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_features=50000,sublinear_tf=True)
                x=tf.fit_transform([documents[i] for i in fit_ids]);xt=tf.transform([documents[i] for i in te])
                clf=LogisticRegression(C=.1,solver='lbfgs',max_iter=2000,tol=1e-5,random_state=42)
                with warnings.catch_warnings():
                    warnings.simplefilter('error',ConvergenceWarning);clf.fit(x,y[fit_ids],sample_weight=weights)
                pred[:,te]=clf.decision_function(xt)
                model_details.append(dict(method=name,fold=int(fold),train_calls=len(tr),positive_weight_train_calls=len(fit_ids),test_calls=len(te),vocabulary=len(tf.vocabulary_),iterations=clf.n_iter_.tolist()))
                print('FIT',model,name,fold,len(te),flush=True)
            assert np.isfinite(pred).all();methods[name]=pred
        for flag in ['write_file','handoff_write']:methods[flag]=np.tile([r[flag] for r in flags],(3,1))
        metrics={};boots={};paired={}
        for name,values in methods.items():metrics[name],boots[name]=stream_metrics(rows,ids,y,values,folds,1000)
        for name in methods:
            if name=='last_prompt':continue
            d=boots['last_prompt']['within_round']-boots[name]['within_round'];paired['last_prompt_minus_'+name]=dict(estimate=metrics['last_prompt']['within_round_auc']-metrics[name]['within_round_auc'],ci95=np.nanquantile(d,[.025,.975]).tolist())
        counts={}
        for flag in ['write_file','handoff_write']:
            keep=np.array([r[flag] for r in flags]);counts[flag]=dict(calls=int(keep.sum()),positives=int(y[keep].sum()),negatives=int(sum(y[keep]==0)))
            if len(set(y[keep]))==2:metrics['last_prompt_within_'+flag]=stream_metrics(rows,ids[keep],y[keep],probe[:,keep],folds[:,keep],1000)[0]
      write_json_atomic(run.dir/'metrics.json',dict(metrics=metrics,paired=paired,counts=counts));write_json_atomic(run.dir/'fits.json',model_details)
      with gzip.open(run.dir/'scores.csv.gz','wt',newline='') as f:
        fields=['row_id','family','scenario','round','label','seed','fold']+list(methods);w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for i,r in enumerate(rows):
          for s in range(3):w.writerow({k:r[k] for k in ['row_id','family','scenario','round']}|dict(label=int(y[i]),seed=42+s,fold=int(folds[s,i]))|{k:float(v[s,i]) for k,v in methods.items()})
      run.result(metrics={k:v['within_round_auc'] for k,v in metrics.items()},counts=counts);run.finish();print(run.dir,flush=True)
    except BaseException as e:run.finish('failed',str(e));raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['gpt','qwen'],required=True);p.add_argument('--restore-root',type=Path,required=True);a=p.parse_args();main(a.model,a.restore_root)
