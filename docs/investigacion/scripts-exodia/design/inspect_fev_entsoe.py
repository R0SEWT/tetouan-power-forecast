import sys, pandas as pd, numpy as np
df = pd.read_parquet(sys.argv[1])
print(df.columns.tolist())
for _, r in df.iterrows():
    ts = r['timestamp']; y = np.asarray(r['target'], float)
    print(r['id'], ts[0], ts[-1], len(y), 'mean', np.nanmean(y).round(0))
