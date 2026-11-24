import sys, pandas as pd
df = pd.read_csv(sys.argv[1])
df['DateTime'] = pd.to_datetime(df['DateTime'])
z = [c for c in df.columns if 'Zone' in c]
m = df.groupby(df.DateTime.dt.month)[z].mean().round(0)
print(m.to_string())
print('Aug/Jan ratio:', (m.loc[8]/m.loc[1]).round(3).to_dict())
print('Jul/Jan ratio:', (m.loc[7]/m.loc[1]).round(3).to_dict())
print('annual mean:', df[z].mean().round(1).to_dict())
# energy per 10 min if kW: kWh = kW/6 ; annual MWh
print('annual MWh if kW avg:', (df[z].mean()*8760/1000).round(0).to_dict())
