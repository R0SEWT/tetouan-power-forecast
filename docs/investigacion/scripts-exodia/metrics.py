import sys, os
import numpy as np, pandas as pd
S = sys.argv[1]
df = pd.read_csv(os.path.join(S, 'coes', 'coes_sein_demanda_30min_2022_2026.csv'), parse_dates=['fecha_fin_intervalo'], index_col=0)
y = df['ejecutado_mw']
fc = {
 'COES Prog. Diaria (PDO, day-ahead)': df['prog_diaria_mw'],
 'COES Prog. Semanal (PSO, week-ahead)': df['prog_semanal_mw'],
 'Persistence t+1 (30 min)': y.shift(1),
 'Persistence t+2 (1 h)': y.shift(2),
 'Seasonal naive 1 day (t-48)': y.shift(48),
 'Seasonal naive 2 days (t-96)': y.shift(96),
 'Seasonal naive 1 week (t-336)': y.shift(336),
}
def m(yt, yp):
    k = yt.notna() & yp.notna(); yt, yp = yt[k], yp[k]; e = yp - yt
    return dict(n=int(k.sum()), MAE_MW=e.abs().mean(), RMSE_MW=np.sqrt((e**2).mean()),
                MAPE_pct=100*(e.abs()/yt).mean(), WAPE_pct=100*e.abs().sum()/yt.sum(),
                bias_MW=e.mean(), bias_pct=100*e.mean()/yt.mean(), mean_load_MW=yt.mean())
periods = {'2022': ('2022-01-01 00:30','2023-01-01 00:00'), '2023': ('2023-01-01 00:30','2024-01-01 00:00'),
           '2024': ('2024-01-01 00:30','2025-01-01 00:00'), '2025': ('2025-01-01 00:30','2026-01-01 00:00'),
           '2026 (to 21-Nov)': ('2026-01-01 00:30','2026-11-22 00:00'),
           '2025 Nov-Dec (Tetouan test-like window)': ('2025-11-01 00:30','2026-01-01 00:00'),
           'All 2022-01..2026-11': (None, None)}
out = []
for p,(a,b) in periods.items():
    sl = slice(a,b)
    for name, f in fc.items():
        r = m(y.loc[sl], f.loc[sl]); r.update(period=p, forecast=name); out.append(r)
res = pd.DataFrame(out)[['period','forecast','n','mean_load_MW','MAE_MW','RMSE_MW','MAPE_pct','WAPE_pct','bias_MW','bias_pct']]
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
print(res.round(2).to_string(index=False))
res.round(4).to_csv(os.path.join(S,'coes','coes_baseline_metrics.csv'), index=False)
# 2025 detail: by hour of day and by month for PDO and persistence 1h
s25 = slice('2025-01-01 00:30','2026-01-01 00:00')
d = df.loc[s25].copy(); d['y']=y.loc[s25]
d['e_pdo']=(df['prog_diaria_mw']-y).loc[s25]; d['e_p1h']=(y.shift(2)-y).loc[s25]; d['e_w']=(y.shift(336)-y).loc[s25]
d['month']=d.index.month; d['hour']=(d.index - pd.Timedelta('30min')).hour
for g in ['month','hour']:
    t = d.groupby(g).apply(lambda x: pd.Series({'MAPE_PDO':100*(x.e_pdo.abs()/x.y).mean(),'MAPE_pers1h':100*(x.e_p1h.abs()/x.y).mean(),'MAPE_week':100*(x.e_w.abs()/x.y).mean(),'bias_PDO_MW':x.e_pdo.mean()}))
    print(t.round(2).to_string()); t.round(4).to_csv(os.path.join(S,'coes',f'coes_2025_by_{g}.csv'))
# PSO resolution check
ps = df['prog_semanal_mw']; print('PSO changes at :30 stamps share', (ps.diff()!=0)[df.index.minute==0].mean(), 'at :00', (ps.diff()!=0)[df.index.minute==30].mean())
# daily energy-level errors of PDO 2025 (daily mean)
dd = df.loc[s25].resample('D', label='left', closed='right').mean()
print('2025 daily-mean PDO MAPE', round(100*((dd.prog_diaria_mw-dd.ejecutado_mw).abs()/dd.ejecutado_mw).mean(),3))
# worst PDO days 2025
dd['ape']=100*(dd.prog_diaria_mw-dd.ejecutado_mw).abs()/dd.ejecutado_mw
print(dd.sort_values('ape',ascending=False).head(8).round(1))
print('max ejecutado', y.idxmax(), y.max(), 'min', y.idxmin(), y.min())
