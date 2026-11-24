import sys, pandas as pd
df = pd.read_csv(sys.argv[1], parse_dates=["t"]).set_index("t").sort_index()
full = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="30min"))
miss = full[full.iloc[:,0].isna()].index
print("portal missing by day:", pd.Series(miss.normalize()).value_counts().sort_index().to_dict())
for d in ["2017-12-27","2018-06-07","2018-08-11","2019-03-30","2019-07-31","2020-11-04","2020-12-25"]:
    s = full.loc[pd.Timestamp(d)+pd.Timedelta(minutes=30): pd.Timestamp(d)+pd.Timedelta(days=1)]
    print(d, "portal non-null Ejecutado:", int(s.iloc[:,0].notna().sum()), "PDO:", int(s.iloc[:,1].notna().sum()))
