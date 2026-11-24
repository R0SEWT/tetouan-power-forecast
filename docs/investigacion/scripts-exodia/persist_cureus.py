import sys,numpy as np,pandas as pd
df=pd.read_csv(sys.argv[1]); df.columns=[c.strip() for c in df.columns]
df['DateTime']=pd.to_datetime(df['DateTime']); df=df.sort_values('DateTime').reset_index(drop=True)
z=[c for c in df.columns if 'Zone' in c]
# replicate paper: drop first 1008 rows (warm-up), 80/20 split -> test rows idx>=split
df=df.iloc[1008:].reset_index(drop=True); N=len(df); s=int(N*0.8)
print('N',N,'split',s,'test',N-s)
for c in z:
    y=df[c].values
    for h in (1,6):
        yt=y[s:]; yp=y[s-h:N-h]
        rmse=np.sqrt(np.mean((yt-yp)**2)); mae=np.mean(np.abs(yt-yp)); mape=np.mean(np.abs((yt-yp)/yt))*100
        r2=1-np.sum((yt-yp)**2)/np.sum((yt-yt.mean())**2)
        print(f'{c} persistence h={h}: RMSE {rmse:.2f} MAE {mae:.2f} MAPE {mape:.2f}% R2 {r2:.4f}')
    # seasonal naive day
    yt=y[s:]; yp=y[s-144:N-144]
    rmse=np.sqrt(np.mean((yt-yp)**2)); r2=1-np.sum((yt-yp)**2)/np.sum((yt-yt.mean())**2)
    print(f'{c} seasonal-naive 24h: RMSE {rmse:.2f} R2 {r2:.4f}')
