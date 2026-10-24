"""Add an evidence summary and audit caveat without recomputing frozen results."""
import hashlib
import json
import shutil
import sys
from data import ROOT
from report import write_json
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run
SOURCE='20261025-0531-e05-replay2-analysis';AUDIT='20261025-0533-e05-replay2-baseline-audit'


def main():
    source=ROOT/'runs'/SOURCE;metrics=json.loads((source/'metrics.json').read_text())
    run=start_run('e05-replay2-analysis',experiment='E05',parents=[SOURCE,AUDIT],settings={'stage':'final narrative and artifact package','no_refits_or_metric_changes':True,'plots_copied_without_changes':True})
    try:
        hashes={}
        for path in source.iterdir():
            if path.name in ('meta.json','log.txt','diff.patch','report.md'):continue
            if path.is_file():
                target=run.dir/path.name;shutil.copy2(path,target);digest=hashlib.sha256(path.read_bytes()).hexdigest();assert hashlib.sha256(target.read_bytes()).hexdigest()==digest;hashes[path.name]=digest
        write_json(run.dir/'source_artifacts.json',hashes)
        text=(source/'report.md').read_text()
        lead='''# Replay2 probe analysis

The extraction checks passed, but the primary results do not establish robust generalization or clear added value. Inner-selected logistic scenario × round AUROC is **0.632 [0.474, 0.757]** on v2, **0.522 [0.450, 0.591]** in pooled family CV, and **0.551 [0.499, 0.597]** in LOSO. MLP estimates are 0.635 [0.474, 0.758] on v2 and 0.519 [0.460, 0.568] in LOSO; the paired MLP-minus-logistic intervals include zero. The pooled added-value gain is +0.009 [-0.004, 0.022], and the clean branching correlation is −0.032 [-0.460, 0.401].

At a 5% training-benign episode false-alarm target, the pooled logistic probe detects **3.2%** of positive episodes, with **5.6%** held-out benign FPR (8.2% on control episodes alone). Lead times below are conditional on the few detections. Deliberate-only sensitivity gives higher logistic estimates—v2 0.661 [0.512, 0.769], pooled 0.588 [0.502, 0.657]—but does not replace the primary mixed-outcome analyses.

**CV baseline limitation:** several training-fold baselines, and the v2 shuffled-label check, rank below chance under the predeclared metric. A post-hoc audit exactly reconstructed the scenario-rate scores and found both scenario baselines equal 0.5 when comparisons are additionally confined to the same fitted fold. Cross-fold calibration shifts therefore matter: a training prevalence comes from the complement of a held-out fold and can rank a more-positive held-out fold lower. LOSO has one model per held-out scenario and its stratified scenario baselines are exactly 0.5. No primary metric was changed, and no probe was refit or rescored with the added fold stratum. See the [baseline audit](../20261025-0533-e05-replay2-baseline-audit/report.md). Gaps against these below-chance CV baselines should not be treated as robust added value on their own.
'''
        text=text.replace('# Replay2 probe analysis',lead,1)
        alarm=['## Episode alarms','','### Raw alarms at the 5% training-benign target','','| Analysis | Probe | Recall [family 95% CI] | Held-out benign FPR [family 95% CI] | Control-only FPR | Median lead steps |','|---|---|---|---|---|---|']
        def pct(item):return f"{item['mean']:.1%} [{item['ci95'][0]:.1%}, {item['ci95'][1]:.1%}]"
        for mode in ('v2','pooled','loso'):
            for method in ('nested','mlp'):
                if method not in metrics[mode]['alarms']:continue
                a=metrics[mode]['alarms'][method]['raw_0.05'];alarm.append(f"| {mode} | {'Inner-selected logistic' if method=='nested' else 'MLP'} | {pct(a['recall'])} | {pct(a['control_fpr'])} | {a['control_only_fpr']['mean']:.1%} | {a['lead_steps_conditional_on_detection']['median']} |")
        alarm+=['','Zero observed alone FPR is based on 25 pooled eligible alone episodes (6 in v2). A zero-event empirical bootstrap interval is not a population-risk upper bound. Counts by seed and all alarm intervals remain in `metrics.json`.','','### Inner-selected logistic trade-off','']
        text=text.replace('## Episode alarms','\n'.join(alarm),1)
        (run.dir/'report.md').write_text(text)
        summary={'primary_metrics_unchanged':True,'validation_passed':True,'source_analysis':SOURCE,'baseline_audit':AUDIT,'headline':{mode:metrics[mode]['methods']['nested'] for mode in ('v2','pooled','loso')}}
        write_json(run.dir/'summary.json',summary);run.result(primary_metrics_unchanged=True,validation_passed=True);run.finish();print('FINAL_ANALYSIS',run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':main()
