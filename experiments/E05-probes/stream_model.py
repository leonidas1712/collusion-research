"""Memory-bounded CPU logistic fitting for reply-labelled activation streams."""
import time
import numpy as np
from scipy.optimize import minimize
from stream_loss import reply_loss_gradient


def token_indices(rows,indices):
    lengths=np.array([rows[i]['capture_tokens'] for i in indices])
    ids=np.concatenate([np.asarray(rows[i]['capture_indices'],dtype=int) if 'capture_indices' in rows[i] else np.arange(rows[i]['capture_start'],rows[i]['capture_stop']) for i in indices])
    return ids,np.r_[0,np.cumsum(lengths)]


def blocks(x,ids,size=2048):
    for start in range(0,len(ids),size):
        stop=min(start+size,len(ids))
        yield start,stop,np.asarray(x[ids[start:stop]],dtype=np.float64).reshape(stop-start,-1)


def scaler(x,ids,offsets):
    lengths=np.diff(offsets);weights=np.repeat(1/lengths,lengths);den=float(len(lengths))
    dimension=int(np.prod(x.shape[1:]));mean=np.zeros(dimension);second=np.zeros(dimension)
    for a,b,xx in blocks(x,ids):
        w=weights[a:b];mean+=w@xx;second+=w@(xx*xx)
    mean/=den;variance=np.maximum(second/den-mean*mean,0)
    scale=np.sqrt(variance);scale[scale<1e-12]=1
    return mean,scale


def fit(x,rows,indices,labels,reply_weights,*,swim=False,weighted=False,C=.1,maxiter=2000,cache_gib=12):
    keep=np.asarray(reply_weights)>0;indices=np.asarray(indices)[keep];labels=np.asarray(labels)[keep];rw=np.asarray(reply_weights,dtype=float)[keep]
    ids,offsets=token_indices(rows,indices);mean,scale=scaler(x,ids,offsets)
    n=len(ids);d=len(mean);calls=0;begin=time.monotonic()
    dense=None
    if n*d*8<=cache_gib*2**30:
        dense=np.empty((n,d),dtype=np.float64)
        for a,b,xx in blocks(x,ids):dense[a:b]=(xx-mean)/scale
    print('TRAIN_MATRIX',n,d,'cached-float64' if dense is not None else 'chunked-float64',flush=True)
    def objective(theta):
        nonlocal calls
        direction=theta[:-1]/scale;bias=theta[-1]-mean@direction
        if dense is not None:z=dense@theta[:-1]+theta[-1]
        else:
            z=np.empty(n)
            for a,b,xx in blocks(x,ids):z[a:b]=xx@direction+bias
        value=0.;dz=np.zeros(n)
        for j,(a,b) in enumerate(zip(offsets[:-1],offsets[1:])):
            loss,g=reply_loss_gradient(z[a:b],labels[j],swim=swim,weighted=weighted)
            value+=rw[j]*loss;dz[a:b]=rw[j]*g
        if dense is not None:grad=dense.T@dz+theta[:-1]/C
        else:
            raw_grad=np.zeros(d)
            for a,b,xx in blocks(x,ids):raw_grad+=xx.T@dz[a:b]
            grad=(raw_grad-mean*dz.sum())/scale+theta[:-1]/C
        value+=.5*(theta[:-1]@theta[:-1])/C
        calls+=1
        if calls%10==0:print('OBJECTIVE',calls,round(value,6),round(time.monotonic()-begin,1),flush=True)
        return value,np.r_[grad,dz.sum()]
    result=minimize(objective,np.zeros(d+1),method='L-BFGS-B',jac=True,options={'maxiter':maxiter,'gtol':1e-5,'ftol':1e-10,'maxls':30})
    if not result.success:raise RuntimeError('Expanded probe optimizer failed: '+str(result.message))
    return {'mean':mean,'scale':scale,'coef':result.x[:-1],'intercept':result.x[-1]}, {'iterations':int(result.nit),'evaluations':calls,'objective':float(result.fun),'seconds':time.monotonic()-begin,'tokens':n,'replies':len(indices),'dimension':d,'matrix_cache':'float64' if dense is not None else 'chunked','termination':str(result.message)}


def predict(model,x,rows,indices):
    direction=model['coef']/model['scale'];bias=float(model['intercept'])-model['mean']@direction
    values=[]
    for i in indices:
        r=rows[i];ix=np.asarray(r['capture_indices'],dtype=int) if 'capture_indices' in r else slice(r['capture_start'],r['capture_stop']);xx=np.asarray(x[ix],dtype=float).reshape(r['capture_tokens'],-1)
        values.append(xx@direction+bias)
    return values
