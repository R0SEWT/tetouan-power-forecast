"""Figuras del short paper (paper/quarto/), a una columna de IEEE (8.9 cm) y listas para imprimir.

Se dibujan de nuevo, sin recalcular ningún modelo, a partir de lo que ya escribieron los notebooks en la carpeta
de datos ($TETOUAN_DATA o ./data):

  nino_demanda           capas silver de demanda e ICEN, como el notebook 01
  real_predicho_2025     reportes/sein/modelado/predicciones_validacion_1h_*.csv (notebook 02)
  mensual_2026           reportes/sein/prueba_2026/mensual.csv (notebook 03)
  shap_familias          reportes/sein/explicabilidad/shap_por_familia.csv (notebook 05)
  fundacionales_mensual  reportes/sein/fundacionales/tablas/mensual.csv (notebook 04)

Cada una sale en PDF (vectorial, la del paper) y en PNG (la de la vista previa en HTML). Letra de 8 pt al tamaño
de impresión y la paleta Okabe-Ito, apta para daltónicos.

Uso, desde la raíz del repositorio:

    TETOUAN_DATA=/ruta/a/los/datos uv run python paper/quarto/figuras/generar.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from tetouan_power_forecast.coes import cargar_demanda_areas
from tetouan_power_forecast.medallon import raiz_datos

DESTINO = Path(__file__).resolve().parent
ANCHO = 3.5  # pulgadas: una columna de IEEEtran (8.9 cm)
AREAS = ["NORTE", "CENTRO", "SUR"]
NOMBRES = {"NORTE": "Norte", "CENTRO": "Centro", "SUR": "Sur"}
COLORES = {"NORTE": "#E69F00", "CENTRO": "#0072B2", "SUR": "#009E73"}  # Okabe-Ito, como en los notebooks
CALIDO, NEUTRO = "#D55E00", "#56B4E9"
GRIS = "#7F7F7F"
MESES = {1: "ene", 4: "abr", 7: "jul", 10: "oct"}
MARCAS_MW = {"NORTE": [800, 1200], "CENTRO": [3000, 6000], "SUR": [500, 2000]}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Nimbus Sans", "Liberation Sans", "DejaVu Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "lines.linewidth": 0.9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "axes.unicode_minus": True,
})


def guardar(fig, nombre):
    for ext in ("pdf", "png"):
        fig.savefig(DESTINO / f"{nombre}.{ext}", dpi=300)
    plt.close(fig)
    print(f"{nombre}: {fig.get_size_inches().round(2)} pulgadas")


def nino_demanda(raiz):
    """ICEN mensual y variación interanual de la demanda media mensual de cada área (notebook 01)."""
    demanda = cargar_demanda_areas()
    mensual = demanda.set_index("DateTime")[AREAS].resample("MS").mean()
    variacion = 100 * (mensual / mensual.shift(12) - 1)
    icen = pd.read_parquet(raiz / "exogenas" / "silver" / "icen.parquet").set_index("mes")["icen"].loc["2016":]
    fig, (arriba, abajo) = plt.subplots(2, 1, figsize=(ANCHO, 2.7), sharex=True, layout="constrained",
                                        gridspec_kw={"height_ratios": [1, 1.4]})
    arriba.bar(icen.index, icen, width=25, color=np.where(icen > 0.4, CALIDO, NEUTRO))
    arriba.axhline(0.4, color=GRIS, lw=0.6, ls="--")
    arriba.set_ylabel("ICEN")
    arriba.yaxis.set_major_locator(MaxNLocator(4))
    for a in AREAS:
        abajo.plot(variacion.index, variacion[a], color=COLORES[a], lw=0.8, label=NOMBRES[a])
    abajo.axhline(0, color="black", lw=0.5)
    abajo.set_ylabel("Variación interanual (%)")
    abajo.legend(ncol=3, loc="upper left", frameon=False, handlelength=1.2, columnspacing=1.0)
    abajo.set_xlim(pd.Timestamp("2016-01-01"), variacion.index.max() + pd.Timedelta(days=20))
    anios = range(2016, 2027, 2)
    abajo.set_xticks([pd.Timestamp(f"{y}-01-01") for y in anios], [str(y) for y in anios])
    guardar(fig, "nino_demanda")


def real_predicho_2025(raiz):
    """Real contra predicho y residuos del Random Forest en la validación de 2025, a 1 h (notebook 02)."""
    fig, ejes = plt.subplots(2, 3, figsize=(ANCHO, 2.6), layout="constrained")
    for j, a in enumerate(AREAS):
        t = pd.read_csv(raiz / "reportes" / "sein" / "modelado" / f"predicciones_validacion_1h_{a.lower()}.csv")
        real, pred = t["real"], t["fijo_M0"]
        residuo = real - pred
        eje = ejes[0, j]
        eje.scatter(real, pred, s=0.3, alpha=0.25, color=COLORES[a], linewidths=0, rasterized=True)
        limites = [real.min(), real.max()]
        eje.plot(limites, limites, color="black", lw=0.6)
        eje.set_title(NOMBRES[a])
        eje.set_xticks(MARCAS_MW[a])
        eje.set_yticks(MARCAS_MW[a])
        eje = ejes[1, j]
        bajo, alto = np.percentile(residuo, [0.1, 99.9])
        cuentas, _, _ = eje.hist(residuo.clip(bajo, alto), bins=50, color=COLORES[a])
        eje.set_ylim(0, 2.1 * cuentas.max())
        eje.axvline(0, ymax=1 / 2.1, color="black", lw=0.6)
        eje.set_yticks([])
        eje.xaxis.set_major_locator(MaxNLocator(3, symmetric=True))
        eje.text(0.02, 0.98, f"media {residuo.mean():.1f}\ndesv. {residuo.std():.1f}", transform=eje.transAxes,
                 va="top", ha="left", linespacing=1.1)
    ejes[0, 0].set_ylabel("Predicho (MW)")
    ejes[0, 1].set_xlabel("Real (MW)")
    ejes[1, 0].set_ylabel("Periodos")
    ejes[1, 1].set_xlabel("Residuo: real − predicho (MW)")
    guardar(fig, "real_predicho_2025")


def mensual_2026(raiz):
    """MAE mensual de 2026: modelo fijo, reentrenado cada semana y mejor referencia (notebook 03)."""
    mensual = pd.read_csv(raiz / "reportes" / "sein" / "prueba_2026" / "mensual.csv")
    mensual["m"] = mensual["Mes"].str[5:].astype(int)
    estilos = {"Fijo (A)": "-", "Semanal (C)": "--", "Semanal con exógenas (D)": ":"}
    fig, ejes = plt.subplots(2, 3, figsize=(ANCHO, 2.9), sharex=True, layout="constrained")
    for i, h in enumerate(["1h", "24h"]):
        for j, a in enumerate(AREAS):
            eje = ejes[i, j]
            d = mensual[(mensual["Horizonte"] == h) & (mensual["Área"] == NOMBRES[a])].sort_values("m")
            eje.plot(d["m"], d["Mejor referencia"], color=GRIS, lw=1.1)
            for col, estilo in estilos.items():
                eje.plot(d["m"], d[col], estilo, color=COLORES[a], lw=0.9)
            eje.set_title(f"{NOMBRES[a]}, {h[:-1]} h")
            eje.yaxis.set_major_locator(MaxNLocator(3))
            eje.set_xticks(list(MESES), list(MESES.values()))
        ejes[i, 0].set_ylabel("MAE (MW)")
    claves = [Line2D([], [], color="black", ls=e, lw=0.9, label=n) for n, e in estilos.items()]
    claves.append(Line2D([], [], color=GRIS, lw=1.1, label="Mejor referencia"))
    fig.legend(handles=claves, loc="outside upper center", ncol=2, frameon=False, handlelength=2.2,
               columnspacing=1.2)
    guardar(fig, "mensual_2026")


def shap_familias(raiz):
    """|SHAP| medio por familia de variables del XGBoost de la app en la prueba de 2026 (notebook 05)."""
    tabla = pd.read_csv(raiz / "reportes" / "sein" / "explicabilidad" / "shap_por_familia.csv")
    familias = ["Demanda reciente", "Calendario", "Código de área", "Clima", "El Niño", "Fallas"]
    y = np.arange(len(familias))
    alto = 0.26
    fig, ejes = plt.subplots(1, 2, figsize=(ANCHO, 1.9), sharey=True, layout="constrained")
    for eje, h in zip(ejes, ["1h", "24h"]):
        d = tabla[(tabla["Horizonte"] == h) & (tabla["Año"] == 2026)].set_index("Área")
        for k, a in enumerate(AREAS):
            eje.barh(y + (k - 1) * alto, d.loc[NOMBRES[a], familias], height=alto, color=COLORES[a],
                     label=NOMBRES[a])
        eje.set_title(f"A {h[:-1]} h (2026)")
        eje.xaxis.set_major_locator(MaxNLocator(3))
        eje.set_xlabel("|SHAP| medio (MW)")
    ejes[0].set_yticks(y, familias)
    ejes[0].invert_yaxis()
    ejes[1].legend(loc="lower right", frameon=False, handlelength=1.0)
    guardar(fig, "shap_familias")


def fundacionales_mensual(raiz):
    """Error mensual de cuatro modelos frente al Random Forest elegido, 2025 y 2026 (notebook 04)."""
    mensual = pd.read_csv(raiz / "reportes" / "sein" / "fundacionales" / "tablas" / "mensual.csv")
    modelos = {
        "simons_c2048": ("Simons, zero-shot", "#0072B2", "o"),
        "chronos2ftcal_c2048": ("Chronos-2 ajustado", "#D55E00", "s"),
        "xgb_simons_c2048": ("Híbrido XGBoost + Simons", "#009E73", "^"),
        "combinacion_c2048": ("Combinación", "#CC79A7", "D"),
    }
    fig, ejes = plt.subplots(2, 3, figsize=(ANCHO, 3.0), sharex=True, layout="constrained")
    for i, h in enumerate(["1h", "24h"]):
        for j, a in enumerate(AREAS):
            eje = ejes[i, j]
            for m, (_, color, marca) in modelos.items():
                d = mensual[(mensual["Modelo"] == m) & (mensual["Horizonte"] == h)
                            & (mensual["Área"] == NOMBRES[a])].sort_values("Mes")
                x = pd.PeriodIndex(d["Mes"], freq="M").to_timestamp()
                eje.plot(x, 100 * (d["MAE (MW)"] / d["MAE del elegido (MW)"] - 1), marker=marca, ms=1.6,
                         color=color, lw=0.7)
            eje.axhline(0, color="black", lw=0.5)
            eje.axvline(pd.Timestamp("2026-01-01"), color=GRIS, ls=":", lw=0.7)
            eje.set_title(f"{NOMBRES[a]}, {h[:-1]} h")
            eje.yaxis.set_major_locator(MaxNLocator(4))
            eje.set_xticks([pd.Timestamp("2025-07-01"), pd.Timestamp("2026-06-01")], ["2025", "2026"])
            eje.tick_params(axis="x", length=0)
        ejes[i, 0].set_ylabel("MAE frente al RF (%)")
    claves = [Line2D([], [], color=c, marker=mk, ms=3, lw=0.8, label=n) for n, c, mk in modelos.values()]
    fig.legend(handles=claves, loc="outside upper center", ncol=2, frameon=False, handlelength=1.8,
               columnspacing=1.2)
    guardar(fig, "fundacionales_mensual")


if __name__ == "__main__":
    raiz = raiz_datos()
    nino_demanda(raiz)
    real_predicho_2025(raiz)
    mensual_2026(raiz)
    shap_familias(raiz)
    fundacionales_mensual(raiz)
