"""Reconstruct saved scores and audit split isolation without fitting models."""
import json
import numpy as np
from replay2_models import metadata_features
from metrics import threshold_at_fpr,ema_max
from data import ROOT


def validate_variant(rows,x,path):
    pred=np.load(path/'predictions.npz');notes=json.loads((path/'folds.json').read_text());checks=[]
    exported=None
    if path.name=='pooled':
        export=ROOT/'runs/20261025-0240-e05-replay2-folds'
        exported={(n['seed'],n['fold']):n for n in json.loads((export/'folds.json').read_text())}
        original=[json.loads(s) for s in (export/'rows.jsonl').read_text().splitlines()]
        assert len(original)==len(rows)
        for a,b in zip(original,rows):
            for field in ('episode','request_idx','request_sha256','prompt_sha256','label','eligible'):assert a[field]==b[field]
    for note in notes:
        seed=note['seed'];si=list(pred['seeds']).index(seed);fold=note['fold'];split=np.load(path/f'split-s{seed}-f{fold}.npz');train,test,cal=[split[k] for k in ('train','test','calibration')]
        if exported is not None:
            for name in ('train','test','calibration'):np.testing.assert_array_equal(split[name],exported[(seed,fold)][name+'_indices'])
        groups=lambda ids:{rows[i]['family'] for i in ids}
        assert not groups(test)&(groups(train)|groups(cal));assert not groups(split['inner_train'])&groups(split['inner_validation'])
        assert set(split['inner_train'])|set(split['inner_validation'])<=set(train)
        assert all(rows[i]['condition']=='recruiting' for i in train)
        assert all(rows[i]['condition'] in ('control','alone') and not rows[i]['label'] for i in cal)
        if path.name=='loso':
            assert not {rows[i]['scenario'] for i in train}&{rows[i]['scenario'] for i in test}
            assert not {rows[i]['scenario'] for i in split['inner_train']}&{rows[i]['scenario'] for i in split['inner_validation']}
        for stack in note.get('stacking',{}).get('folds',[]):
            assert not set(stack['train_families'])&set(stack['test_families']);assert set(stack['train_families'])|set(stack['test_families'])<=groups(train)
            assert not set(stack['inner']['inner_train_families'])&set(stack['inner']['inner_validation_families'])
        errors={}
        for method,layer in [('nested',note['chosen_layer']),('fixed32',32)]:
            model=np.load(path/f'lr-s{seed}-f{fold}-l{layer}.npz');z=(x[test,layer].astype(float)-model['mean'])/model['scale'];reconstructed=(z@model['coef'].T+model['intercept']).ravel()
            error=float(np.max(np.abs(reconstructed-pred[method][si,test])));assert error<1e-9;errors[method]=error
            cz=(x[cal,layer].astype(float)-model['mean'])/model['scale'];cs=(cz@model['coef'].T+model['intercept']).ravel();episodes=np.array([rows[i]['episode'] for i in cal]);smooth=ema_max(cs,episodes)
            for fi,fpr in enumerate(pred['fprs']):
                threshold,_=threshold_at_fpr(cs,episodes,fpr);ema_threshold,_=threshold_at_fpr(smooth,episodes,fpr)
                np.testing.assert_allclose(pred['threshold_'+method][si,test,fi],threshold,rtol=0,atol=1e-9)
                np.testing.assert_allclose(pred['ema_threshold_'+method][si,test,fi],ema_threshold,rtol=0,atol=1e-9)
        for method,filename,length in [('scenario_round','scenario-round',False),('metadata_base','metadata-base',True),('metadata_probe','metadata-probe',True)]:
            if method not in pred.files:continue
            model=np.load(path/f'{filename}-s{seed}-f{fold}.npz');numeric,scenarios=metadata_features(rows,test,length)
            if method=='metadata_probe':numeric=np.column_stack([numeric,pred['nested'][si,test]])
            onehot=(scenarios==model['categories'][None,:]).astype(float);z=np.column_stack([(numeric-model['mean'])/model['scale'],onehot]);reconstructed=(z@model['coef'].T+model['intercept']).ravel()
            error=float(np.max(np.abs(reconstructed-pred[method][si,test])));assert error<1e-9;errors[method]=error
        if 'mlp' in pred.files:
            import torch
            torch.set_num_threads(4)
            layer=note['mlp']['layer'];model=np.load(path/f'mlp-s{seed}-f{fold}-l{layer}.npz');pieces=[];evaluation=np.r_[test,cal]
            for start in range(0,len(evaluation),512):
                values=x[evaluation[start:start+512],layer].copy();values-=model['mean'];values/=model['scale'];z=torch.from_numpy(values.astype('float32'))
                hidden=torch.relu(torch.nn.functional.linear(z,torch.from_numpy(model['w1']),torch.from_numpy(model['b1'])))
                pieces.append(torch.nn.functional.linear(hidden,torch.from_numpy(model['w2']),torch.from_numpy(model['b2'])).numpy().ravel())
            reconstructed=np.concatenate(pieces);error=float(np.max(np.abs(reconstructed[:len(test)]-pred['mlp'][si,test])));assert error<1e-5;errors['mlp']=error
            cs=reconstructed[len(test):];episodes=np.array([rows[i]['episode'] for i in cal]);smooth=ema_max(cs,episodes)
            for fi,fpr in enumerate(pred['fprs']):
                threshold,_=threshold_at_fpr(cs,episodes,fpr);ema_threshold,_=threshold_at_fpr(smooth,episodes,fpr)
                np.testing.assert_allclose(pred['threshold_mlp'][si,test,fi],threshold,rtol=0,atol=1e-5)
                np.testing.assert_allclose(pred['ema_threshold_mlp'][si,test,fi],ema_threshold,rtol=0,atol=1e-5)
        checks.append(dict(seed=int(seed),fold=int(fold),max_errors=errors,selected_and_fixed32_cutoffs_reconstructed=True))
    for si in range(len(pred['seeds'])):
        tested=np.concatenate([np.load(path/f"split-s{int(pred['seeds'][si])}-f{n['fold']}.npz")['test'] for n in notes if n['seed']==pred['seeds'][si]])
        assert len(set(tested))==len(tested) and set(tested)==set(pred['eligible'])
    return checks
