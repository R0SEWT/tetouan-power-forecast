"""QC de series diarias de reanálisis (Open-Meteo ERA5 / ERA5-Land, NASA POWER MERRA-2)
para Lima, Piura, Tumbes, Chiclayo 2015-2024, y su relación con el ICEN.
Uso: uv run --with pandas python -I clima_qc.py <dir_dl>
"""
import sys, io, re
import pandas as pd
import numpy as np

D = sys.argv[1]
pd.set_option("display.width", 220)

def read_om(path):
    txt = open(path).read().split("\n\n", 1)
    meta = txt[0].splitlines()[1].split(",")
    df = pd.read_csv(io.StringIO(txt[1]), parse_dates=["time"]).set_index("time")
    df.columns = ["tmax", "tmin", "tmean", "atmax", "prcp"]
    return df, {"lat": meta[0], "lon": meta[1], "elev": meta[2]}

def read_power(path):
    lines = open(path).read().splitlines()
    i = lines.index("-END HEADER-")
    elev = [l for l in lines[:i] if "elevation" in l][0].split("=")[-1].strip()
    df = pd.read_csv(io.StringIO("\n".join(lines[i + 1:])))
    df.index = pd.to_datetime(dict(year=df.YEAR, month=df.MO, day=df.DY))
    df = df.rename(columns={"T2M": "tmean", "T2M_MAX": "tmax", "T2M_MIN": "tmin", "PRECTOTCORR": "prcp", "RH2M": "rh"})
    df = df.replace(-999, np.nan)[["tmax", "tmin", "tmean", "prcp", "rh"]]
    return df, {"elev": elev}

def read_icen(path):
    rows = []
    for l in open(path, encoding="utf-8"):
        if l.startswith("%"): continue
        p = l.split()
        if len(p) >= 3: rows.append((int(p[0]), int(p[1]), float(p[2])))
    return pd.Series({pd.Period(year=y, month=m, freq="M"): v for y, m, v in rows})

icen = read_icen(f"{D}/icen/ICEN.txt")
SEAS = ["DJF","JFM","FMA","MAM","AMJ","MJJ","JJA","JAS","ASO","SON","OND","NDJ"]
oni = {}
for l in open(f"{D}/noaa/oni.ascii.txt"):
    p = l.split()
    if len(p) == 4 and p[0] in SEAS: oni[pd.Period(year=int(p[1]), month=SEAS.index(p[0]) + 1, freq="M")] = float(p[3])
oni = pd.Series(oni)

src = {}
for city in ["lima", "piura", "tumbes", "chiclayo"]:
    src[(city, "ERA5")] = read_om(f"{D}/openmeteo/{city}_era5.csv")
    src[(city, "POWER")] = read_power(f"{D}/nasapower/{city}_power.csv")
    try:
        src[(city, "ERA5-Land")] = read_om(f"{D}/openmeteo/{city}_era5_land.csv")
    except FileNotFoundError:
        pass

print("=== 1. Completitud y rangos (2015-2024) ===")
full = pd.date_range("2015-01-01", "2024-12-31", freq="D")
for (city, s), (df, meta) in src.items():
    miss = len(full.difference(df.index)); nan = int(df[["tmax", "tmin", "prcp"]].isna().sum().sum())
    bad = int((df.tmin > df.tmax).sum())
    print(f"{city:9s} {s:9s} elev_celda={meta.get('elev'):>8s} días={len(df)} faltan={miss} NaN={nan} tmin>tmax={bad} "
          f"Tmax[{df.tmax.min():.1f},{df.tmax.max():.1f}] P_max_día={df.prcp.max():.1f} mm P_anual_media={df.prcp.resample('YE').sum().mean():.0f} mm")

print("\n=== 2. Climatología de Tmax (°C) feb y ago, media 2015-2024 ===")
rows = []
for (city, s), (df, _) in src.items():
    m = df.tmax.groupby(df.index.month).mean()
    rows.append((city, s, round(m[2], 1), round(m[8], 1), round(m[2] - m[8], 1)))
print(pd.DataFrame(rows, columns=["ciudad", "fuente", "Tmax_feb", "Tmax_ago", "amplitud"]).to_string(index=False))

print("\n=== 3. Señal de El Niño: anomalías mensuales de Tmedia vs ICEN/ONI (2015-2024, n=120) ===")
for (city, s), (df, _) in src.items():
    mon = df.tmean.resample("ME").mean()
    mon.index = mon.index.to_period("M")
    anom = mon - mon.groupby(mon.index.month).transform("mean")
    j = pd.DataFrame({"a": anom, "icen": icen, "oni": oni}).dropna()
    r_i = j.a.corr(j.icen); r_o = j.a.corr(j.oni)
    r_i1 = j.a.corr(j.icen.shift(1))
    feb17 = anom.get(pd.Period("2017-03", "M")); m23 = anom.get(pd.Period("2023-03", "M")); f24 = anom.get(pd.Period("2024-02", "M"))
    print(f"{city:9s} {s:9s} r(ICEN)={r_i:+.2f} r(ICEN t-1)={r_i1:+.2f} r(ONI)={r_o:+.2f} | anom mar-2017={feb17:+.1f} mar-2023={m23:+.1f} feb-2024={f24:+.1f} °C")

print("\n=== 4. Lluvia en eventos (mm, suma) ===")
per = {"feb-mar 2017": ("2017-02-01", "2017-03-31"), "mar 2023 (Yaku)": ("2023-03-01", "2023-03-31"), "feb-mar 2016 (Niño global)": ("2016-02-01", "2016-03-31")}
rows = []
for (city, s), (df, _) in src.items():
    clim = df.prcp.groupby([df.index.year, df.index.month]).sum().groupby(level=1).mean()
    r = [city, s]
    for k, (a, b) in per.items():
        r.append(round(df.prcp.loc[a:b].sum(), 0))
    r.append(round(clim.loc[[2, 3]].sum(), 0))
    r.append(round(df.prcp.loc["2017-01-01":"2017-04-30"].max(), 1))
    rows.append(r)
print(pd.DataFrame(rows, columns=["ciudad", "fuente"] + list(per) + ["clim feb+mar 2015-24", "máx diario ene-abr 2017"]).to_string(index=False))

print("\n=== 5. Calor de verano: días con Tmax >= p90 (de todo el periodo) en ene-mar ===")
for (city, s), (df, _) in src.items():
    if s != "ERA5": continue
    p90 = df.tmax.quantile(0.9)
    jfm = df[df.index.month.isin([1, 2, 3])]
    cnt = (jfm.tmax >= p90).groupby(jfm.index.year).sum()
    print(f"{city:9s} {s} p90={p90:.1f}°C  " + " ".join(f"{y}:{c}" for y, c in cnt.items()))

print("\n=== 6. Concordancia entre fuentes (Tmedia diaria, r y sesgo ERA5 - POWER) ===")
for city in ["lima", "piura", "tumbes", "chiclayo"]:
    a = src[(city, "ERA5")][0].tmean; b = src[(city, "POWER")][0].tmean
    j = pd.concat([a, b], axis=1).dropna()
    s = f"{city:9s} r={j.iloc[:,0].corr(j.iloc[:,1]):.2f} sesgo={(j.iloc[:,0]-j.iloc[:,1]).mean():+.1f} °C"
    if (city, "ERA5-Land") in src:
        c = src[(city, "ERA5-Land")][0].tmean
        k = pd.concat([a, c], axis=1).dropna()
        s += f" | ERA5 vs ERA5-Land r={k.iloc[:,0].corr(k.iloc[:,1]):.2f} sesgo={(k.iloc[:,0]-k.iloc[:,1]).mean():+.1f}"
    print(s)
