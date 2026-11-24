# Simplified replica of COES PR-03 Anexo A (ordinary days) on total SEIN demand.
# Simplifications: no vegetative/industrial split (no agent data), no holiday handling, uses days <= D-2.
import sys, pandas as pd, numpy as np
df = pd.read_csv(sys.argv[1], parse_dates=['t'], index_col='t'); df.columns = ['E','PDO','PSO']
# interval-ending timestamps -> shift to interval start so 00:30 stamp belongs to 00:00-00:30 of the same day
df.index = df.index - pd.Timedelta('30min')
df = df[~df.index.duplicated()]
df['day'] = df.index.normalize(); df['slot'] = df.index.hour*2 + df.index.minute//30
E = df.pivot_table(index='day', columns='slot', values='E')
E = E[E.notna().sum(axis=1) == 48]
days = E.index
def dtype(d):
    w = d.weekday(); return {5:'sat',6:'sun',0:'mon'}.get(w,'tue-fri')
types = pd.Series([dtype(d) for d in days], index=days)
slots = np.arange(48); base = slots < 16; media = (slots >= 16) & (slots < 36); punta = slots >= 36
def pr03(D):
    cand = [d for d in days if d <= D - pd.Timedelta('2D') and types[d] == dtype(D)]
    if len(cand) < 5: return None
    sel = cand[-5:]; M = E.loc[sel].values.copy()  # 5 x 48
    med = np.median(M, axis=0)
    ok = np.abs(M - med)/med < 0.05
    for j in range(48):
        if (~ok[:, j]).any():
            v = M[ok[:, j], j]; M[~ok[:, j], j] = v.mean() if len(v) else med[j]
    mn = M[:, base].min(1); mxm = M[:, media].max(1); mxp = M[:, punta].max(1)
    ref = np.where(base, mn[:, None], np.where(media, mxm[:, None], mxp[:, None]))
    pu = np.median(M/ref, axis=0)
    pu = np.where(base, pu/pu[base].min(), np.where(media, pu/pu[media].max(), pu/pu[punta].max()))
    x = np.arange(5)
    f = lambda y: np.polyval(np.polyfit(x, y, 1), 5)
    return pu*np.where(base, f(mn), np.where(media, f(mxm), f(mxp)))
rows = []
for D in days:
    if D.year < 2017: continue
    p = pr03(D)
    if p is None: continue
    rows.append(pd.DataFrame({'t': [D + pd.Timedelta(minutes=30*s) for s in slots], 'rep': p}))
R = pd.concat(rows).set_index('t')
J = df.join(R, how='inner')
def mape(a, b):
    ok = a.notna() & b.notna(); return float(((a[ok]-b[ok]).abs()/a[ok]).mean()*100)
out = []
for yr, g in J.groupby(J.index.year):
    out.append((yr, round(mape(g.E, g.rep),3), round(mape(g.E, g.PDO),3), len(g)))
print('year, MAPE PR03-replica (no industrial split, no holiday rule), MAPE COES PDO, n')
for o in out: print(o)
g = J.loc['2023':'2025']; print('2023-2025', round(mape(g.E,g.rep),3), round(mape(g.E,g.PDO),3))
g = J.loc['2017-11':'2017-12']; print('Nov-Dec 2017', round(mape(g.E,g.rep),3), round(mape(g.E,g.PDO),3))
