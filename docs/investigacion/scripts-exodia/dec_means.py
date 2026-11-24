import sys, pandas as pd
df = pd.read_csv(sys.argv[1]); df['DateTime']=pd.to_datetime(df['DateTime'])
z=[c for c in df.columns if 'Zone' in c]; print(z, len(df))
df['Total']=df[z].sum(axis=1)
dec=df[df.DateTime.dt.month==12]; print('Dec rows',len(dec))
print(dec[z+['Total']].mean()); print(df[z+['Total']].mean())
for c in z+['Total']:
    y=dec[c].values; yp=y[:-1]; yt=y[1:]
    import numpy as np
    print(c,'persist t+1 RMSE',np.sqrt(np.mean((yt-yp)**2)),'MAE',np.mean(abs(yt-yp)),'MAPE',100*np.mean(abs(yt-yp)/yt))
