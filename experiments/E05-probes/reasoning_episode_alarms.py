"""Episode aggregation of the existing reply-calibrated reasoning MAX alarms."""
import json
from pathlib import Path
import numpy as np
from reasoning_stream_data import ROOT
from collusion.runs import write_json_atomic
out=ROOT/'runs/20261026-0526-e05-reasoning-stream';data=ROOT/'runs/20261026-0522-e05-reasoning-stream-data';rows=json.loads((data/'replies.json').read_text())
held=sorted({r['episode'] for r in rows if r['condition']=='recruiting' and r['stream_window']=='post_ask' and not r['ever_public']});family={r['episode']:r['family'] for r in rows};groups=sorted({family[e] for e in held});code={g:i for i,g in enumerate(groups)};weights=np.random.default_rng(20261025).multinomial(len(groups),np.ones(len(groups))/len(groups),size=1000)
results={}
for mask in ['all','censored']:
 for mode in ['pooled','loso']:
  perseed=[];boot=[];counts=[]
  for seed in [42,43,44]:
   alarms={e:False for e in held};seen=set()
   for file in (out/f'immediate/{mask}/{mode}').glob(f's{seed}-f*/fit.json'):
    fit=json.loads(file.read_text());z=np.load(file.parent/'scores.npz')
    for i,score in zip(z['indices'],z['max_scores']):
     r=rows[int(i)]
     if r['stream_window']=='post_ask' and r['episode'] in alarms:
      seen.add(r['episode']);alarms[r['episode']]|=bool(score>fit['threshold'])
   assert seen==set(held)
   flags=np.array([alarms[e] for e in held]);ew=weights[:,[code[family[e]] for e in held]];boot.append((ew@flags)/ew.sum(axis=1));perseed.append(float(flags.mean()));counts.append(int(flags.sum()))
  results[f'immediate/{mask}/{mode}']={'held_episodes':len(held),'alarms_by_seed':counts,'rate_by_seed':perseed,'mean_rate':float(np.mean(perseed)),'family_ci95':np.quantile(np.mean(boot,axis=0),[.025,.975]).tolist(),'calibration':'unchanged5%trainingCONTROL REPLY MAX,strict>;notepisodecalibration'}
write_json_atomic(out/'held_episode_alarms.json',results)
lines=['# Held-episode alarms from the existing reasoning probe','','These are any alarms across eligible post-ask replies of a held recruiting episode, retaining the original per-fold5% CONTROL-REPLY threshold. No threshold is refit or recalibrated. The primary immediate MAX probe is used.','','| Cut | Split | Alarms by seed / held episodes | Mean rate [95% family CI] |','|---|---|---|---|']
for key,r in results.items():
 _,cut,mode=key.split('/');lo,hi=r['family_ci95'];lines.append(f"| {cut} | {mode} | {r['alarms_by_seed']} / {r['held_episodes']} | {r['mean_rate']:.1%} [{lo:.1%},{hi:.1%}] |")
(out/'held_episode_alarms.md').write_text('\n'.join(lines)+'\n');print(json.dumps(results,indent=2))
