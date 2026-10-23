"""Check the unchanged E02 renderer against saved requests; never load model weights."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'experiments/E02-activation-replay'))
from collusion.runs import start_run,write_json_atomic
from replay import render,digest
from transformers import AutoTokenizer


def main(args):
 catalog=json.loads(Path(args.catalog).read_text())
 run=start_run('e03-template-check',experiment='E03',parents=[Path(args.catalog).parent.name],settings=vars(args),tags=['model-selection','template-only'])
 results=[]
 try:
  for item in catalog:
   mid=item['model'];hf=item['hf_model'];revision=item['hf'].get('sha')
   calls=[];sources=[]
   for meta in sorted((ROOT/'runs').glob('*/meta.json')):
    d=json.loads(meta.read_text())
    if d.get('started','')<args.since or d.get('settings',{}).get('target_model')!=mid:continue
    for path in sorted((meta.parent/'episodes').glob('*.json')):
     if '.attempt-' in path.name:continue
     ep=json.loads(path.read_text());sources.append(str(path.relative_to(ROOT)))
     for idx,r in enumerate(ep['requests']):
      if r['actor']=='target':calls.append((str(path.relative_to(ROOT)),idx,r['request']))
   result={'model':mid,'hf_model':hf,'revision':revision,'sources':sources,'calls':len(calls),'passed':0,'failures':[],'template_sha256':None}
   if not calls:
    result['status']='no screened requests';results.append(result);continue
   try:
    tok=AutoTokenizer.from_pretrained(hf,revision=revision,trust_remote_code=False)
    template=tok.get_chat_template(tools=calls[0][2].get('tools'))
    result['template_sha256']=digest(template.encode())
    (run.dir/(mid.replace('/','--')+'.jinja')).write_text(template)
    for path,idx,request in calls:
     try:
      text,ids,changes,thinking=render(tok,request,'from-request')
      result['passed']+=1
     except Exception as exc:
      result['failures'].append({'episode':path,'request_idx':idx,'error':str(exc)})
    result['status']='passed' if not result['failures'] else 'template incompatible'
   except Exception as exc:
    result['status']='tokenizer unavailable';result['error']=str(exc)
   results.append(result)
   print(mid,result['status'],result['passed'],'/',len(calls),result.get('error','')[:180],flush=True)
   write_json_atomic(run.dir/'templates.json',results)
  run.result(models=len(results));run.finish()
 except BaseException as exc:
  run.finish('failed',str(exc));raise


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('catalog');p.add_argument('--since',default='2026-10-24T02:31:48');main(p.parse_args())
