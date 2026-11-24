import sys
sys.path.insert(0, "/tmp/claude-1000/-home-cip-exodia-Code-exprimental/6eb617d0-39a3-45e8-8eeb-156768150d8d/scratchpad/scripts")
import numpy as np, pandas as pd
from load849 import load
df = load(sys.argv[1]).set_index("dt")
print(df.groupby(df.index.month)[["Z1","Z2","Z3","T"]].mean().round(0).to_string())
dm = df[["Z1","Z2","Z3"]].resample("D").mean()
for c in ["Z1","Z2","Z3"]:
    r = dm[c] / dm[c].shift(1).rolling(7).median()
    print(c, "days ratio>1.12 or <0.88 vs prior-7d median:", [(i.strftime("%m-%d"), round(v,2)) for i,v in r[(r>1.12)|(r<0.88)].items()])
# Z3 summer: daily mean around June-Sept
print("Z3 daily mean weekly, Jun-Sep:", dm.Z3["2017-06-01":"2017-09-30"].resample("W").mean().round(0).to_dict())
print("Z3/Z1 ratio monthly:", (df.Z3/df.Z1).groupby(df.index.month).mean().round(3).to_dict())
# Ramadan and Eid effects on Z1 evening profile
ram = df["2017-05-27":"2017-06-25"]; pre = df["2017-05-06":"2017-05-26"]
for lbl, d in [("pre-Ramadan May6-26", pre), ("Ramadan May27-Jun25", ram)]:
    p = d.Z1.groupby(d.index.hour).mean()
    print(lbl, "Z1 hourly mean:", p.round(0).astype(int).to_dict())
for day in ["2017-06-26","2017-06-27","2017-09-01","2017-09-02","2017-09-03","2017-07-30","2017-11-06","2017-11-18","2017-12-01","2017-01-11","2017-05-01","2017-08-14","2017-08-21"]:
    d = pd.Timestamp(day)
    same = dm.Z1[(dm.index.dayofweek == d.dayofweek) & (abs((dm.index - d).days) <= 21) & (dm.index != d)]
    print(day, d.day_name()[:3], "Z1 daily mean", round(dm.Z1[d]), "vs same weekday +-3wk mean", round(same.mean()), "ratio", round(dm.Z1[d]/same.mean(),3))
# naive-baseline residual for t+6 on holidays (persist+daily delta) to show calendar exceptions matter
