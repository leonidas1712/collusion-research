import numpy as np
import pytest
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from stream_model import fit,predict
from threadpoolctl import threadpool_limits


@pytest.mark.parametrize('cache_gib',[0,12])
def test_uniform_matches_weighted_logistic(cache_gib):
    rng=np.random.default_rng(18);lengths=[7,19,4,22,13,8];x=rng.normal(size=(sum(lengths),5))
    offsets=np.r_[0,np.cumsum(lengths)];rows=[{'capture_start':int(a),'capture_stop':int(b),'capture_tokens':int(b-a)} for a,b in zip(offsets[:-1],offsets[1:])]
    labels=np.array([0,1,1,0,0,1]);rw=np.array([1.,.8,1.2,.5,1.3,.7])
    with threadpool_limits(limits=1):
        model,info=fit(x,rows,list(range(6)),labels,rw,cache_gib=cache_gib)
        scale=StandardScaler().fit(x,sample_weight=np.repeat(1/np.array(lengths),lengths))
        clf=LogisticRegression(C=.1,max_iter=2000,tol=1e-8).fit(scale.transform(x),np.repeat(labels,lengths),sample_weight=np.repeat(rw/lengths,lengths))
        got=np.concatenate(predict(model,x,rows,list(range(6))))
        np.testing.assert_allclose(got,clf.decision_function(scale.transform(x)),atol=2e-5)
