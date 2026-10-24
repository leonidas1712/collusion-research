"""Read-only recursive Volume download; directory entries are never treated as files."""
import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
import modal
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

async def main(args):
    remote=Path(args.remote);destination=ROOT/'runs'/remote.name
    run=start_run('e02-volume-download',experiment='E02',parents=[remote.name],settings={'remote':args.remote,'destination':str(destination),'read_only_remote':True,'workers':args.workers,'reuse_complete_local_files':True})
    try:
        volume=modal.Volume.from_name('collusion-activations');metadata=b''
        async for chunk in volume.read_file.aio(args.remote+'/meta.json'):metadata+=chunk
        assert json.loads(metadata)['status']=='finished','Only completed immutable runs may be downloaded/resumed'
        entries=await volume.listdir.aio(args.remote,recursive=True);records=[];semaphore=asyncio.Semaphore(args.workers)
        async def one(entry):
            if entry.type.name!='FILE':return
            relative=Path(entry.path).relative_to(remote);target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
            async with semaphore:
                if target.is_file() and target.stat().st_size==entry.size:
                    h=hashlib.sha256(target.read_bytes()).hexdigest()
                    records.append(dict(path=str(relative),size=entry.size,sha256=h,reused=True));return
                tmp=target.with_name(target.name+'.download-tmp');h=hashlib.sha256();size=0
                with tmp.open('wb') as f:
                    async for chunk in volume.read_file.aio(entry.path):f.write(chunk);h.update(chunk);size+=len(chunk)
                assert size==entry.size,(entry.path,size,entry.size)
                tmp.replace(target);records.append(dict(path=str(relative),size=size,sha256=h.hexdigest(),reused=False))
        await asyncio.gather(*(one(e) for e in entries))
        (run.dir/'files.json').write_text(json.dumps(records,indent=2));run.result(files=len(records),bytes=sum(r['size'] for r in records));run.finish();print('DOWNLOADED',destination,run.id)
    except BaseException as exc:run.finish('failed',str(exc));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('remote');p.add_argument('--workers',type=int,default=32);args=p.parse_args();assert 1<=args.workers<=64;asyncio.run(main(args))
