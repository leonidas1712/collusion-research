"""Snapshot public serving endpoints and HF model metadata for target selection."""
import argparse
import json
import sys
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic

MODELS = {
 'qwen/qwen3-32b':'Qwen/Qwen3-32B',
 'qwen/qwen3.5-27b':'Qwen/Qwen3.5-27B',
 'mistralai/ministral-14b-2512':'mistralai/Ministral-3-14B-Instruct-2512',
 'qwen/qwen3-14b':'Qwen/Qwen3-14B',
 'google/gemma-3-27b-it':'google/gemma-3-27b-it',
 'mistralai/mistral-small-3.2-24b-instruct':'mistralai/Mistral-Small-3.2-24B-Instruct-2506',
 'qwen/qwen3-30b-a3b-instruct-2507':'Qwen/Qwen3-30B-A3B-Instruct-2507',
 'openai/gpt-oss-20b':'openai/gpt-oss-20b',
 'meta-llama/llama-3.3-70b-instruct':'meta-llama/Llama-3.3-70B-Instruct',
 'ibm-granite/granite-4.2-8b':'ibm-granite/granite-4.2-8b',
 'ibm-granite/granite-3.3-8b-instruct':'ibm-granite/granite-3.3-8b-instruct',
}

def fetch(url):
 try:
  with urllib.request.urlopen(url,timeout=60) as response:
   return json.load(response)
 except Exception as exc:
  return {'error':str(exc),'url':url}

def collect(item):
 mid,hf=item
 endpoint_url='https://openrouter.ai/api/v1/models/'+mid+'/endpoints'
 hf_url='https://huggingface.co/api/models/'+hf
 metadata=fetch(hf_url)
 commit=metadata.get('sha','main')
 return {'model':mid,'hf_model':hf,'endpoint_url':endpoint_url,'endpoints':fetch(endpoint_url),
         'hf_url':hf_url,'hf':metadata,'config':fetch('https://huggingface.co/'+hf+'/resolve/'+commit+'/config.json')}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--model', nargs=2, action='append', metavar=('API_ID','HF_ID'),
                     help='Catalog this pair; repeat for several. Omit for the original screen.')
 args=parser.parse_args()
 selected=dict(args.model) if args.model else MODELS
 run=start_run('e03-target-catalog',experiment='E03',settings={'models':selected},tags=['model-selection'])
 try:
  with ThreadPoolExecutor(max_workers=6) as pool:
   entries=list(pool.map(collect,selected.items()))
  write_json_atomic(run.dir/'catalog.json',entries)
  for entry in entries:
   hf=entry['hf'];print(entry['model'],'HF',hf.get('sha'),hf.get('safetensors',{}).get('total'),'gated',hf.get('gated'))
   for e in entry['endpoints'].get('data',{}).get('endpoints',[]):
    if 'tools' in e.get('supported_parameters',[]):print(' ',e['provider_name'],e['quantization'],e['pricing'])
  run.result(models=len(entries));run.finish()
 except BaseException as exc:
  run.finish('failed',str(exc));raise
