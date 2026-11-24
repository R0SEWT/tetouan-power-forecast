import sys, math
sys.path.insert(0, "/tmp/claude-1000/-home-cip-exodia-Code-exprimental/6eb617d0-39a3-45e8-8eeb-156768150d8d/scratchpad/scripts")
import numpy as np, pandas as pd
from load849 import load
df = load(sys.argv[1]).set_index("dt")
lat, lon = 35.5785, -5.3684
def sun_utc(date):
    n = date.timetuple().tm_yday; g = 2*math.pi/365*(n-1)
    eot = 229.18*(0.000075+0.001868*math.cos(g)-0.032077*math.sin(g)-0.014615*math.cos(2*g)-0.040849*math.sin(2*g))
    decl = 0.006918-0.399912*math.cos(g)+0.070257*math.sin(g)-0.006758*math.cos(2*g)+0.000907*math.sin(2*g)-0.002697*math.cos(3*g)+0.00148*math.sin(3*g)
    ha = math.degrees(math.acos(math.cos(math.radians(90.833))/(math.cos(math.radians(lat))*math.cos(decl))-math.tan(math.radians(lat))*math.tan(decl)))
    noon = 720-4*lon-eot
    return noon-4*ha, noon, noon+4*ha
rows = []
for d, g in df.groupby(df.index.date):
    d = pd.Timestamp(d); sr, sn, ss = sun_utc(d)
    mod = g.index.hour*60+g.index.minute
    ev = g[(mod >= 16*60) & (mod <= 23*60)]
    pk = ev.Z1.idxmax(); pkm = pk.hour*60+pk.minute
    # evening ramp: first time after 16:00 when Z1 exceeds midpoint between 16:00-17:30 min and evening max
    base = g[(mod >= 15*60) & (mod <= 17*60+30)].Z1.min(); top = ev.Z1.max()
    thr = base + 0.5*(top-base)
    em = ev[(ev.Z1 > thr)].index[0]; emm = em.hour*60+em.minute
    # GDF last time > 20 (sunset proxy) and first time >20
    gd = g[g.GDF > 20]; gl = gd.index[-1].hour*60+gd.index[-1].minute if len(gd) else np.nan
    gf = gd.index[0].hour*60+gd.index[0].minute if len(gd) else np.nan
    rows.append(dict(date=d, dow=d.dayofweek, sunset_utc=ss, sunrise_utc=sr, peak_minus_sunset=pkm-ss, evramp_minus_sunset=emm-ss,
                     gdf_last20_minus_sunset=gl-ss, gdf_first20_minus_sunrise=gf-sr))
R = pd.DataFrame(rows).set_index("date")
def win(a, b, col):
    m = (R.index >= a) & (R.index < b)
    return round(R.loc[m, col].median(), 0)
print("median (minutes) in 7-day windows before | after each transition")
for lbl, t in [("DST start", "2017-03-26"), ("Ramadan susp.", "2017-05-21"), ("DST resume", "2017-07-02"), ("DST end", "2017-10-29"), ("control", "2017-02-12"), ("control", "2017-09-17"), ("control", "2017-12-10")]:
    t = pd.Timestamp(t)
    out = []
    for col in ["evramp_minus_sunset", "peak_minus_sunset", "gdf_last20_minus_sunset", "gdf_first20_minus_sunrise"]:
        out.append(f"{col}: {win(t-pd.Timedelta('7D'), t, col)} | {win(t+pd.Timedelta('1D'), t+pd.Timedelta('8D'), col)}")
    print(lbl, t.date(), " ; ".join(out))
print("\nmonthly median evramp_minus_sunset:", R.groupby(R.index.month).evramp_minus_sunset.median().to_dict())
print("monthly median gdf_first20_minus_sunrise:", R.groupby(R.index.month).gdf_first20_minus_sunrise.median().to_dict())
print("monthly median gdf_last20_minus_sunset:", R.groupby(R.index.month).gdf_last20_minus_sunset.median().to_dict())
# raw values at transition hours: check for interpolation (constant 2nd diff) in loads
for day in ["2017-03-26", "2017-05-21", "2017-07-02", "2017-10-29"]:
    sub = df.loc[pd.Timestamp(day)+pd.Timedelta("1h"):pd.Timestamp(day)+pd.Timedelta("4h"), ["Z1", "Z2", "Z3", "T"]]
    d2 = sub.diff().diff().round(3)
    print("\n", day, "Z1 values 01:00-04:00:", sub.Z1.round(0).astype(int).tolist())
    print("  Z1 2nd diff:", d2.Z1.dropna().round(0).astype(int).tolist())
