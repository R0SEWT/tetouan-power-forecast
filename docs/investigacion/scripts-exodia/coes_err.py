import json, sys, os, glob
import statistics as st
base = sys.argv[1]
for year in sys.argv[2:]:
    rows = []
    for f in sorted(glob.glob(os.path.join(base, year + '??', 'r.json'))):
        rows += json.load(open(f))['Data']
    # dedupe by timestamp
    seen = {}
    for r in rows: seen[r['Fecha']] = r
    keys = sorted(seen)
    y  = [seen[k]['ValorEjecutado'] for k in keys]
    pd = [seen[k]['ValorProgramacionDiaria'] for k in keys]
    pw = [seen[k]['ValorProgramacionSemanal'] for k in keys]
    n = len(y)
    def met(pred, lag=None, name=''):
        e=[]; a=[]; yy=[]
        for i in range(n):
            if lag is not None:
                if i - lag < 0: continue
                p = y[i-lag]
            else:
                p = pred[i]
            if y[i] is None or p is None or y[i] <= 0: continue
            e.append(abs(y[i]-p)/y[i]); a.append(abs(y[i]-p)); yy.append(y[i])
        mae = sum(a)/len(a); 
        print(f"  {name:42s} N={len(e):6d} MAPE={100*sum(e)/len(e):5.2f}%  MAE={mae:7.1f} MW  nMAE={100*mae/(sum(yy)/len(yy)):5.2f}%")
    yv=[v for v in y if v]
    print(f"{year}: n={n} first={keys[0]} last={keys[-1]} mean={sum(yv)/len(yv):.0f} MW min={min(yv):.0f} max={max(yv):.0f}")
    met(pd, name='COES Programa Diario (day-ahead)')
    met(pw, name='COES Programa Semanal (week-ahead)')
    met(None, lag=1, name='Persistence 30 min ahead (y[t-1])')
    met(None, lag=2, name='Persistence 1 h ahead (y[t-2])')
    met(None, lag=48, name='Seasonal naive 24 h (y[t-48])')
    met(None, lag=336, name='Seasonal naive 7 d (y[t-336])')
