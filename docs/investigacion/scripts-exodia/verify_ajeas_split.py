import sys, numpy as np, pandas as pd
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
df = pd.read_csv(sys.argv[1]); df.columns=[c.strip() for c in df.columns]
dt = pd.to_datetime(df['DateTime']); y_col=[c for c in df.columns if 'Zone 1' in c or 'Zone1' in c][0]
W=['Temperature','Humidity','Wind Speed','general diffuse flows','diffuse flows']
df['hour']=dt.dt.hour+dt.dt.minute/60; df['doy']=dt.dt.dayofyear; df['month']=dt.dt.month; df['dow']=dt.dt.dayofweek
lo,hi=df[y_col].quantile([.01,.99]); d=df[(df[y_col]>=lo)&(df[y_col]<=hi)]
for name,F in [('weather',W),('weather+cal',W+['hour','doy','month','dow'])]:
  X=StandardScaler().fit_transform(d[F]); y=d[y_col].values
  for sh in [True,False]:
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,shuffle=sh,random_state=42)
    p=KNeighborsRegressor(5,p=1,weights='distance').fit(Xtr,ytr).predict(Xte)
    print(name,'shuffle' if sh else 'chrono', round(r2_score(yte,p),4), round(mean_squared_error(yte,p)**.5,1), round(mean_absolute_error(yte,p),1))
