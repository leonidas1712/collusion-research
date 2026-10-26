"""Checks for reply weighting and post-token censoring in the exploratory probe."""
import numpy as np
from reasoning_stream_fit import fit, predict
from reasoning_stream_data import first_mention_cutoff

class CharacterTokenizer:
    def decode(self, ids):
        return ''.join(ids)

def test_cutoff_removes_first_secret_character_even_inside_token():
    enc=CharacterTokenizer()
    assert first_mention_cutoff(enc,['safe ','AB','CD',' after'],['ABCD'])==(1,True)
    assert first_mention_cutoff(enc,['safe A','BCD'],['ABCD'])==(0,True)
    assert first_mention_cutoff(enc,['safe'],['ABCD'])==(1,False)

def test_repeating_each_reply_tokens_preserves_fit_and_aggregates():
    rng=np.random.default_rng(12)
    x=rng.normal(size=(12,3)); y=np.array([0,1]*6)
    rows=[{'start':i,'stop':i+1,'reasoning_tokens':1,'clean_tokens':1,'round':1,'y':int(y[i])} for i in range(12)]
    a=fit(x,rows,list(range(12)),'y',False,42)
    lengths=np.arange(1,13)
    xx=np.repeat(x,lengths,axis=0)
    rr=[];start=0
    for r,n in zip(rows,lengths):
        rr.append({**r,'start':start,'stop':start+n,'reasoning_tokens':int(n),'clean_tokens':int(n)});start+=n
    b=fit(xx,rr,list(range(12)),'y',False,42)
    for u,v in zip(a,b):np.testing.assert_allclose(u,v,rtol=1e-5,atol=1e-6)
    pa=predict(a,x,rows,list(range(12)),False)
    pb=predict(b,xx,rr,list(range(12)),False)
    np.testing.assert_allclose([p.max() for p in pa],[p.max() for p in pb],atol=1e-5)

def test_horizons_count_empty_replies_and_preserve_paper_outcome():
    from reasoning_stream_labels import add_horizon_labels
    rows=[dict(episode='file-only',ordinal=i,stream_window='post_ask',y_immediate=int(i==4),y_near=1,label=0,reasoning_tokens=0 if i==3 else 2) for i in range(5)]
    rows += [dict(episode='held',ordinal=0,stream_window='post_ask',y_immediate=0,y_near=0,label=0,reasoning_tokens=2)]
    add_horizon_labels(rows)
    assert [r['eligible_replies_until_public'] for r in rows[:5]]==[4,3,2,1,0]
    assert [r['y_h1'] for r in rows[:5]]==[0,0,0,1,1]
    assert [r['y_h2'] for r in rows[:5]]==[0,0,1,1,1]
    assert [r['y_h3'] for r in rows[:5]]==[0,1,1,1,1]
    assert not any(r['y_round'] for r in rows)
    assert not rows[-1]['y_h3']

def test_combined_stream_normalization_and_empty_reasoning():
    from reasoning_stream_combined import normalizer,combine
    last=np.array([-1.,1.]);reason=[np.array([0.,2.]),np.array([2.,4.])]
    a=normalizer(last,reason)
    b=normalizer(last,[np.repeat(reason[0],7),reason[1]])
    for k in a:np.testing.assert_allclose(a[k],b[k])
    assert a['last_mean']==0 and a['last_sd']==1 and a['reasoning_mean']==2
    score,stream=combine(3.,np.array([]),a)
    assert score==3 and stream.tolist()==[3]
    score,stream=combine(-1.,np.array([0.,4.]),a)
    assert score==stream.max() and np.argmax(stream)==2
