"""Frozen broad keyword scores at each selected captured prefix, no future tokens."""
import argparse,json
from pathlib import Path
import numpy as np
from reasoning_stream_text import patterns
from reasoning_stream_data import harmony_encoding
import re

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);a=p.parse_args();rows=json.loads((a.data/'replies.json').read_text());enc=harmony_encoding();arrays={s:np.zeros(sum(r['capture_tokens'] for r in rows),dtype=np.uint8) for s in ['incoming','action_time']}
 for j,r in enumerate(rows):
  with np.load(r['capture_source']) as z:
   ids=z['input_ids'].tolist();positions=z['capture_positions'];roles=z['capture_roles']
  regex=re.compile('|'.join(patterns(r['scenario'],True)),re.I)
  for stream in arrays:
   selected=np.flatnonzero(roles==0) if stream=='incoming' else np.arange(len(positions));segment=[];previous=None;seen=False
   for k in selected:
    position=int(positions[k])
    if previous is None or position!=previous+1:segment=[]
    segment.append(ids[position]);seen=seen or bool(regex.search(enc.decode(segment)));arrays[stream][r['capture_start']+k]=seen;previous=position
  if j%100==0:print('KEYWORDS',j,len(rows),flush=True)
 np.savez(a.data/'keyword_broad_streams.npz',**arrays)
 (a.data/'keyword_broad_streams.json').write_text(json.dumps({'source':'reasoning_stream_text.patterns(scenario,broad=True), fixed before evaluating the expanded keyword baseline','protected_values_used':False,'streams':['incoming','action_time'],'matching':'decoded observed contiguous segment only; running match persists across gaps; no synthetic phrases across uncaptured gaps','null':'binary any-match in observed prefix'},indent=2)+'\n')
