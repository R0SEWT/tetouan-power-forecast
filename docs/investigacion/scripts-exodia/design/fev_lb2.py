import sys, glob, os, re
import pandas as pd, numpy as np
root=sys.argv[1]; hidden_names=set(sys.argv[2].split(','))
A=pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(root,'*.csv'))],ignore_index=True)
A=A[~A.model_name.isin(hidden_names)]
for metric in ['SQL','MASE']:
    P=A.pivot_table(index='task_name',columns='model_name',values=metric)
    # impute missing with seasonal naive (fev convention is similar)
    P=P.apply(lambda c: c.fillna(P['Seasonal Naive']))
    rel=P.div(P['Seasonal Naive'],axis=0).clip(1e-2,100)
    skill=1-np.exp(np.log(rel).mean())
    W={m:((P.drop(columns=m).values>P[[m]].values).sum()+0.5*(P.drop(columns=m).values==P[[m]].values).sum())/P.drop(columns=m).size for m in P.columns}
    R=pd.DataFrame({'skill':skill,'winrate':pd.Series(W)}).sort_values('winrate',ascending=False)
    R['pos']=range(1,len(R)+1)
    print('--',metric,len(R),'models'); print(R.head(12).round(3).to_string())
    print(R.loc[[m for m in ['TabPFN-TS-3','TiRex-2','TimesFM-2.5','timesfm-3','Sundial-Base','Chronos-2','Simons-297M','Toto-2.0-2.5B','t0-gamma','Timestral-209M'] if m in R.index]].round(3).to_string())
