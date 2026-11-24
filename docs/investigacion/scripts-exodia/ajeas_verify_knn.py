import sys, numpy as np, pandas as pd
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
df = pd.read_csv(sys.argv[1]); df.columns=[c.strip() for c in df.columns]
dt = pd.to_datetime(df['DateTime'])
w = ['Temperature','Humidity','Wind Speed','general diffuse flows','diffuse flows']
y = 'Zone 1 Power Consumption'
lo,hi = df[y].quantile([.01,.99]); m=(df[y]>=lo)&(df[y]<=hi); d=df[m].copy(); t=dt[m]
d['hour']=t.dt.hour+t.dt.minute/60; d['doy']=t.dt.dayofyear; d['month']=t.dt.month; d['dow']=t.dt.dayofweek
sets={'weather':w,'weather+cal':w+['hour','doy','month','dow'],'weather+otherzones':w+['Zone 2  Power Consumption','Zone 3  Power Consumption']}
for name,f in sets.items():
  missing=[c for c in f if c not in d.columns]
  if missing: print(name,'missing',missing, list(d.columns)); continue
  X=StandardScaler().fit_transform(d[f]); Y=d[y].values
  for sh in [True,False]:
    Xtr,Xte,ytr,yte=train_test_split(X,Y,test_size=.2,shuffle=sh,random_state=42)
    p=KNeighborsRegressor(5,p=1,weights='distance').fit(Xtr,ytr).predict(Xte)
    print(name,'shuffle' if sh else 'chrono', 'R2=%.4f RMSE=%.0f MAE=%.0f'%(r2_score(yte,p),mean_squared_error(yte,p)**.5,mean_absolute_error(yte,p)))
