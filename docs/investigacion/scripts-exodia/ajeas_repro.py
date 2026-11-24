import sys, numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
df=pd.read_csv(sys.argv[1]); df.columns=[c.strip() for c in df.columns]
df['DateTime']=pd.to_datetime(df['DateTime'])
W=['Temperature','Humidity','Wind Speed','general diffuse flows','diffuse flows']
y='Zone 1 Power Consumption'
# percentile 1-99 outlier removal on target
lo,hi=df[y].quantile([.01,.99]); d=df[(df[y]>=lo)&(df[y]<=hi)].copy()
d['ts']=d['DateTime'].astype('int64')//10**9
d['hour']=d.DateTime.dt.hour+d.DateTime.dt.minute/60; d['doy']=d.DateTime.dt.dayofyear; d['month']=d.DateTime.dt.month; d['dow']=d.DateTime.dt.dayofweek
sets={'weather_only':W,'weather+ts':W+['ts'],'weather+hour/doy/month/dow':W+['hour','doy','month','dow'],'weather+zone2+zone3':W+['Zone 2  Power Consumption','Zone 3  Power Consumption']}
for shuffle in [True,False]:
  for k,f in sets.items():
    X=d[f].values; Y=d[y].values
    Xtr,Xte,ytr,yte=train_test_split(X,Y,test_size=0.2,shuffle=shuffle,random_state=42)
    sc=StandardScaler().fit(Xtr)
    m=KNeighborsRegressor(n_neighbors=5,p=1,weights='distance').fit(sc.transform(Xtr),ytr)
    p=m.predict(sc.transform(Xte))
    print(f"shuffle={shuffle} {k}: R2={r2_score(yte,p):.4f} RMSE={mean_squared_error(yte,p)**.5:.1f} MAE={mean_absolute_error(yte,p):.1f}")
