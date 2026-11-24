import sys, json, pandas as pd, numpy as np
df = pd.read_csv(sys.argv[1], parse_dates=['t'], index_col='t')
df.columns = ['E','PDO','PSO']
full = pd.date_range(df.index.min(), df.index.max(), freq='30min')
df = df.reindex(full)
E = df['E']
# naive baselines on the executed series
df['pers1h'] = E.shift(2)        # 1 hour ahead persistence (2 x 30 min)
df['pers30'] = E.shift(1)
df['snaive_d'] = E.shift(48)     # same half-hour previous day
df['snaive_w'] = E.shift(336)    # same half-hour previous week
def m(y, yh):
    ok = y.notna() & yh.notna() & (y > 0)
    y, yh = y[ok], yh[ok]
    e = yh - y
    return dict(n=int(ok.sum()), MAPE=round(float((e.abs()/y).mean()*100),3), MAE=round(float(e.abs().mean()),1),
                RMSE=round(float(np.sqrt((e**2).mean())),1), bias=round(float(e.mean()),1), meanE=round(float(y.mean()),1))
out = {}
for yr, g in df.groupby(df.index.year):
    out[yr] = {k: m(g['E'], g[k]) for k in ['PDO','PSO','pers30','pers1h','snaive_d','snaive_w']}
res = pd.DataFrame({(yr,k): v for yr, d in out.items() for k, v in d.items()}).T
pd.set_option('display.width', 200); pd.set_option('display.max_rows', 200)
print(res)
# Nov-Dec 2017 to mirror Tetouan test months
g = df.loc['2017-11-01':'2017-12-31']
print('Nov-Dec 2017:', {k: m(g['E'], g[k]) for k in ['PDO','PSO','pers1h','snaive_d','snaive_w']})
g = df.loc['2023-01-01':'2025-12-31']
print('2023-2025:', {k: m(g['E'], g[k]) for k in ['PDO','PSO','pers1h','snaive_d','snaive_w']})
# PDO MAPE by hour of day for 2025
g = df.loc['2025']; ape = ((g['PDO']-g['E']).abs()/g['E']*100)
print('2025 PDO MAPE by hour:', ape.groupby(g.index.hour).mean().round(2).to_dict())
# daily-MAPE distribution 2025
dm = ape.groupby(g.index.date).mean()
print('2025 daily MAPE pct: p50 %.2f p90 %.2f p99 %.2f max %.2f' % tuple(np.percentile(dm.dropna(), [50,90,99,100])))
