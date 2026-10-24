"""TF-IDF baselines with the frozen activation-probe splits and paired evaluation."""
import hashlib
import json
import re
import sys
import warnings
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
from data import ROOT,REPLAY
from metrics import position_weights,within_round,threshold_at_fpr
from evaluate import ranking_summary,interval,alert_summary
from report import clean,f,ci,write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

FIT='20261024-1937-e05-probe-core'
CORE_REPORT='20261024-2007-e05-probe-core'
CS=[.1,1.,10.,100.]
TEXTS=['full_prompt','target_only','target_prose']


def digest(x):
    if not isinstance(x,bytes):x=json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()
    return hashlib.sha256(x).hexdigest()


def own_spans(prompt,messages):
    # Reject delimiter injection rather than silently attributing peer text to the target.
    for message in messages:
        assert '<|im_start|>' not in json.dumps(message) and '<|im_end|>' not in json.dumps(message)
    blocks=re.findall(r'<\|im_start\|>([^\n]+)\n(.*?)<\|im_end\|>',prompt,re.S)
    spans=[text for role,text in blocks if role=='assistant']
    assert len(spans)==sum(m['role']=='assistant' for m in messages)
    prose=[re.sub(r'<tool_call>.*?</tool_call>','',text,flags=re.S) for text in spans]
    prose=[re.sub(r'<think>\s*</think>','',text).strip() for text in prose]
    return '\n\n'.join(spans),'\n\n'.join(prose)


def load_text(rows,out):
    replay=ROOT/'runs'/REPLAY;index=[json.loads(s) for s in (replay/'index.jsonl').read_text().splitlines()]
    assert len(index)==len(rows)
    episodes={};texts={name:[] for name in TEXTS};audit=[]
    for i,(r,source) in enumerate(zip(rows,index)):
        assert r['request_sha256']==source['request_sha256']
        raw=(replay/source['prompt_file']).read_bytes();assert digest(raw)==source['prompt_sha256']
        path=ROOT/source['manifest']['episode_file']
        if path not in episodes:episodes[path]=json.loads(path.read_text())
        record=episodes[path]['requests'][r['request_idx']];assert record['actor']=='target'
        request=record['request'];assert digest(request)==r['request_sha256']
        full=raw.decode();own,prose=own_spans(full,request['messages'])
        for key,text in zip(TEXTS,[full,own,prose]):texts[key].append(text)
        audit.append(dict(row=i,episode=r['episode'],request_idx=r['request_idx'],request_sha256=r['request_sha256'],prompt_sha256=digest(raw),
                          target_only_sha256=digest(own.encode()),target_prose_sha256=digest(prose.encode()),target_only_chars=len(own),target_prose_chars=len(prose)))
    (out/'text-index.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in audit))
    return texts


def vectorizer():
    return TfidfVectorizer(lowercase=True,ngram_range=(1,1),min_df=1,sublinear_tf=True,norm='l2',dtype=np.float64)


def fit_model(x,y,weights,c):
    model=LogisticRegression(C=c,solver='lbfgs',max_iter=2000,tol=1e-5)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning);model.fit(x,y,sample_weight=weights)
    if any(issubclass(w.category,ConvergenceWarning) for w in caught):raise RuntimeError('Text logistic convergence failure')
    return model


def main():
    source=ROOT/'runs'/FIT;rows=[json.loads(s) for s in (source/'rows.jsonl').read_text().splitlines()]
    original=np.load(source/'main'/'predictions.npz');eligible=original['eligible'];y=original['y'];seeds=list(original['seeds'])
    notes=json.loads((source/'main'/'folds.json').read_text());rounds=np.array([r['round'] for r in rows]);ep=np.array([r['episode'] for r in rows])
    run=start_run('e05-text-baselines',experiment='E05',parents=[FIT,CORE_REPORT,REPLAY],settings={'C_candidates':CS,'tfidf':'word unigrams, lowercase, min_df1, sublinear TF, L2 norm','splits':'exact saved main outer and inner folds','bootstrap_reps':1000,'target_only':'complete prior rendered assistant spans including tool-call text','target_prose':'same spans with tool-call blocks and empty think tags removed'})
    try:
        texts=load_text(rows,run.dir);pred={name:np.full_like(original['nested'],np.nan) for name in TEXTS};thresholds={name:np.full_like(original['nested'],np.nan) for name in TEXTS};fit_notes=[]
        with threadpool_limits(limits=4):
            for note in notes:
                si=seeds.index(note['seed']);fold=note['fold']
                select=lambda key:eligible[np.isin(ep[eligible],note[key])]
                train=select('train_episodes');test=select('test_episodes');cal=select('calibration_episodes');inner=select('inner_train_episodes');val=select('inner_validation_episodes')
                assert not set(ep[train])&set(ep[test]);assert not set(ep[cal])&set(ep[test])
                assert np.array_equal(np.sort(test),np.sort(eligible[original['folds'][si,eligible]==fold]))
                iw=position_weights(y[inner],rounds[inner]);inner=inner[iw>0];iw=iw[iw>0]
                tw=position_weights(y[train],rounds[train]);train=train[tw>0];tw=tw[tw>0]
                for name in TEXTS:
                    text=texts[name];vec=vectorizer();x=vec.fit_transform([text[i] for i in inner]);vx=vec.transform([text[i] for i in val]);scores={}
                    for c in CS:scores[c]=within_round(y[val],fit_model(x,y[inner],iw,c).decision_function(vx),rounds[val])[0]
                    chosen=max(CS,key=lambda c:(scores[c] if np.isfinite(scores[c]) else -1,-c))
                    vec=vectorizer();x=vec.fit_transform([text[i] for i in train]);model=fit_model(x,y[train],tw,chosen)
                    values=model.decision_function(vec.transform([text[i] for i in test]));calvalues=model.decision_function(vec.transform([text[i] for i in cal]))
                    cutoff,info=threshold_at_fpr(calvalues,ep[cal]);pred[name][si,test]=values;thresholds[name][si,test]=cutoff
                    prefix=f'{name}-s{note["seed"]}-f{fold}'
                    np.savez_compressed(run.dir/(prefix+'.npz'),coef=model.coef_,intercept=model.intercept_,idf=vec.idf_)
                    write_json(run.dir/(prefix+'-vocabulary.json'),vec.vocabulary_)
                    fit_notes.append(dict(method=name,seed=note['seed'],fold=fold,C=chosen,inner_validation_auroc=scores,features=len(vec.vocabulary_),threshold=cutoff,**info))
                print('FIT',note['seed'],fold,flush=True)
            for name in TEXTS:assert np.isfinite(pred[name][:,eligible]).all()
            np.savez_compressed(run.dir/'predictions.npz',**pred,**{'threshold_'+k:v for k,v in thresholds.items()},eligible=eligible,y=y,seeds=seeds,folds=original['folds'])
            write_json(run.dir/'fits.json',fit_notes)
            head=eligible[[rows[i]['condition']=='recruiting' for i in eligible]];groups=np.array([rows[i]['family'] for i in head]);ys=np.tile(y[head],(3,1));results={};boots={}
            for name,values in {'probe':original['nested'],**pred}.items():
                result,boot,_=ranking_summary(ys,values[:,head],rounds[head],groups);boots[name]=boot
                t=original['threshold_nested'] if name=='probe' else thresholds[name]
                result['alerts'],_=alert_summary(rows,eligible,values[:,eligible],t[:,eligible],y[eligible])
                results[name]=result;print('RESULT',name,result['within_round_auc'],flush=True)
            differences={name:dict(mean=results['probe']['within_round_auc']-results[name]['within_round_auc'],family_ci95=interval(boots['probe']-boots[name])) for name in TEXTS}
            output=dict(methods=results,probe_minus_text=differences,headline_rows=len(head),headline_episodes=len(set(ep[head])),headline_families=len(set(groups)),prompt_hashes_verified=len(rows),empty_target_prose_rows=sum(not texts['target_prose'][i].strip() for i in head))
            write_json(run.dir/'metrics.json',output)
        lines=['# Text baselines on the frozen E05 steps','',f'Run `{run.id}`; probe/folds `{FIT}`. Same 1,810 exposed steps, 92 recruiting episodes, 47 families; five family-grouped outer folds and three fold dealings. No new model inference.','',
            '| Method | Within-round AUROC (95% family CI) | Pooled AUROC | Episode recall | Held recruiting FPR | Held-out control FPR |','|---|---:|---:|---:|---:|---:|']
        for name,r in results.items():
            a=r['alerts'];lines.append(f"| {name} | {f(r['within_round_auc'])} {ci(r['within_round_ci95'])} | {f(r['pooled_auc'])} | {f(a['raw_alert_episode_recall'])} | {f(a['raw_alert_held_recruiting_fpr'])} | {f(a['raw_alert_heldout_control_fpr'])} |")
        lines+=['','| Comparison | Within-round AUROC difference | Paired 95% family CI |','|---|---:|---:|']
        for name,r in differences.items():lines.append(f"| Probe minus {name} | {f(r['mean'])} | {ci(r['family_ci95'])} |")
        lines+=['','Full-prompt features use the exact saved rendered prompt, including system rules, tool schema, peer text, prior target messages and tool results. Every prompt and source request hash was checked. Target-only features use prior complete assistant spans from that same rendering, including the target’s function names/arguments, but no peer messages or tool results. The pending reply is never included. Target-prose removes tool-call blocks and empty thinking tags. Empty histories remain empty feature rows.',
            '',f"There are {output['empty_target_prose_rows']} empty prose-only rows among headline steps. Empty rows are retained, not imputed with a label-dependent placeholder.",'',
            'TF-IDF uses lowercase word unigrams, sublinear term frequency, L2 document normalization and no stop-word removal. Vocabulary and IDF are fitted only on the relevant training split. Logistic regression uses L2, with C selected from 0.1/1/10/100 using the exact saved inner validation episodes and within-round metric; ties prefer the smaller C. Outer fits use the same round-matched negative weights as the activation probe. The saved outer-test folds and control/alone calibration episodes are unchanged.','',
            'The paired intervals reuse identical family-bootstrap draws across methods, average over the three fold dealings, and condition on frozen fitted scores. They do not include refitting/model-selection uncertainty. Thresholds use control/alone episode maxima with the same ≤5% calibration rule as E05; held-out FPR need not equal5%. No outer-test score selects vocabulary, C or a feature variant.','',
            'These comparisons assess incremental predictive value over these text baselines, not causal evidence or hidden intent. The original logged/reporting/mock-tool cues, provisional labels and strict-transfer limitation still apply. No optional sentence-embedding baseline was required; no weights were downloaded.','',
            'Artifacts: predictions.npz, metrics.json, fits.json, text-index.jsonl, and fold-specific vocabulary/IDF/coefficients.']
        (run.dir/'report.md').write_text('\n'.join(lines)+'\n')
        run.result(**{name:r['within_round_auc'] for name,r in results.items()});run.finish();print('TEXT_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
