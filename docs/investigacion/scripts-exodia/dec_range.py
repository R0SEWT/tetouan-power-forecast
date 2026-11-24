import sys, pandas as pd
df=pd.read_csv(sys.argv[1]); df['DateTime']=pd.to_datetime(df['DateTime'])
z=[c for c in df.columns if 'Zone' in c]; df['Total']=df[z].sum(axis=1)
dec=df[df.DateTime.dt.month==12]
print(dec[z+['Total']].agg(['min','max']))
print('daily mean total max', df.set_index('DateTime')['Total'].resample('D').mean().max())
