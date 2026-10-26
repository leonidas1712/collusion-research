"""Freeze final incoming/generated capture positions and seeded projections offline."""
import hashlib,json,sys
from collections import Counter
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic
from gpt_oss_stream_positions import positions,ROLE
from gpt_oss_stream_capture import FULL_LAYERS,PROJECTION_SEED,PROJECTION_DIM


def main():
    old=ROOT/'runs/20261026-0540-e02-gpt-oss-blocking-plan'
    base=json.loads((old/'plan.json').read_text())
    run=start_run('e02-gpt-oss-stream-plan',experiment='E02',parents=[old.name],tags=['exploratory','approved-expanded-capture','offline-plan'],settings={'cap_usd':15,'full_layers':FULL_LAYERS,'projection_seed':PROJECTION_SEED,'projection_dim':PROJECTION_DIM,'benchmark_requests':20})
    try:
        (run.dir/'cache').mkdir();(run.dir/'shards').mkdir()
        rng=np.random.default_rng(PROJECTION_SEED)
        matrix=(rng.integers(0,2,size=(24,2880,PROJECTION_DIM),dtype=np.int8)*2-1).astype(np.float16)/np.float16(np.sqrt(PROJECTION_DIM))
        projection=run.dir/'cache/projection.npz';np.savez_compressed(projection,projection=matrix)
        sha=hashlib.sha256(projection.read_bytes()).hexdigest()
        episodes={};parts=[];role_counts=Counter();incoming_control=0;total_positions=0
        for part in base['shards']:
            payload=json.loads((old/part['path']).read_text());payload.update(full_layers=FULL_LAYERS,projection_sha256=sha)
            for row in payload['rows']:
                source=row['source_path']
                if source not in episodes:episodes[source]=json.loads(Path(source).read_text())
                row.update(positions(row,episodes[source]))
                role_counts.update(row['capture_roles']);total_positions+=len(row['capture_positions'])
                if row['condition']=='control':incoming_control+=row['capture_roles'].count(ROLE['incoming'])
            target=run.dir/part['path'];write_json_atomic(target,payload)
            parts.append({**part,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'capture_positions':sum(len(r['capture_positions']) for r in payload['rows'])})
            print('MAPPED',part['path'],total_positions,flush=True)
        bytes_per_token=(len(FULL_LAYERS)*2880+24*PROJECTION_DIM)*2
        raw=total_positions*bytes_per_token+3330*24*2880*4
        previous=ROOT/'runs/20261026-0653-e02-gpt-oss-blocking-client'
        shared=ROOT/'runs/20261026-0652-e02-gpt-oss-blocking-launch-plan'
        counts={**base['counts'],'capture_positions':total_positions,'role_counts':{k:role_counts[v] for k,v in ROLE.items()},'control_incoming_positions':incoming_control,'activation_raw_bytes':raw,'activation_raw_gib':raw/2**30,'prior_throughput_projection_usd':base['counts']['projection_usd']+.0441,'projection_usd':base['counts']['input_tokens']/1128.8*1.5*.0009+1+.0441}
        m={k:v for k,v in base.items() if k not in ['shards','counts','primary_report_required','sources']}
        m.update(capture_spec='incoming_and_generated_prefixes_v1',budget_approval='shared_cap_15usd_v1',approval='Final incoming/generated positions, four full layers fp16 plus all-layer256 projection; USD15 including earlier startup',budget_root=str(shared),shards=parts,counts=counts,projection_path=str(projection),projection_sha256=sha,full_layers=FULL_LAYERS,projection_seed=PROJECTION_SEED,projection_dim=PROJECTION_DIM)
        m['sources']={str(projection):sha}
        for name in ['gpt_oss_stream_capture.py','gpt_oss_stream_positions.py','gpt_oss_stream_budget.py','modal_gpt_oss_stream.py','gpt_oss_replay.py','replay.py','fidelity.py']:
            p=ROOT/'experiments/E02-activation-replay'/name;m['sources'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        write_json_atomic(run.dir/'plan.json',m);write_json_atomic(run.dir/'counts.json',counts);(ROOT/'private/stream_launch_plan.txt').write_text(str(run.dir/'plan.json'))
        run.result(**counts);run.finish();print('FINAL_STREAM_PLAN',run.dir/'plan.json');print(json.dumps(counts))
    except BaseException as e:run.finish('failed',str(e));raise

if __name__=='__main__':main()
