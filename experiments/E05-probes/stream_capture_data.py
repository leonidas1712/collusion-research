"""Validate expanded capture and assemble immutable CPU feature arrays."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import sys
import numpy as np
from reasoning_stream_data import ROOT,DATA
from collusion.runs import start_run,write_json_atomic


def prepare(plan_path,download_path):
    plan=json.loads(plan_path.read_text());downloads=json.loads(download_path.read_text())
    assert set(downloads)=={s['path'] for s in plan['shards']},'Incomplete download coverage'
    source=Path(plan['source_data']);source=source if source.is_absolute() else ROOT/source
    original=json.loads((source/'replies.json').read_text());by_id={r['row_id']:r for r in original}
    entries=[]
    for shard in plan['shards']:
        path=plan_path.parent/shard['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==shard['sha256']
        wanted=json.loads(path.read_text())['rows'];local=Path(downloads[shard['path']]['local'])
        actual=json.loads((local/'index.json').read_text());assert len(actual)==len(wanted)
        for w,a in zip(wanted,actual):
            assert w['row_id']==a['row_id'] and w['request_sha256']==a['request_sha256']
            entries.append((w,a,local/a['file']))
    entries.sort(key=lambda x:by_id[x[0]['row_id']]['stream_index'])
    assert len(entries)==3330 and len({w['row_id'] for w,_,_ in entries})==3330
    n=sum(len(w['capture_positions']) for w,_,_ in entries);required=n*(4*2880+24*256)*2
    assert shutil.disk_usage(ROOT).free-required>=44*2**30,'Insufficient space to preserve40GiB plus reserve'
    run=start_run('e05-expanded-stream-data',experiment='E05',parents=[plan_path.parent.name,download_path.parent.name,source.name],tags=['exploratory','cpu-only'],settings={'requests':len(entries),'tokens':n,'full_layers':plan['full_layers'],'projection_dim':256,'dtype':'float16','plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest()})
    try:
        full=np.lib.format.open_memmap(run.dir/'full.npy',mode='w+',dtype='float16',shape=(n,4,2880))
        projected=np.lib.format.open_memmap(run.dir/'projected.npy',mode='w+',dtype='float16',shape=(n,24,256))
        last=np.load(DATA/'features.npy',mmap_mode='r');rows=[];roles=[];positions=[];offsets=[];cursor=0;fidelity={};max_delta=0.
        for j,(w,a,path) in enumerate(entries):
            r=by_id[w['row_id']];count=len(w['capture_positions'])
            with np.load(path,allow_pickle=False) as z:
                ids=w['prompt_ids']+w['reply_ids']
                assert z['input_ids'].tolist()==ids
                for k in ['capture_positions','capture_roles']:assert z[k].tolist()==w[k]
                assert z['full_layers'].tolist()==[6,12,18,23] and z['projection_layers'].tolist()==list(range(24))
                assert z['residual_full'].shape==(4,count,2880) and z['residual_projected'].shape==(24,count,256)
                assert z['residual_full'].dtype==z['residual_projected'].dtype==np.float16
                assert all(np.isfinite(z[k]).all() for k in ['residual_full','residual_projected','residual_last'])
                old=np.asarray(last[r['index']],dtype=float);new=z['residual_last'].astype(float)
                delta=float(np.linalg.norm(new-old)/max(np.linalg.norm(old),1e-12));max_delta=max(delta,max_delta)
                assert delta<.005,('Last-prompt parity failure',r['row_id'],delta)
                li=np.flatnonzero(z['capture_roles']==4);assert len(li)==1
                assert np.array_equal(z['residual_full'][:,li[0]],z['residual_last'][[6,12,18,23]].astype(np.float16))
                assert all(p<len(w['prompt_ids']) or w['first_value_token_position'] is None or p<w['first_value_token_position'] for p in w['capture_positions'])
                full[cursor:cursor+count]=z['residual_full'].transpose(1,0,2)
                projected[cursor:cursor+count]=z['residual_projected'].transpose(1,0,2)
                roles.extend(z['capture_roles'].tolist());positions.extend(z['capture_positions'].tolist());offsets.extend(z['offset_to_first_public_secret'].tolist())
            rows.append({**r,'original_stream_index':r['stream_index'],'stream_index':j,'capture_start':cursor,'capture_stop':cursor+count,'capture_tokens':count,'capture_source':str(path.relative_to(ROOT)),'first_public_value_token_position':w['first_public_value_token_position'],'first_value_token_position':w['first_value_token_position'],'prompt_length':len(w['prompt_ids'])})
            cursor+=count
            provider=w['served_provider'];bucket=fidelity.setdefault(provider,{'all':[],'reasoning':[],'answer':[]});bucket['all'].append(a['fidelity'])
            for name in ['reasoning','answer']:bucket[name].append(a['segments'][name])
            if j%100==0:print('VALIDATED',j,len(entries),flush=True)
        full.flush();projected.flush();assert cursor==n
        np.savez(run.dir/'positions.npz',roles=np.array(roles,dtype=np.int8),positions=np.array(positions,dtype=np.int32),offset_to_first_public_secret=np.array(offsets,dtype=np.int32))
        write_json_atomic(run.dir/'replies.json',rows)
        totals={}
        for provider,segments in fidelity.items():
            totals[provider]={}
            for segment,values in segments.items():
                nk='n_reply_tokens' if segment=='all' else 'n_tokens';den=sum(v[nk] for v in values)
                totals[provider][segment]={'tokens':den,**{k:sum(v[k]*v[nk] for v in values if v[nk])/den if den else None for k in ['mean_token_nll','top5_fraction']}}
        write_json_atomic(run.dir/'fidelity.json',totals)
        check={'requests':len(rows),'tokens':n,'recruiting':sum(r['condition']=='recruiting' for r in rows),'controls':sum(r['condition']=='control' for r in rows),'max_old_last_relative_l2':max_delta,'finite':True,'exact_full_last_fp16_parity':True,'all_before_first_generated_value_token':True,'free_gib':shutil.disk_usage(ROOT).free/2**30}
        assert check['recruiting']==2205 and check['controls']==1125
        write_json_atomic(run.dir/'verification.json',check);run.result(**check);run.finish();print('DATA_RUN',run.dir,flush=True)
    except BaseException as e:run.finish('failed',str(e));raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--downloads',type=Path,required=True);a=p.parse_args();prepare(a.plan,a.downloads)
