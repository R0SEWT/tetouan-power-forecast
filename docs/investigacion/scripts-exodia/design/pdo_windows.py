import sys, pandas as pd, numpy as np
df = pd.read_csv(sys.argv[1], parse_dates=["t"]).set_index("t").sort_index()
df.columns = ["ej", "pdo", "pso"]
full = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="30min"))
print("rows", len(df), "missing slots", int(full["ej"].isna().sum()), "dup", int(df.index.duplicated().sum()))
y = full["ej"]
refs = {"PDO": full["pdo"], "PSO": full["pso"], "persist_1h(t-2)": y.shift(2), "naive24h(t-48)": y.shift(48),
        "naive7d(t-336)": y.shift(336)}
wins = {"val2025": ("2025-01-01 00:30", "2026-01-01 00:00"), "test2026_to_10-17": ("2026-01-01 00:30", "2026-10-18 00:00"),
        "2017": ("2017-01-01 00:30", "2018-01-01 00:00")}
for w, (a, b) in wins.items():
    s = slice(a, b)
    for k, r in refs.items():
        e = (r[s] - y[s]).dropna(); yy = y[s].loc[e.index]
        print(f"{w:20s} {k:16s} n={len(e):6d} MAE={e.abs().mean():7.1f} MW  MAPE={100*(e.abs()/yy).mean():5.2f}%  bias={e.mean():+6.1f}")
