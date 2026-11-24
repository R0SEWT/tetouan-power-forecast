import sys, pandas as pd, numpy as np
df = pd.read_csv(sys.argv[1])
df['DateTime'] = pd.to_datetime(df['DateTime'])
z = df.set_index('DateTime')['Zone 1 Power Consumption'].resample('h').mean()
n = len(z); y = z.values
# target y[t+1]; samples after 24-step window; approximate split 70/10/20 on hourly series
te0 = int(0.8*n)
yt = y[te0:]; prev = y[te0-1:-1]; prev24 = y[te0-24:-24]
def m(p, a):
    e = p-a; rmse=np.sqrt(np.mean(e**2)); mae=np.mean(abs(e)); mape=100*np.mean(abs(e)/a)
    r2=1-np.sum(e**2)/np.sum((a-a.mean())**2); return dict(RMSE=round(rmse,1),MAE=round(mae,1),MAPE=round(mape,2),R2=round(r2,4),CVRMSE=round(100*rmse/a.mean(),2))
print('n hourly', n, 'test from', z.index[te0], 'test mean', round(yt.mean(),1))
print('persistence t-1h ->t:', m(prev, yt))
print('seasonal naive t-24h:', m(prev24, yt))
