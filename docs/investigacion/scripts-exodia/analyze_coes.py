import json, glob, sys
import pandas as pd, numpy as np
d = sys.argv[1]
rows = []
for f in sorted(glob.glob(d + '/d_*.json')):
    try: j = json.load(open(f, encoding='utf-8-sig'))
    except Exception: continue
    ser = {s['Name']: {p['Nombre']: p['Valor'] for p in s['Data']} for s in j['Chart']['Series']}
    names = list(ser)
    idx = sorted(set().union(*[set(v) for v in ser.values()]))
    for t in idx:
        rows.append({'t': t, **{n: ser[n].get(t) for n in names}})
df = pd.DataFrame(rows)
df['t'] = pd.to_datetime(df['t'], format='%Y/%m/%d %H:%M:%S')
df = df.drop_duplicates('t').set_index('t').sort_index()
print('series names:', list(df.columns)); print(df.index.min(), df.index.max(), len(df))
# also check Data table field names
j = json.load(open(sorted(glob.glob(d + '/d_*.json'))[0], encoding='utf-8-sig'))
print('Data keys:', list(j['Data'][0].keys()), j['Data'][0])
df.to_csv(sys.argv[2])
