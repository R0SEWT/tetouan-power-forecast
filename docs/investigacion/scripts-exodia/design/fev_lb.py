import sys, glob, os
import pandas as pd, numpy as np
root=sys.argv[1]
dfs=[pd.read_csv(f) for f in glob.glob(os.path.join(root,'*.csv'))]
A=pd.concat(dfs,ignore_index=True)
try:
    import fev
    for metric in ['SQL','MASE']:
        lb=fev.leaderboard(A, metric_column=metric, baseline_model='Seasonal Naive' if 'Seasonal Naive' in set(A.model_name) else None)
        print('== fev.leaderboard', metric); print(lb.head(25).to_string())
except Exception as e:
    print('fev failed:', repr(e)[:500])
print(sorted(A.model_name.unique()))
# leakage flags
lk=A.groupby('model_name').trained_on_this_dataset.apply(lambda s: s.astype(str).str.lower().eq('true').sum())
print('tasks flagged trained_on_this_dataset:', lk[lk>0].to_dict())
# energy tasks for some models
E=A[A.task_name.str.contains('entsoe|ercot|proenfo|epf|solar',regex=True)]
piv=E.pivot_table(index='task_name',columns='model_name',values='MASE')
cols=[c for c in piv.columns if any(k in c for k in ['Seasonal','Chronos-2','TabPFN-TS-3','TiRex-2','TimesFM-2.5','TimesFM-3','Sundial','Simons-297','Timestral-209','TimeH2O-v1','ChakraTS','PDM-Nano'])]
pd.set_option('display.width',300)
print(piv[cols].round(3).to_string())
print('=== own leaderboard (models with all 100 tasks)')
for metric in ['SQL','MASE']:
    P=A.pivot_table(index='task_name',columns='model_name',values=metric)
    P=P.dropna(axis=1)
    base=P['Seasonal Naive']
    rel=P.div(base,axis=0).clip(lower=1e-2,upper=100)
    skill=1-np.exp(np.log(rel).mean())
    # win rate: fraction of (task, other model) pairs beaten, ties=0.5
    W={}
    for m in P.columns:
        o=P.drop(columns=m)
        W[m]=((o.values>P[[m]].values).sum()+0.5*(o.values==P[[m]].values).sum())/o.size
    R=pd.DataFrame({'skill':skill,'winrate':pd.Series(W)}).sort_values('winrate',ascending=False)
    print('--',metric); print(R.head(20).round(3).to_string())
    for m in ['TabPFN-TS-3','TiRex-2','TimesFM-2.5','timesfm-3','Sundial-Base','Chronos-2','Simons-297M','Toto-2.0-313m','Toto-2.0-2.5B','t0-gamma','Timestral-209M','timeh2o-v1','ChakraTS','PDM-Nano','chakrats-os-10m']:
        if m in R.index: print(m, list(R.index).index(m)+1, R.loc[m].round(3).to_dict())
lk=A[A.trained_on_this_dataset.astype(str).str.lower()=='true'].groupby('model_name').task_name.apply(list)
print(lk.to_dict())
print(A[A.model_name.isin(['TabPFN-TS-3','TiRex-2','timesfm-3','timeh2o-v1','ChakraTS','PDM-Nano','Timestral-209M','Simons-297M'])].groupby('model_name').agg(v=('fev_version','first'),kw=('model_kwargs','first')).to_string())
