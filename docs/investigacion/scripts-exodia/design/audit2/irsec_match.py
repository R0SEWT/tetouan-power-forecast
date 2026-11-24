import sys, pandas as pd, numpy as np
p=sys.argv[1]
df=pd.read_csv(p); df.columns=[c.strip() for c in df.columns]
df['dt']=pd.to_datetime(df['DateTime'],format='%m/%d/%Y %H:%M')
cols={'Temperature':'T','Humidity':'H','Wind Speed':'W','general diffuse flows':'GDF','diffuse flows':'DF','Zone 1 Power Consumption':'Z1','Zone 2  Power Consumption':'Z2','Zone 3  Power Consumption':'Z3'}
df=df.rename(columns=cols)
print('rows',len(df))
d=df[list(cols.values())].describe().T[['count','mean','std','min','max']]
print(d.round(4).to_string())
print('corr with Z1:'); print(df[list(cols.values())].corr()['Z1'].round(6).to_string())
m=df.set_index('dt')[['Z1','Z2','Z3']].resample('MS').mean().round(0); print(m.to_string())
# April block check, late Oct transfer
for a,b in [('2017-03-20','2017-03-31'),('2017-04-03','2017-04-28'),('2017-05-05','2017-05-20'),('2017-10-15','2017-10-23'),('2017-10-27','2017-11-05')]:
    s=df[(df.dt>=a)&(df.dt<b)][['Z1','Z2','Z3']]; print(a,b,'mean',s.mean().round(0).to_dict(),'min',s.min().round(0).to_dict())
h=df.set_index('dt')[['Z1','Z2','Z3']].resample('h')
print('hourly sum stats:'); print(h.sum().describe().round(1).to_string())
print('hourly mean stats:'); print(h.mean().describe().round(1).to_string())
