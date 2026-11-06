import sys, io, pandas as pd
D = sys.argv[1]
def rd(p):
    t = open(p).read().split("\n\n", 1)[1]
    df = pd.read_csv(io.StringIO(t), parse_dates=["time"]).set_index("time")
    return df.iloc[:, :3].set_axis(["tmax", "tmin", "tmean"], axis=1)
for city in ["lima", "piura"]:
    base = rd(f"{D}/{city}_era5.csv"); new = rd(f"{D}/{city}_era5_2025_26.csv")
    clim = base.groupby(base.index.month).mean()
    m = new.resample("ME").mean()
    an = m - clim.loc[m.index.month].values
    print(city, "último día:", new.dropna().index.max().date())
    print(an.loc["2026"].round(1).assign(tmax_obs=m.loc["2026", "tmax"].round(1)).to_string())
    print("máx anomalía Tmax mensual 2015-2024:", round((base.resample('ME').mean() - clim.loc[base.resample('ME').mean().index.month].values).tmax.max(), 1))
