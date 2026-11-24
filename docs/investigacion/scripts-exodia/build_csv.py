import json, glob, sys, os
import pandas as pd
S = sys.argv[1]
rows = []
for f in sorted(glob.glob(os.path.join(S, 'downloads', 'coes_dem_*', 'data.json'))):
    d = json.load(open(f))
    for r in d['Data']:
        rows.append((r['Fecha'], r['ValorEjecutado'], r['ValorProgramacionDiaria'], r['ValorProgramacionSemanal'], os.path.basename(os.path.dirname(f))))
df = pd.DataFrame(rows, columns=['fecha', 'ejecutado_mw', 'prog_diaria_mw', 'prog_semanal_mw', 'src'])
df['fecha'] = pd.to_datetime(df['fecha'], format='%Y/%m/%d %H:%M')
print('raw rows', len(df), 'dups', df.duplicated('fecha').sum())
# check duplicated stamps agree
dd = df[df.duplicated('fecha', keep=False)].sort_values('fecha')
g = dd.groupby('fecha')[['ejecutado_mw','prog_diaria_mw','prog_semanal_mw']].agg(lambda s: s.max()-s.min() if s.notna().all() else -1)
print('max disagreement among dup stamps', g.max().to_dict())
df = df.drop_duplicates('fecha', keep='first').sort_values('fecha').drop(columns='src').set_index('fecha')
full = pd.date_range(df.index.min(), df.index.max(), freq='30min')
print('expected', len(full), 'have', len(df), 'missing stamps', len(full.difference(df.index)))
df = df.reindex(full); df.index.name = 'fecha_fin_intervalo'
print(df.describe().T)
for c in df.columns:
    print(c, 'nulls', df[c].isna().sum(), 'zeros', (df[c] == 0).sum(), '<3000', (df[c] < 3000).sum())
out = os.path.join(S, 'coes', 'coes_sein_demanda_30min_2022_2026.csv')
df.to_csv(out, float_format='%.5f')
print('saved', out)
