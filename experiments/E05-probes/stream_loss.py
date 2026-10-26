"""Reply-level streaming losses with explicit gradients through token weights."""
import numpy as np
from scipy.special import expit,softmax


def smooth_logits(z,window=16):
    z=np.asarray(z,dtype=float)
    if len(z)<window:return np.array([z.mean()])
    sums=np.r_[0.,np.cumsum(z)]
    return (sums[window:]-sums[:-window])/window


def smooth_adjoint(g,n,window=16):
    if n<window:return np.full(n,float(g[0])/n)
    # Each full-window logit receives a gradient spread equally over its tokens.
    delta=np.zeros(n+1);delta[:len(g)]+=g/window;delta[window:window+len(g)]-=g/window
    return np.cumsum(delta[:-1])


def reply_loss_gradient(logits,label,*,swim=False,weighted=False,window=16,tau=1.):
    z=np.asarray(logits,dtype=float)
    if not len(z):raise ValueError('Empty stream')
    x=smooth_logits(z,window) if swim else z
    loss=np.logaddexp(0,x)-label*x
    weights=softmax(x/tau) if weighted else np.full(len(x),1/len(x))
    value=float(weights@loss)
    grad=weights*(expit(x)-label)
    if weighted:grad+=weights*(loss-value)/tau
    return value,smooth_adjoint(grad,len(z),window) if swim else grad


def inference_scores(logits,alpha=2/17,rolling_window=10):
    z=np.asarray(logits,dtype=float)
    if not len(z):raise ValueError('Empty stream')
    ema=np.empty(len(z));ema[0]=z[0]
    for i in range(1,len(z)):ema[i]=alpha*z[i]+(1-alpha)*ema[i-1]
    # A short prefix has an available-token mean; full windows thereafter.
    sums=np.r_[0.,np.cumsum(z)];counts=np.minimum(np.arange(1,len(z)+1),rolling_window)
    rolling=(sums[1:]-sums[np.maximum(0,np.arange(1,len(z)+1)-rolling_window)])/counts
    return {'raw':z,'ema':ema,'rolling10':rolling}
