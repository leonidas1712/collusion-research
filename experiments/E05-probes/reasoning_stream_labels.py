"""Reply horizons count eligible requests, including replies with no reasoning."""
from collections import defaultdict

VARIANTS=['immediate','h1','h2','h3','round']

def add_horizon_labels(rows):
    groups=defaultdict(list)
    for i,r in enumerate(rows):
        for k in [1,2,3]:r['y_h'+str(k)]=0
        # The paper's A label additionally requires the channel-publication
        # episode outcome; the timing boundary remains first public emission.
        r['y_round']=int(bool(r['label']) and bool(r['y_near']))
        r['eligible_replies_until_public']=None
        if r['stream_window']=='post_ask':groups[r['episode']].append(i)
    for indices in groups.values():
        indices.sort(key=lambda i:rows[i]['ordinal'])
        actions=[j for j,i in enumerate(indices) if rows[i]['y_immediate']]
        assert len(actions)<=1
        if not actions:continue
        action=actions[0]
        assert action==len(indices)-1
        for j,i in enumerate(indices):
            distance=action-j;rows[i]['eligible_replies_until_public']=distance
            for k in [1,2,3]:rows[i]['y_h'+str(k)]=int(distance<=k)
    return rows
