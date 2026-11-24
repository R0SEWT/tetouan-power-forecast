import sys, json, glob, os
import pandas as pd, numpy as np
root = sys.argv[1]
rows=[]; meta={}
for d in sorted(glob.glob(os.path.join(root,'*'))):
    n=os.path.basename(d)
    try:
        df=pd.read_csv(os.path.join(d,'all_results.csv')); cfg=json.load(open(os.path.join(d,'config.json')))
    except Exception as e:
        continue
    df['m']=n; rows.append(df[['dataset','m','eval_metrics/MASE[0.5]','eval_metrics/mean_weighted_sum_quantile_loss']]); meta[n]=cfg
A=pd.concat(rows); A.columns=['ds','m','mase','crps']
A=A.drop_duplicates(['ds','m'])
cnt=A.groupby('m').ds.nunique(); full=cnt[cnt==cnt.max()].index
A=A[A.m.isin(full)]
sn=A[A.m=='Seasonal_Naive'].set_index('ds')
A['nm']=A.mase/A.ds.map(sn.mase); A['nc']=A.crps/A.ds.map(sn.crps)
A['rk']=A.groupby('ds').crps.rank(method='min')
g=A.groupby('m').agg(MASE=('nm',lambda x: np.exp(np.log(x).mean())),CRPS=('nc',lambda x: np.exp(np.log(x).mean())),rank=('rk','mean')).sort_values('rank')
g['type']=[meta[m].get('model_type') for m in g.index]; g['leak']=[meta[m].get('testdata_leakage') for m in g.index]
g['org']=[meta[m].get('org') for m in g.index]
pd.set_option('display.width',250); pd.set_option('display.max_rows',300)
print('n datasets',cnt.max(),'models',len(g))
print(g.head(45).round(3).to_string())
print('---- non-leak zero-shot/pretrained only')
print(g[(g.leak.astype(str).str.lower()=='no')&(g.type.isin(['zero-shot','pretrained']))].head(20).round(3).to_string())
for m in ['TabPFN-TS','TiRex-2-Zeroshot','TiRex-2-Pretrained','TimesFM-2.5','TimesFM-3','Timer-S1','sundial_base_128m','Chronos-2','Simons-297M','Toto-2.0-313m','t0-gamma','Timestral-209M','TimeH2O-v1','Moirai2']:
    if m in g.index: print(m, g.index.get_loc(m)+1, g.loc[m].to_dict())
    else: print(m,'not in full set', cnt.get(m))
