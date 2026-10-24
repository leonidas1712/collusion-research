"""Report the approved main replay, including the original control miss and diagnostics."""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from collusion.runs import start_run

ids={'replay':'20261024-1018-e02-activation-replay','client':'20261024-1818-e02-main-modal-client',
     'validation':'20261024-1918-e02-main-replay-validation','probe':'20261024-1918-e02-exposure-positive-control',
     'diagnostic':'20261024-1920-e02-exposure-diagnostics','curve':'20261024-1921-e02-exposure-layer-curve'}
run=start_run('e02-main-replay-report',experiment='E02',parents=list(ids.values()),settings={'app_id':'ap-DdAMunexkDGOOOpHb9fN8J','approved_cap_usd':9,'matplotlib':matplotlib.__version__})
def load(name,file='summary.json'):return json.loads((ROOT/'runs'/ids[name]/file).read_text())
validation=load('validation');probe=load('probe');diagnostic=load('diagnostic');curve=load('curve');replay=load('replay');client=load('client','meta.json');meta=load('replay','meta.json')
billing=json.loads(subprocess.check_output(['modal','billing','report','--for','today','--resolution','h','--show-resources','--json'],text=True))
billing=[r for r in billing if r.get('object_id')=='ap-DdAMunexkDGOOOpHb9fN8J']
(run.dir/'billing.json').write_text(json.dumps(billing,indent=2))
app=json.loads(subprocess.check_output(['modal','app','info','ap-DdAMunexkDGOOOpHb9fN8J','--json'],text=True));assert app['lifecycle']['state']=='stopped'
(run.dir/'app.json').write_text(json.dumps(app,indent=2))
cost=sum(float(r['cost']) for r in billing)
local=ROOT/'runs'/ids['replay'];download_bytes=sum(p.stat().st_size for p in local.rglob('*') if p.is_file())
result=dict(run_ids=ids,requests=validation['requests'],episodes=validation['episodes'],
    client_wall_seconds=client['results']['client_wall_seconds'],remote_wall_seconds=(datetime.fromisoformat(meta['ended'])-datetime.fromisoformat(meta['started'])).total_seconds(),
    app_billed_usd=cost,billing_may_lag=True,approved_cap_usd=9,app_stopped=True,
    download_bytes=download_bytes,download_egress_allowance_usd=download_bytes/2**30*.04,
    prompt_tokens=validation['prompt_tokens'],reply_tokens=validation['reply_tokens'],
    decoder_seconds=validation['decoder_seconds'],processing_seconds=validation['processing_seconds'],
    prompt_tokens_per_decoder_second=validation['prompt_tokens']/validation['decoder_seconds'],
    prompt_tokens_per_processing_second=validation['prompt_tokens']/validation['processing_seconds'],
    scored_requests=validation['statuses']['scored'],missing_replies=validation['statuses']['missing_response'],
    weighted_nll=validation['weighted_nll'],weighted_top5=validation['weighted_top5'],
    request_nll_quantiles=validation['request_nll_quantiles'],peak_cuda_memory_gib=replay['peak_cuda_memory_bytes']/2**30,
    layer_curve=curve['curve'],last_layer_control=probe,exposure_audit=curve['exposure_counts'],
    bitwise_prompt_only_overlap=diagnostic['prompt_only_benchmark_overlap'])
(run.dir/'results.json').write_text(json.dumps(result,indent=2))
with plt.rc_context({'font.size':10,'pdf.fonttype':42,'svg.fonttype':'none'}):
    fig,axes=plt.subplots(1,2,figsize=(9,4),layout='constrained')
    xs=[r['layer'] for r in curve['curve']];ys=[r['heldout_auroc'] for r in curve['curve']]
    for ax in axes:
        ax.scatter(xs,ys,color='#235a9f',marker='o',s=38,zorder=3)
        ax.axhline(.98,color='#666666',linestyle='--',linewidth=1,label='Diagnostic target 0.98')
        ax.set(xlabel='Decoder block (zero-based)',ylabel='Held-out AUROC',xticks=xs,xlim=(12,67))
        ax.spines[['top','right']].set_visible(False)
    axes[0].set(ylim=(0,1.03),title='Full AUROC scale');axes[1].set(ylim=(.94,1.005),title='Detail: 0.94–1.00')
    for xx,yy in zip(xs,ys):axes[1].annotate(f'{yy:.4f}',(xx,yy),xytext=(0,7),textcoords='offset points',ha='center',fontsize=8)
    axes[0].legend(loc='lower right',frameon=False)
    fig.suptitle('Token-exposure positive control: 43 held-out episodes, 816 steps',fontsize=12)
    fig.savefig(run.dir/'exposure-layer-curve.png',dpi=180,facecolor='white')
    fig.savefig(run.dir/'exposure-layer-curve.svg',facecolor='white')
    plt.close(fig)
(run.dir/'figure-note.md').write_text('Post-hoc diagnostic at owner-specified layers after the layer-63 miss. Same fixed episode split and fixed probe settings. Points only; unmeasured layers are not interpolated. No uncertainty interval estimated. Right panel explicitly zooms the AUROC scale. These are not independent confirmatory estimates after layer selection. Source: '+ids['curve']+'/curve.csv.\n')
print(json.dumps(result,indent=2));run.result(requests=3034,cost_usd=cost,weighted_nll=result['weighted_nll'],middle_layer_26_auc=curve['curve'][1]['heldout_auroc']);run.finish();print(run.id)
