"""Fixed small CPU MLP and metadata baselines; preprocessing stays in the fit split."""
import warnings
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from metrics import position_weights

MLP_SETTINGS={'hidden_units':32,'epochs':80,'batch_size':256,'learning_rate':.001,'weight_decay':.01}

def fit_mlp(x,y,rounds,seed,*,threads=4):
    torch.set_num_threads(threads);torch.manual_seed(seed)
    weights=position_weights(y,rounds);keep=weights>0;y=np.asarray(y)[keep];weights=weights[keep]
    scaler=StandardScaler().fit(np.asarray(x[keep],dtype=np.float64));z=torch.from_numpy(scaler.transform(x[keep]).astype('float32'));labels=torch.tensor(y,dtype=torch.float32);w=torch.tensor(weights,dtype=torch.float32)
    network=torch.nn.Sequential(torch.nn.Linear(z.shape[1],32),torch.nn.ReLU(),torch.nn.Linear(32,1)).to('cpu')
    optimizer=torch.optim.AdamW(network.parameters(),lr=.001,weight_decay=.01)
    generator=torch.Generator(device='cpu').manual_seed(seed);losses=[]
    for epoch in range(80):
        order=torch.randperm(len(z),generator=generator);total=0.
        for batch in order.split(256):
            optimizer.zero_grad();logits=network(z[batch]).squeeze(1)
            loss=(torch.nn.functional.binary_cross_entropy_with_logits(logits,labels[batch],reduction='none')*w[batch]).mean()
            if not torch.isfinite(loss):raise ValueError('Non-finite MLP training loss')
            loss.backward();optimizer.step();total+=float(loss.detach())*len(batch)
        losses.append(total/len(z))
    network.eval();return scaler,network,losses

def score_mlp(model,x):
    scaler,network,_=model
    with torch.no_grad():
        parts=[]
        for start in range(0,len(x),512):
            z=torch.from_numpy(scaler.transform(x[start:start+512]).astype('float32'));parts.append(network(z).squeeze(1).numpy())
    values=np.concatenate(parts);assert np.isfinite(values).all();return values.astype(float)

def save_mlp(path,model):
    scaler,network,losses=model
    np.savez_compressed(path,mean=scaler.mean_,scale=scaler.scale_,w1=network[0].weight.detach().numpy(),b1=network[0].bias.detach().numpy(),w2=network[2].weight.detach().numpy(),b2=network[2].bias.detach().numpy(),training_loss=losses)

def metadata_features(rows,indices,include_length=True):
    columns=[[rows[i]['round']] + ([rows[i]['n_tokens']] if include_length else []) for i in indices]
    scenarios=np.array([[rows[i]['scenario']] for i in indices]);return np.asarray(columns,dtype=float),scenarios

def fit_metadata(rows,train,y,include_length=True,probe=None):
    numeric,scenarios=metadata_features(rows,train,include_length)
    if probe is not None:numeric=np.column_stack([numeric,probe])
    scaler=StandardScaler().fit(numeric);encoder=OneHotEncoder(handle_unknown='ignore',sparse_output=False).fit(scenarios)
    design=np.column_stack([scaler.transform(numeric),encoder.transform(scenarios)])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning)
        model=LogisticRegression(C=.1,solver='lbfgs',max_iter=2000,tol=1e-5).fit(design,y)
    if any(issubclass(w.category,ConvergenceWarning) for w in caught):raise RuntimeError('Metadata logistic convergence failure')
    return scaler,encoder,model,include_length

def score_metadata(fit,rows,indices,probe=None):
    scaler,encoder,model,include_length=fit;numeric,scenarios=metadata_features(rows,indices,include_length)
    if probe is not None:numeric=np.column_stack([numeric,probe])
    return model.decision_function(np.column_stack([scaler.transform(numeric),encoder.transform(scenarios)]))

def scenario_rates(rows,train,indices,y):
    episodes={rows[i]['episode']:(rows[i]['scenario'],int(label)) for i,label in zip(train,y)}
    default=float(np.mean([label for _,label in episodes.values()]));rates={}
    for name in {s for s,_ in episodes.values()}:rates[name]=float(np.mean([label for scenario,label in episodes.values() if scenario==name]))
    return np.array([rates.get(rows[i]['scenario'],default) for i in indices]),{'rates':rates,'unseen_scenario_fallback':default}


def save_metadata(path,fit):
    scaler,encoder,model,include_length=fit
    np.savez_compressed(path,mean=scaler.mean_,scale=scaler.scale_,categories=np.asarray(encoder.categories_[0],dtype=str),coef=model.coef_,intercept=model.intercept_,include_length=include_length)
