import json, sys, glob, os
base=sys.argv[1]
S={'Real':{},'Prevista':{},'Programada':{}}
for f in sorted(glob.glob(os.path.join(base,'2025??','r.json'))):
    d=json.load(open(f))
    for x in d['included']:
        if x['type'] in S:
            for v in x['attributes']['values']:
                S[x['type']][v['datetime']]=v['value']
ts=sorted(t for t in S['Real'] if t in S['Prevista'])
print('n 5-min points', len(ts), ts[0], ts[-1])
# hourly means of real & prevista using hour prefix
from collections import defaultdict
def hourly(series):
    h=defaultdict(list)
    for t,v in series.items():
        h[t[:13]].append(v)
    return {k:sum(v)/len(v) for k,v in h.items() if len(v)>=10}
R=hourly(S['Real']); P=hourly(S['Prevista']); G=hourly(S['Programada'])
def rep(name,pairs):
    pairs=[(a,b) for a,b in pairs if a and b]
    m=100*sum(abs(a-b)/a for a,b in pairs)/len(pairs)
    print(f'{name:45s} N={len(pairs)} MAPE={m:.2f}%')
rep('REE Prevista vs Real (5-min)', [(S['Real'][t],S['Prevista'][t]) for t in ts])
rep('REE Prevista vs Real (hourly means)', [(R[k],P[k]) for k in R if k in P])
rep('REE Programada vs Real (hourly means)', [(R[k],G[k]) for k in R if k in G])
# persistence 1h on 5-min: lag 12
rt=sorted(S['Real']); vals=[S['Real'][t] for t in rt]
rep('Persistence 1h ahead (5-min data, lag 12)', [(vals[i],vals[i-12]) for i in range(12,len(vals))])
hk=sorted(R); hv=[R[k] for k in hk]
rep('Persistence 1h ahead (hourly means)', [(hv[i],hv[i-1]) for i in range(1,len(hv))])
rep('Seasonal naive 24h (hourly means)', [(hv[i],hv[i-24]) for i in range(24,len(hv))])
print('mean real MW', sum(vals)/len(vals))
