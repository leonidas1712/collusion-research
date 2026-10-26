"""Use the existing collection postprocessor at the fixed confirmation quotas."""
import argparse,json,subprocess
from pathlib import Path
import finalize_gpt_oss_collection as f
from collusion.runs import start_run,write_json_atomic

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--freeze',type=Path,required=True);a=p.parse_args();parent=a.freeze
 benchmark=json.loads((parent/'benchmark-retry_collection.json').read_text());bulk=json.loads((parent/'bulk_run.json').read_text());assert bulk['status']=='finished'
 # The first bulk launcher omitted these descriptive counts from child meta;
 # reconstruct them from the pre-launch fixed allocation, never the outcomes.
 for child in bulk['children']:
  path=Path(child)/'meta.json';meta=json.loads(path.read_text());settings=meta['settings']
  counts={'recruiting':12 if settings['scenario']=='service-rollout-threshold' else 11,'control':2}
  for key,value in counts.items():
   assert key not in settings or settings[key]==value
   settings[key]=value
  settings['planned_counts_source']='frozen throughput_amendment.json; five benchmark recruiting episodes included in84'
  write_json_atomic(path,meta)
 paths=[Path(r['run_dir']) for r in benchmark]+[Path(p) for p in bulk['children']]
 if (parent/'topup_run.json').exists():
  topup=json.loads((parent/'topup_run.json').read_text());assert topup['status']=='finished' and topup['incomplete']==0
  paths += [Path(p) for p in topup['children']]
 # Failed zero-inference setup attempts remain in the audit, never in the scored cohort.
 failed=json.loads((parent/'benchmark_collection.json').read_text());paths=[Path(r['run_dir']) for r in failed]+paths
 f.QUOTAS={'recruiting':12,'control':2}
 run=start_run('e03-stream-confirm-manifest',experiment='E03',parents=[parent.name,Path(bulk['run_dir']).name],tags=['confirmation','cpu-only'],settings={'quotas':f.QUOTAS,'fixed_total_complete_target':84,'no_quality_based_topup':True})
 try:
  manifest=f.freeze_manifest(paths,run.dir,subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
  assert len({r['scenario'] for r in manifest['episodes']})==6
  assert len({(r['scenario'],r['condition'],r['family_id']) for r in manifest['episodes']})==manifest['selected_episode_count']
  write_json_atomic(parent/'confirmation_manifest.json',{'path':str(run.dir/'manifest.json'),'selected':manifest['selected_episode_count'],'deficits':manifest['deficits']})
  run.result(selected=manifest['selected_episode_count'],deficits=manifest['deficits']);run.finish();print('CONFIRM_MANIFEST',run.dir/'manifest.json',flush=True)
 except BaseException as e:run.finish('failed',str(e));raise
