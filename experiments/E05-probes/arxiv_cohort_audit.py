"""Record scoring-cohort attrition, fresh scenario counts, and freeze chronology."""
import csv,json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic

def main():
    q=json.loads((ROOT/'runs/20261026-2155-e05-qwen-any-public-audit/rows.json').read_text())
    g=json.loads((ROOT/'runs/20261026-2218-e05-arxiv-gpt-percall-freeze/fresh_rows.json').read_text())
    counts={}
    for model,rows in [('Qwen',[r for r in q if r['index']>=6026 and r['condition']=='recruiting']),('GPT',g)]:
        for scenario in sorted({r['scenario'] for r in rows}):
            sub=[r for r in rows if r['scenario']==scenario];counts[model+'/'+scenario]=dict(calls=len(sub),episodes=len({r['episode'] for r in sub}),leaking_calls=sum(int(r['y_immediate']) for r in sub))
    replay=json.loads((ROOT/'runs/20261025-0923-e02-replay3-completion/summary.json').read_text())
    counts_plan=json.loads((ROOT/'paper-arxiv/dataset_plan_input.json').read_text())['datasets'];fresh=json.loads((ROOT/'runs/20261026-1302-e05-stream-confirm-score/counts.json').read_text())
    q_all=replay['combined_data']['real_episodes'];q_new=replay['new_data']['real_episodes']
    attrition={}
    q_dev_kept=sum(v['episodes'] for v in counts_plan['qwen_development']['counts'].values());q_fresh_kept=sum(v['episodes'] for v in counts_plan['qwen_fresh']['counts'].values())
    q_invalid=replay['combined_data']['excluded_episode_reasons']['invalid'];q_new_invalid=replay['new_data']['excluded_episode_reasons']['invalid']
    gdev=counts_plan['gpt_oss_development'];g_kept=gdev['scored_recruiting_episodes']+gdev['scored_control_episodes'];gf_kept=sum(fresh['selected_episodes_including_no_reasoning'].values());eligible=fresh['episode_flags_by_condition']['recruiting']['episode_eligible']
    for model,total,kept,reasons in [('qwen_development',q_all-q_new,q_dev_kept,dict(original_invalid=q_invalid-q_new_invalid,no_original_strict_window=replay['combined_data']['excluded_episode_reasons']['no_completed_step_in_strict_window'])),('qwen_fresh',q_new,q_fresh_kept,dict(original_invalid=q_new_invalid)),('gpt_oss_development',gdev['collection_episodes'],g_kept,dict(not_in_scored_post_ask_cohort=gdev['collection_episodes']-g_kept)),('gpt_oss_fresh',fresh['all_manifest_episodes'],gf_kept,dict(no_ever_correct_summary=fresh['manifest_by_condition']['recruiting']-eligible,no_selected_post_ask_call=eligible-fresh['selected_episodes_including_no_reasoning']['recruiting']))]:
        assert total-kept==sum(reasons.values());attrition[model]=dict(collection_or_replayed_episodes=total,scored_episodes_all_conditions=kept,excluded=total-kept,reasons=reasons)
    plans={
      'qwen_original':dict(initial_commit='99d82de',last_preanalysis_addendum='4232523',file='docs/confirmatory_plan.md',freeze='before near-term analysis, after collection and episode outcome counts',collection_start_sgt='2026-10-25 08:17',initial_commit_sgt='2026-10-25 08:55',analysis_start_sgt='2026-10-25 10:29'),
      'gpt_reasoning':dict(initial_commit='d470afd',file='runs/20261026-1139-e05-stream-confirm/frozen_plan.json',freeze='before fresh collection',initial_commit_sgt='2026-10-26 11:43',collection_start_sgt='2026-10-26 11:46'),
      'qwen_new_last_prompt':dict(initial_commit='f7a2995',file='paper-arxiv/frozen/qwen_percall_plan.json',freeze='before new predictions on previously inspected episodes'),
      'gpt_new_last_prompt':dict(initial_commit='2b05b71',file='paper-arxiv/frozen/gpt_percall_plan.json',freeze='before new predictions on previously inspected episodes')}
    for value in plans.values():
        value['full_commit']=subprocess.check_output(['git','rev-parse',value['initial_commit']],cwd=ROOT,text=True).strip()
        assert subprocess.check_output(['git','cat-file','-t',value['full_commit']+':'+value['file']],cwd=ROOT,text=True).strip()=='blob'
    run=start_run('e05-arxiv-cohort-audit',experiment='E05',tags=['cpu-only'],settings={'counts_only':True,'no_label_changes':True})
    write_json_atomic(run.dir/'counts.json',dict(fresh_scenarios=counts,attrition=attrition,freeze_provenance=plans,sources=['paper-arxiv/dataset_plan_input.json','runs/20261025-0923-e02-replay3-completion/summary.json','runs/20261026-1302-e05-stream-confirm-score/counts.json']))
    run.result(all_counts_reconciled=True);run.finish();print(run.dir,flush=True)
if __name__=='__main__':main()
