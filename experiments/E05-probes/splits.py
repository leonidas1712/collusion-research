"""Constrained group splits using labels/categories only, never fitted scores."""
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold


def assign_folds(rows,eligible,seed,n_splits=5,unit='family',require_all=True):
    episodes={rows[i]['episode']:rows[i] for i in eligible}
    names=sorted(episodes);groups=np.asarray([episodes[e][unit] if unit=='family' else e for e in names])
    categories=np.asarray([('give_in' if episodes[e]['label']==1 else 'held') if episodes[e]['condition']=='recruiting' else episodes[e]['condition'] for e in names])
    required={'give_in','held','control','alone'} if require_all else {'give_in','held'}
    for attempt in range(500):
        actual_seed=seed+1009*attempt
        splitter=StratifiedGroupKFold(n_splits=n_splits,shuffle=True,random_state=actual_seed)
        assignments={};valid=True
        for fold,(_,test) in enumerate(splitter.split(np.zeros(len(names)),categories,groups)):
            if not required.issubset(set(categories[test])):valid=False;break
            for i in test:assignments[names[i]]=fold
        if valid:return assignments,actual_seed
    raise ValueError(f'Cannot find category-complete {n_splits}-fold {unit} split')


def inner_split(rows,train,seed,unit='family'):
    assignment,actual_seed=assign_folds(rows,train,seed,n_splits=4,unit=unit,require_all=False)
    validation=np.asarray([i for i in train if assignment[rows[i]['episode']]==0]);fit=np.asarray([i for i in train if assignment[rows[i]['episode']]!=0])
    assert not {rows[i][unit] if unit=='family' else rows[i]['episode'] for i in fit}&{rows[i][unit] if unit=='family' else rows[i]['episode'] for i in validation}
    return fit,validation,actual_seed
