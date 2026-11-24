import sys, numpy as np, pandas as pd
df = pd.read_csv(sys.argv[1], parse_dates=[0], index_col=0)
y, p = df.ejecutado_mw, df.prog_diaria_mw
c = {'Persistence 1h y(t-2)': y.shift(2),
     'Persistence + PDO delta: y(t-2)+PDO(t)-PDO(t-2)': y.shift(2) + p - p.shift(2),
     'Persistence + weekly delta: y(t-2)+y(t-336)-y(t-338)': y.shift(2) + y.shift(336) - y.shift(338),
     'PDO bias-corrected with last obs: PDO(t)+[y(t-2)-PDO(t-2)]': p + (y.shift(2) - p.shift(2)),
     'PDO raw': p}
rows=[]
for per,(a,b) in {'2025':('2025-01-01 00:30','2026-01-01 00:00'),'2025 Nov-Dec':('2025-11-01 00:30','2026-01-01 00:00')}.items():
    for k,f in c.items():
        yt, yp = y.loc[a:b], f.loc[a:b]; e = yp-yt
        rows.append(dict(period=per, forecast=k, MAE_MW=e.abs().mean(), RMSE_MW=np.sqrt((e**2).mean()), MAPE_pct=100*(e.abs()/yt).mean(), median_APE_pct=100*(e.abs()/yt).median(), bias_MW=e.mean()))
r = pd.DataFrame(rows); print(r.round(2).to_string(index=False)); r.round(4).to_csv(sys.argv[2], index=False)
