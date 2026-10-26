"""Download committed full-replay shards as they finish; never modifies the Volume."""
import argparse,asyncio,hashlib,json,sys,shutil
from pathlib import Path
import modal
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run,write_json_atomic


async def main(args):
    plan_path=Path(args.plan).resolve();plan=json.loads(plan_path.read_text());journal=plan_path.parent/'completed-shards.json'
    run=start_run('e02-gpt-oss-stream-download',experiment='E02',parents=[plan_path.parent.name,Path(args.client).name],
        settings={'read_only_remote':True,'workers':args.workers,'expected_shards':len(plan['shards'])})
    volume=modal.Volume.from_name('collusion-activations');done={};semaphore=asyncio.Semaphore(args.workers)
    try:
        while len(done)<len(plan['shards']):
            state=json.loads(journal.read_text()) if journal.exists() else {'completed':{}}
            for shard,entry in state['completed'].items():
                if shard in done:continue
                remote=Path(entry['remote']);destination=ROOT/'runs'/remote.name
                raw=b''
                async for chunk in volume.read_file.aio(str(remote/'meta.json')):raw+=chunk
                assert json.loads(raw)['status']=='finished'
                files=await volume.listdir.aio(str(remote),recursive=True);records=[]
                async def download(item):
                    if item.type.name!='FILE':return
                    relative=Path(item.path).relative_to(remote);target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
                    async with semaphore:
                        assert shutil.disk_usage(ROOT).free-item.size>=48*2**30, 'Download stopped to preserve 40 GiB plus concurrent-write reserve'
                        if target.is_file() and target.stat().st_size==item.size:
                            records.append(dict(path=str(relative),size=item.size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),reused=True));return
                        tmp=target.with_name(target.name+'.download-tmp');digest=hashlib.sha256();size=0
                        with tmp.open('wb') as output:
                            async for chunk in volume.read_file.aio(item.path):output.write(chunk);digest.update(chunk);size+=len(chunk)
                        assert size==item.size
                        tmp.replace(target);records.append(dict(path=str(relative),size=size,sha256=digest.hexdigest(),reused=False))
                await asyncio.gather(*(download(item) for item in files))
                write_json_atomic(run.dir/(Path(shard).stem+'-files.json'),records)
                done[shard]=dict(remote=str(remote),local=str(destination),bytes=sum(r['size'] for r in records),files=len(records))
                write_json_atomic(run.dir/'downloads.json',done)
                print('DOWNLOADED_SHARD',shard,len(done),len(plan['shards']),done[shard]['bytes'],flush=True)
            client_summary=Path(args.client)/'summary.json'
            if client_summary.exists():
                client=json.loads(client_summary.read_text())
                if client.get('error'):raise RuntimeError('GPU client stopped with an error; completed downloads preserved')
                if len(done)<len(plan['shards']):raise RuntimeError('Finished client lacks required shard coverage')
            if len(done)<len(plan['shards']):await asyncio.sleep(10)
        run.result(shards=len(done),bytes=sum(r['bytes'] for r in done.values()));run.finish();print('DOWNLOAD_RUN',run.dir)
    except BaseException as exc:run.finish('failed',str(exc));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--client',required=True);p.add_argument('--workers',type=int,default=8)
    args=p.parse_args();assert 1<=args.workers<=8;asyncio.run(main(args))
