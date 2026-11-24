import sys, pandas as pd, numpy as np
df=pd.read_csv(sys.argv[1]); df.columns=[c.strip() for c in df.columns]
df['dt']=pd.to_datetime(df['DateTime'],format='%m/%d/%Y %H:%M')
z=df['Zone 1 Power Consumption'].values; agg=(df['Zone 1 Power Consumption']+df['Zone 2  Power Consumption']+df['Zone 3  Power Consumption']).values
# anchors digitized by eye from IRSEC Fig 5 (left, REAL): (index, value, kind)
anc=[(0,47.3,'max'),(70,26.5,'min'),(150,47.2,'max'),(215,26.0,'min'),(290,45.0,'max'),(360,25.0,'min'),(435,46.3,'max'),(500,24.5,'min'),(580,46.3,'max'),(650,22.5,'min'),(725,45.9,'max'),(790,25.0,'min'),(870,47.0,'max'),(940,26.0,'min'),(1010,47.2,'max'),(1080,26.0,'min'),(1150,47.5,'max'),(1230,26.0,'min'),(1300,47.6,'max'),(1370,25.5,'min'),(1440,45.5,'max'),(1520,25.0,'min')]
def score(s,series):
    e=[]
    for i,v,k in anc:
        a,b=s+i-15,s+i+15
        if a<0 or b>len(series): return 1e9
        w=series[a:b]/1000; e.append((w.max() if k=='max' else w.min())-v)
    return float(np.sqrt(np.mean(np.square(e))))
sc=np.array([score(s,z) for s in range(0,len(z)-1700)])
best=np.argsort(sc)[:15]
for s in best: print(s, df.dt[s], round(sc[s],3))
s0=39420-144 if False else None
for lab,s in [('75% of 52560 (incl Dec31) ->',39420),('75% of 52416 ->',39312)]:
    s=min(s,len(z)-1)
    print(lab, s, df.dt[s] if s<len(df) else None, 'score', round(score(s,z),3))
mask=np.abs(np.arange(len(sc))-39705)>300
s2=np.argmin(np.where(mask,sc,1e9)); print('best outside window:',s2,df.dt[s2],round(sc[s2],3))
print('quantiles of score:',np.percentile(sc,[0.1,1,5,50]).round(3))
# 75% boundary as fraction for start 39701
print('fraction of 52416 at best start:', round(39701/52416,4), ' of 52560:', round(39701/52560,4))
