import sys, pandas as pd, numpy as np
df=pd.read_csv(sys.argv[1]); df['DateTime']=pd.to_datetime(df['DateTime'])
z=[c for c in df.columns if 'Zone 1' in c][0]
h=df.set_index('DateTime')[z].resample('h').mean().values
print('hours',len(h))
# sequences: window t-23..t, target t+1
idx=np.arange(23,len(h)-1); y=h[idx+1]; p=h[idx]; n=len(idx); print('seqs',n)
for name,start in [('70/15/15 test',int(n*0.85)),('80/20',int(n*0.8))]:
  yt,pt=y[start:],p[start:]
  e=yt-pt; mae=np.abs(e).mean(); rmse=np.sqrt((e**2).mean()); mape=np.mean(np.abs(e/yt))*100; r2=1-(e**2).sum()/((yt-yt.mean())**2).sum()
  print(name,len(yt),round(mae,2),round(rmse,2),round(mape,3),round(r2,4))
  # seasonal naive 24h
  ps=h[idx+1-24][start:]; e=yt-ps
  print(' snaive24',round(np.abs(e).mean(),2),round(np.sqrt((e**2).mean()),2),round(np.mean(np.abs(e/yt))*100,3),round(1-(e**2).sum()/((yt-yt.mean())**2).sum(),4))
