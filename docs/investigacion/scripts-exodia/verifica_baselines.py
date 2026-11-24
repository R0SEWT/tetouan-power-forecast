import sys,glob,pandas as pd,numpy as np
f=[p for p in glob.glob(sys.argv[1]+'/*') if p.lower().endswith('.csv')][0]
d=pd.read_csv(f); d.columns=[c.strip() for c in d.columns]
z=[c for c in d.columns if 'Zone 1' in c][0]; y=d[z].values.astype(float)
n=len(y); idx=np.arange(144,n-6)
tgt=y[idx+6]; pers=y[idx]; dd=y[idx]+(y[idx-138]-y[idx-144])
# split 70/15/15 on usable rows
m=len(idx); te=slice(int(m*.85),m)
for nm,p in [('pers',pers),('delta',dd)]:
  e=np.abs(tgt-p); print(nm,'MAE all %.0f test %.0f MAPE test %.2f%%'%(e.mean(),e[te].mean(),100*(e[te]/tgt[te]).mean()))
