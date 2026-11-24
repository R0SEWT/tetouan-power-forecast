import sys, pandas as pd, numpy as np
df=pd.read_csv(sys.argv[1]); df.columns=[c.strip() for c in df.columns]
df['dt']=pd.to_datetime(df['DateTime'],format='%m/%d/%Y %H:%M')
h=df.set_index('dt')[['Zone 1 Power Consumption','Zone 2  Power Consumption','Zone 3  Power Consumption']].resample('h').sum()
h.columns=['Z1','Z2','Z3']; h['AGG']=h.sum(axis=1)
for start in ['2017-10-01 18:00','2017-10-03 17:00']:
    w=h.loc[start:].iloc[:500]
    print(start,'->',w.index[-1]); print(w.describe().loc[['mean','min','max']].round(0).to_string())
    print('pct of hours with value>150k:', (w[['Z2','Z3']]>150000).mean().round(3).to_dict())
