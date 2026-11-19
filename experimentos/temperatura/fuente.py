"""Lo que se fija antes de entrenar: el umbral de cada área (con 2016–2024) y la fuente del pronóstico (con 2025).

1. **Umbral.** Demanda diaria del área (media y máxima, en log) frente a la temperatura media diaria ERA5, con efectos
   fijos de año-mes y día de la semana, sin feriados ni 2020, solo hasta 2024: log(D) ~ FE + b1·T + b2·max(0, T − τ).
   τ es el de menor suma de cuadrados en una rejilla de 0.25 °C.
2. **Fuente.** Error de la media diaria pronosticada (llevada al nivel de ERA5 con el ajuste estimado con < 2025)
   frente a ERA5, por modelo, desfase, área y año, y correlación de los cambios día a día. Se elige con 2025.

Uso: python -m experimentos.temperatura.fuente   (escribe umbral.csv y fuente.csv en reportes/sein/temperatura/)
"""

import holidays
import numpy as np
import pandas as pd

from experimentos.temperatura import comun as c
from experimentos.temperatura import descarga


def umbral(rejilla=np.arange(18, 27.01, 0.25)):  # noqa: B008
    t = c.era5_horaria().loc[: "2024-12-31 23:00"]
    dem = pd.read_parquet(c.RAIZ / "coes" / "silver" / "demanda_areas.parquet").set_index("DateTime")
    dia = (dem.index - c.PASO).normalize()
    pe = holidays.country_holidays("PE", years=range(2015, 2026))
    filas = []
    for area in c.AREAS:
        d = dem[area.upper()].groupby(dia).agg(["mean", "max", "count"])
        d = d[d["count"] == 48].join(t[area].groupby(t.index.normalize()).mean().rename("T"), how="inner").dropna()
        d = d[(d.index < "2025-01-01") & ((d.index < "2020-03-01") | (d.index >= "2021-01-01"))]
        d = d[[x not in pe for x in d.index]]
        fe = pd.get_dummies(d.index.to_period("M").astype(str)).astype(float).to_numpy()
        dow = pd.get_dummies(d.index.day_of_week).astype(float).to_numpy()[:, 1:]
        for columna in ("mean", "max"):
            y = np.log(d[columna].to_numpy())
            for tau in rejilla:
                X = np.column_stack([fe, dow, d["T"], np.maximum(0, d["T"] - tau)])
                b = np.linalg.lstsq(X, y, rcond=None)[0]
                filas.append({"area": area, "demanda": "media" if columna == "mean" else "maxima", "tau": tau,
                              "sse": float(((y - X @ b) ** 2).sum()), "pendiente_bajo_pct": 100 * b[-2],
                              "pendiente_extra_pct": 100 * b[-1], "dias_sobre": int((d["T"] > tau).sum()),
                              "dias": len(d)})
    return pd.DataFrame(filas)


def precision_fuentes(era5=None):
    era5 = c.era5_horaria() if era5 is None else era5
    tabla = descarga.leer()
    obs = c.diarias(era5)
    filas = []
    for modelo in descarga.MODELOS:
        pron = c.pronostico_horario(modelo, tabla)
        ajustada = c.aplicar_ajuste(pron, c.ajuste_nivel(pron, era5))
        for n in (1, 2, 3):
            crudo, adj = c.diarias(pron[n]), c.diarias(ajustada[n])
            for area in c.AREAS:
                o = obs[area]["media"].dropna()
                for anio in range(2021, 2027):
                    k = o.index[o.index.year == anio].intersection(adj[area]["media"].dropna().index)
                    if len(k) < 30:
                        continue
                    e = adj[area]["media"].loc[k] - o.loc[k]
                    ec = crudo[area]["media"].loc[k] - o.loc[k]
                    dd = pd.DataFrame({"p": adj[area]["media"].loc[k], "o": o.loc[k]}).asfreq("D").diff().dropna()
                    calido = o.loc[k] > c.UMBRAL[area]
                    filas.append({"modelo": modelo, "desfase": n, "area": area, "anio": anio, "dias": len(k),
                                  "mae_ajustado": e.abs().mean(), "sesgo_ajustado": e.mean(),
                                  "mae_crudo": ec.abs().mean(), "sesgo_crudo": ec.mean(),
                                  "r_cambios": dd.corr().iloc[0, 1], "dias_sobre_umbral": int(calido.sum()),
                                  "sesgo_dias_sobre_umbral": e[calido].mean() if calido.any() else np.nan})
    return pd.DataFrame(filas)


def main():
    u = umbral()
    c.guardar(u, "umbral.csv")
    mejor = u.loc[u.groupby(["area", "demanda"])["sse"].idxmin()]
    print(mejor.round(3).to_string(index=False))
    f = precision_fuentes()
    c.guardar(f, "fuente.csv")
    print(f[(f["anio"] == 2025)].pivot_table(index=["area", "desfase"], columns="modelo",
                                              values="mae_ajustado").round(2))


if __name__ == "__main__":
    main()
