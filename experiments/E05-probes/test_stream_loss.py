import numpy as np
import pytest
from stream_loss import reply_loss_gradient,inference_scores

@pytest.mark.parametrize('n',[1,7,16,23])
@pytest.mark.parametrize('label',[0,1])
@pytest.mark.parametrize('swim',[False,True])
@pytest.mark.parametrize('weighted',[False,True])
def test_gradient(n,label,swim,weighted):
    z=np.random.default_rng(n).normal(size=n)
    loss,g=reply_loss_gradient(z,label,swim=swim,weighted=weighted)
    numeric=[]
    for i in range(n):
        e=np.zeros(n);e[i]=1e-5
        a=reply_loss_gradient(z+e,label,swim=swim,weighted=weighted)[0]
        b=reply_loss_gradient(z-e,label,swim=swim,weighted=weighted)[0]
        numeric.append((a-b)/2e-5)
    assert np.isfinite(loss)
    np.testing.assert_allclose(g,numeric,atol=1e-8,rtol=1e-6)

def test_inference_is_prefix_causal():
    z=np.random.default_rng(3).normal(size=40)
    whole=inference_scores(z)
    for n in [1,7,16,25]:
        prefix=inference_scores(z[:n])
        for key in whole:np.testing.assert_array_equal(prefix[key],whole[key][:n])

def test_weighting_uses_positive_logits_for_both_labels():
    # A single confident false positive must dominate the harmless-reply loss.
    z=np.array([-10.,-10.,10.])
    weighted,_=reply_loss_gradient(z,0,weighted=True)
    uniform,_=reply_loss_gradient(z,0,weighted=False)
    assert weighted>2*uniform
