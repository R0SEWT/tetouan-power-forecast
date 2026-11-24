import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/tmp/claude-1000/-home-cip-exodia-Code-exprimental/6eb617d0-39a3-45e8-8eeb-156768150d8d/scratchpad/scripts")
from load849 import load
df = load(sys.argv[1])
def den_of(vals, maxd=5000):
    for d_ in range(1, maxd):
        x = vals * d_
        if np.all(np.abs(x - np.round(x)) < 0.02):
            return d_
    return None
out = []
for dte, g in df.groupby("date"):
    out.append((dte, den_of(g.Z1.values[:30]), den_of(g.Z2.values[:30]), den_of(g.Z3.values[:30]),
                den_of(g.Z1.values[-30:]), den_of(g.Z2.values[-30:]), den_of(g.Z3.values[-30:])))
den = pd.DataFrame(out, columns=["date", "d1", "d2", "d3", "d1e", "d2e", "d3e"])
den["date"] = pd.to_datetime(den.date)
for c in ["d1", "d2", "d3"]:
    ch = den[den[c].ne(den[c].shift())]
    print(c, "distinct:", den[c].nunique(), "values:", sorted(den[c].dropna().unique().tolist())[:30])
    print("   change points:", [(r.date.strftime("%m-%d"), getattr(r, c)) for r in ch.itertuples()][:60])
    print("   start-vs-end same within day:", (den[c] == den[c + "e"]).mean())
# numerator granularity
df = df.merge(den[["date", "d1", "d2", "d3"]].assign(date=lambda x: x.date.dt.date), on="date")
for c, dc in [("Z1", "d1"), ("Z2", "d2"), ("Z3", "d3")]:
    num = np.round(df[c] * df[dc]).astype(np.int64)
    print(c, "gcd numerators:", np.gcd.reduce(num.values), "num examples", num.values[:6].tolist(), "num mod 100==0 share", (num % 100 == 0).mean().round(3), "num mod 10==0 share", (num % 10 == 0).mean().round(3))
    # implied raw value: num / some constant ; show monthly table of denominators
print(den.groupby(den.date.dt.month)[["d1", "d2", "d3"]].agg(lambda s: s.mode().iloc[0] if s.notna().any() else None).to_string())
