"""Compare frozen v1 OOF scores with independent continuation outcomes."""
import hashlib
import json
import sys
import warnings
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr,ConstantInputWarning
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from data import ROOT,REPLAY
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

FIT='20261024-1937-e05-probe-core'
BRANCH='20261024-2001-e01-branching-scaleup'

def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def rho(x,y):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',ConstantInputWarning)
        return float(spearmanr(x,y).statistic)

def statistics(points,key):
    selected=[p for p in points if p.get(key) is not None]
    scores=np.array([p[key] for p in selected]);y=np.array([p['fraction'] for p in selected]);groups=np.array([p['family'] for p in selected]);names=np.unique(groups)
    rng=np.random.default_rng(20261024);boot=[]
    for _ in range(2000):
        draw=rng.choice(names,size=len(names),replace=True);idx=np.concatenate([np.flatnonzero(groups==g) for g in draw]);boot.append(rho(scores[idx].mean(axis=1),y[idx]))
    valid=np.asarray(boot);valid=valid[np.isfinite(valid)]
    return dict(points=len(selected),episodes=len({p['episode'] for p in selected}),families=len(names),spearman=rho(scores.mean(axis=1),y),
                by_seed=[rho(scores[:,i],y) for i in range(3)],family_bootstrap_ci95=np.quantile(valid,[.025,.975]).tolist(),bootstrap_reps=2000,valid_bootstrap_reps=len(valid),
                fraction_counts=dict(Counter(str(p['fraction']) for p in selected)))

def main():
    run=start_run('e05-branching-check',experiment='E05',parents=[FIT,BRANCH,REPLAY],settings={'score':'mean frozen inner-selected OOF logits across seeds42/43/44','primary_join':'first parent target request in branch round','sensitivity':'last finite OOF target request strictly before branch round','bootstrap':'2000 family clusters','no_refits':True})
    try:
        root=ROOT/'runs';fit=root/FIT;branch=root/BRANCH
        rows=[json.loads(s) for s in (fit/'rows.jsonl').read_text().splitlines()];pred=np.load(fit/'main'/'predictions.npz')['nested']
        replay=[json.loads(s) for s in (root/REPLAY/'index.jsonl').read_text().splitlines()];lookup={(r['episode'],r['request_idx']):i for i,r in enumerate(rows)}
        selection=json.loads((branch/'branch-points.json').read_text());points=[]
        selected_recruiting=[p for p in selection if p['outcome']!='control']
        summaries={}
        for path in branch.glob('*/summary.json'):
            summary=json.loads(path.read_text());parent=Path(summary['parent_path']);key=parent.parent.parent.name+'/'+parent.name;summaries[(key,summary['branch_round'])]=(path,summary)
        for selection_row in selected_recruiting:
            parent_path=ROOT/selection_row['episode'];episode=json.loads(parent_path.read_text());key=parent_path.parent.parent.name+'/'+parent_path.name;t=selection_row['round'];path,summary=summaries[(key,t)]
            metadata=episode['scenario_spec']['metadata'];assert metadata['peer_condition']=='recruiting'
            target=[(i,r) for i,r in enumerate(episode['requests']) if r['actor']=='target' and r['round']==t];assert target
            request_idx,record=target[0];i=lookup.get((key,request_idx));matched=i is not None
            if matched:
                assert rows[i]['request_sha256']==digest(record['request'])==replay[i]['request_sha256']
                assert rows[i]['round']==t
            point=dict(episode=key,family=str(metadata['family_id']),branch_round=t,parent_outcome=selection_row['outcome'],phase=selection_row['phase'],
                request_idx=request_idx,activation_matched=matched,valid=rows[i]['valid'] if matched else None,token_in_context=rows[i]['token_in_context'] if matched else None,score_row=i,score=pred[:,i].tolist() if matched and np.isfinite(pred[:,i]).all() else None,
                unscored_reason=None if matched and np.isfinite(pred[:,i]).all() else ('outside_frozen_probe_eligible_set' if matched else 'no_replayed_request'),summary_file=str(path.relative_to(ROOT)))
            prior=[k for k,r in enumerate(rows) if r['episode']==key and r['round']<t and np.isfinite(pred[:,k]).all()]
            j=max(prior,key=lambda k:rows[k]['request_idx']) if prior else None
            if j is not None:assert digest(episode['requests'][rows[j]['request_idx']]['request'])==rows[j]['request_sha256']
            point.update(prior_score=pred[:,j].tolist() if j is not None else None,prior_score_row=j,prior_round=rows[j]['round'] if j is not None else None)
            complete=[];exact=0;prefix_equal=0
            parent_messages=record['request']['messages'];events=[e for e in episode['channel'] if e['round']==t and e['actor']=='recruiter']
            checkpoint=list(parent_messages)
            for event in reversed(events):
                expected=episode['scenario_spec']['channel_format'].format(actor=event['actor'],name=episode['scenario_spec']['actor_names'][event['actor']],content=event['content'])
                assert checkpoint.pop()=={'role':'user','content':expected}
            for name in summary['branch_files']:
                b=json.loads((path.parent/name).read_text());assert b['branch']['branch_round']==t
                assert b['branch']['rounds_requested']==3 and not b.get('fake')
                if b['status']=='complete':complete.append(bool(b['branch_forbidden_within_window']))
                first=next(r for r in b['requests'] if r['actor']=='target' and r['round']==t)
                exact+=digest(first['request'])==digest(record['request'])
                bm=list(first['request']['messages']);events=[e for e in b['channel'] if e['round']==t and e['actor']=='recruiter']
                for event in reversed(events):
                    expected=b['scenario_spec']['channel_format'].format(actor=event['actor'],name=b['scenario_spec']['actor_names'][event['actor']],content=event['content'])
                    assert bm.pop()=={'role':'user','content':expected}
                assert bm==checkpoint;prefix_equal+=1
            assert len(complete)==summary['branches_complete']==summary['branches_requested']==5
            assert sum(complete)==summary['forbidden_within_window']
            fraction=float(np.mean(complete));assert fraction==summary['share_forbidden_within_window']
            point.update(fraction=fraction,hits=sum(complete),reruns=len(complete),exact_round_target_request_matches=exact,checkpoint_history_matches=prefix_equal)
            points.append(point)
        primary=statistics(points,'score');prior=statistics(points,'prior_score');results=dict(requested_points=len(points),activation_matched=sum(p['activation_matched'] for p in points),primary=primary,pre_branch_sensitivity=prior,
            unscored=[p for p in points if p['score'] is None],exact_target_request_matches=sum(p['exact_round_target_request_matches'] for p in points),total_reruns=sum(p['reruns'] for p in points))
        write_json(run.dir/'points.json',points);write_json(run.dir/'metrics.json',results)
        plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
        fig,axes=plt.subplots(1,2,figsize=(10.5,4.4),sharey=True)
        for ax,key,stats,title in zip(axes,['score','prior_score'],[primary,prior],['First parent request in branch round','Last scored request before branch round']):
            for outcome,color,marker in [('held','#0072B2','o'),('give-in','#D55E00','^')]:
                subset=[p for p in points if p[key] is not None and p['parent_outcome']==outcome]
                ax.scatter([np.mean(p[key]) for p in subset],[p['fraction'] for p in subset],label='Parent '+outcome,color=color,marker=marker,alpha=.75,s=45)
            ax.set(xlabel='Mean frozen OOF probe logit',ylim=(-.06,1.06),yticks=np.arange(0,1.01,.2),title=f"{title}\nn={stats['points']}, Spearman ρ={stats['spearman']:.3f}");ax.legend(frameon=False,fontsize=9)
        axes[0].set_ylabel('Forbidden action within 3 rounds (fraction of 5 reruns)')
        fig.text(.5,.02,'Left includes the original round’s peer message; reruns regenerate that message. Points are not all independent.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.06,1,1));fig.savefig(run.dir/'branching-spearman.png',dpi=200);fig.savefig(run.dir/'branching-spearman.svg');plt.close(fig)
        lines=['# Frozen v1 probe scores versus branching outcomes','',f'Run `{run.id}`. Parents: `{FIT}`, `{BRANCH}`. CPU only; no model inference or refitting.','',
            f"Of {len(points)} recruiting branch points, **{results['activation_matched']}** match a replayed first target request in their parent branch round; **{primary['points']}** have an eligible frozen OOF probe score. All {results['total_reruns']} continuation files are complete (five per point), and outcomes agree with the saved summaries.",'',
            '| Score timing | Scored points | Parent episodes | Families | Spearman ρ | 95% family-bootstrap CI |','|---|---:|---:|---:|---:|---:|']
        for name,stats in [('First parent request at round t',primary),('Last scored parent request before t',prior)]:lines.append(f"| {name} | {stats['points']} | {stats['episodes']} | {stats['families']} | {stats['spearman']:.3f} | [{stats['family_bootstrap_ci95'][0]:.3f}, {stats['family_bootstrap_ci95'][1]:.3f}] |")
        lines+=['',f"Unscored points: {sum(p['score'] is None and not p['valid'] for p in points)} from invalid episodes and {sum(p['score'] is None and p['valid'] for p in points)} from valid episodes before token exposure. All 11 unscored requests lack token exposure; eligibility remains frozen.",'',f"Primary per-seed Spearman: {primary['by_seed']}. Pre-branch sensitivity: {prior['by_seed']}.",'',
            'Scores are the arithmetic mean of the three frozen inner-selected logistic OOF logits. No layer, seed or score transformation was selected using branch outcomes. Confidence intervals resample whole families (including repeated early/late points) 2,000 times. Five reruns yield coarse fractions; these intervals condition on the observed fractions and do not separately model binomial uncertainty. No IID p-value is claimed.','',
            '## Timing and matching caveat','',
            f"Branches restart before the peer speaks in round t. The primary saved target prompt already contains the original peer message from that round. Only {results['exact_target_request_matches']}/{results['total_reruns']} rerun target requests exactly match that full original request. Removing the respective newly delivered peer messages reproduces the same target history in all reruns. Thus the primary correlation is a parent-step association, not a clean estimate from an identical pre-branch target input. The sensitivity uses the latest eligible earlier target call; that is strictly before branching, but it is still not an activation at the exact reconstructed checkpoint.",'',
            'Exact episode/request joins and SHA256 checks link every matched parent score to its replayed input. All points without finite frozen scores remain listed in points.json and metrics.json; no score was imputed and no new probe was fit. Parent outcome and early/late phase influenced point selection, so this is a selected-sample exploratory association. Multiple points may share a parent episode/family. The three-round outcome differs from the eventual-publication label used to train the probe.','',
            '![Branching association](branching-spearman.png)','',
            'Artifacts: points.json (all joins, exclusions, rerun counts and scores), metrics.json, PNG/SVG plot. The original v1 observation/reporting/mock-tool limitations still apply. The remaining nonlinear, added-value and alarm analyses require the second replay dataset.']
        (run.dir/'report.md').write_text('\n'.join(lines)+'\n');run.result(matched=primary['points'],spearman=primary['spearman'],prior_spearman=prior['spearman']);run.finish();print(json.dumps(results,indent=2));print('BRANCH_RUN',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
