import sys,pandas as pd
df=pd.read_csv(sys.argv[1]); df.columns=[c.strip() for c in df.columns]
df['dt']=pd.to_datetime(df['DateTime'],format='%m/%d/%Y %H:%M')
t=df[df.dt>='2017-10-01 18:00']
for c,r,m in [('Zone 1 Power Consumption',3174.7,2663.5),('Zone 2  Power Consumption',3227.8,2475.9),('Zone 3  Power Consumption',2336.9,1939.6)]:
    s=t[c]; print(c,'n',len(s),'mean',round(s.mean(),1),'std',round(s.std(ddof=0),1),'R2 implied',round(1-r**2/s.var(ddof=0),3),'MAPE~',round(100*m/s.mean(),2))
