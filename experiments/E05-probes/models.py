import warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
from metrics import position_weights


def fit_logistic(x,y,rounds=None,seed=42):
    weights=position_weights(y,rounds) if rounds is not None else np.where(np.asarray(y)==1,len(y)/(2*np.sum(y)),len(y)/(2*(len(y)-np.sum(y))))
    keep=weights>0;x=np.asarray(x[keep],dtype=np.float64);y=np.asarray(y)[keep];weights=weights[keep]
    scaler=StandardScaler().fit(x);z=scaler.transform(x)
    model=LogisticRegression(C=.1,solver='lbfgs',max_iter=2000,tol=1e-5,random_state=seed)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning);model.fit(z,y,sample_weight=weights)
    if any(issubclass(w.category,ConvergenceWarning) for w in caught):raise RuntimeError('Logistic convergence failure')
    return scaler,model


def score(model,x):
    scaler,clf=model;return clf.decision_function(scaler.transform(np.asarray(x,dtype=np.float64)))


def fit_dom(x,y,rounds):
    w=position_weights(y,rounds);y=np.asarray(y);x=np.asarray(x,dtype=np.float64)
    positive=np.average(x[y==1],axis=0,weights=w[y==1]);negative=np.average(x[y==0],axis=0,weights=w[y==0])
    direction=positive-negative;direction/=max(np.linalg.norm(direction),1e-12)
    return direction,(positive+negative)/2


def score_dom(model,x):
    direction,center=model;return (x-center)@direction
