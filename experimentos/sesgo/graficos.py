"""Los gráficos del diagnóstico de sesgo (PNG). Paleta categórica validada para daltonismo (azul, naranja, aguamarina)
y siempre con marcador o etiqueta además del color.

Uso: python -m experimentos.sesgo.graficos [carpeta]   (por defecto, reportes/sein/sesgo/graficos)
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experimentos.sesgo import comun as c

AZUL, NARANJA, AGUA = "#2a78d6", "#eb6834", "#1baf7a"
GRIS, TINTA, TINTA2 = "#8a8985", "#0b0b0b", "#52514e"
COLORES = {"NORTE": AZUL, "CENTRO": NARANJA, "SUR": AGUA}
MARCAS = {"NORTE": "o", "CENTRO": "s", "SUR": "^"}
NOMBRE_AREA = {"NORTE": "Norte", "CENTRO": "Centro", "SUR": "Sur"}

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": GRIS, "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titlesize": 11, "axes.titleweight": "bold", "legend.frameon": False,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
})


def _leer(nombre, **kw):
    return pd.read_csv(c.SALIDA / f"{nombre}.csv", **kw)


def vivo_diario(destino):
    """Sesgo diario a 24 h de Chronos-2 ajustado del 1-oct al 13-nov y la temperatura de Lima."""
    e = c.errores_continuos()
    e = e[(e["horizonte"] == "24h") & (e["dia"] >= "2026-10-01") & e["real"].notna()]
    d = e.assign(err=e["pred"] - e["real"]).groupby(["area", "dia"])["err"].mean().unstack("area")
    t = c.temperatura_diaria()
    t = t[(t["area"] == "CENTRO") & (t["dia"] >= "2026-10-01") & (t["dia"] <= d.index.max())].set_index("dia")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    for x in (a1, a2):
        x.axvspan(pd.Timestamp("2026-10-17 12:00"), pd.Timestamp("2026-10-22 12:00"), color="#efeeea", zorder=0)
        x.axvline(pd.Timestamp("2026-10-22 12:00"), color=GRIS, lw=1, ls="--")
    a1.axhline(0, color=TINTA2, lw=0.8)
    for area in ["NORTE", "CENTRO", "SUR"]:
        a1.plot(d.index, d[area], color=COLORES[area], marker=MARCAS[area], ms=4, lw=1.6, label=NOMBRE_AREA[area])
    a1.set_ylim(-150, 220)
    a1.annotate("13-nov: −73 MW en el día\n(−105 MW en lo emitido antes)", (pd.Timestamp("2026-11-13"),
                d.loc["2026-11-13", "CENTRO"]), xytext=(pd.Timestamp("2026-11-05 12:00"), -128), textcoords="data",
                fontsize=8.5, color=TINTA, arrowprops={"arrowstyle": "-", "color": GRIS, "lw": 0.8})
    a1.annotate("1-nov (feriado y domingo)\ny lunes 2", (pd.Timestamp("2026-11-02"), d.loc["2026-11-02", "CENTRO"]),
                xytext=(pd.Timestamp("2026-10-23 06:00"), -128), textcoords="data", fontsize=8.5, color=TINTA,
                arrowprops={"arrowstyle": "-", "color": GRIS, "lw": 0.8})
    a1.text(pd.Timestamp("2026-10-20"), a1.get_ylim()[1] * 0.92, "sin prueba\nni registro", ha="center", va="top",
            fontsize=8, color=TINTA2)
    a1.text(pd.Timestamp("2026-10-23"), a1.get_ylim()[1] * 0.92, " registro en vivo →", ha="left", va="top",
            fontsize=8.5, color=TINTA2)
    a1.set_ylabel("Sesgo diario (MW)\npronóstico − real")
    a1.set_title("Chronos-2 ajustado a 24 h: sesgo de cada día (negativo = subestima)", loc="left")
    a1.legend(ncol=3, loc="lower left")
    era5 = t["fuente"] != "analisis_ajustado"
    for col, nombre, estilo in (("temp_media", "media", "-"), ("temp_min", "mínima (madrugada)", "-")):
        lw = 1.8 if col == "temp_min" else 1.2
        color = NARANJA if col == "temp_min" else TINTA2
        a2.plot(t.index[era5], t.loc[era5, col], color=color, lw=lw, ls=estilo, label=f"{nombre}, ERA5")
        a2.plot(t.index[~era5 | era5.shift(-1, fill_value=False)], t.loc[~era5 | era5.shift(-1, fill_value=False), col],
                color=color, lw=lw, ls=":", label=f"{nombre}, análisis del modelo")
    a2.set_ylabel("Lima (°C)")
    a2.legend(ncol=2, fontsize=8, loc="upper left")
    a2.set_title("Temperatura de Lima (Open-Meteo; desde el 8-nov, análisis de su modelo, no estación)", loc="left",
                 fontsize=9.5, fontweight="normal")
    marcas = pd.date_range("2026-10-01", d.index.max(), freq="7D")
    a2.set_xticks(marcas, [f"{m.day}-{'oct' if m.month == 10 else 'nov'}" for m in marcas])
    fig.tight_layout()
    fig.savefig(destino / "1_vivo_sesgo_diario.png", dpi=150)
    plt.close(fig)


def calor_deciles(destino):
    """Sesgo y error del pico (% del nivel) por decil de anomalía de la mínima, 24 h, Chronos-2 y XGBoost."""
    d = _leer("diario", parse_dates=["dia"])
    d = d[(d["horizonte"] == "24h") & d["tramo"].isin(["2025", "2026"]) & d["modelo"].isin(["c2", "xgb"])]
    d["pico_pct"] = 100 * d["error_pico"] / d["real_max"]
    g = d.groupby(["tramo", "modelo", "decil_anom_min"])[["sesgo_pct", "pico_pct"]].mean().reset_index()
    fig, ejes = plt.subplots(2, 2, figsize=(10, 6), sharex=True, sharey="row")
    nombres = {"c2": ("Chronos-2 ajustado", AZUL, "o"), "xgb": ("XGBoost híbrido (razón)", NARANJA, "s")}
    for j, tramo in enumerate(["2025", "2026"]):
        for i, (col, etiqueta) in enumerate((("sesgo_pct", "Sesgo diario (% del nivel)"),
                                             ("pico_pct", "Error del pico diario (%)"))):
            x = ejes[i, j]
            x.axhline(0, color=TINTA2, lw=0.8)
            for m, (nombre, color, marca) in nombres.items():
                s = g[(g["tramo"] == tramo) & (g["modelo"] == m)]
                x.plot(s["decil_anom_min"], s[col], color=color, marker=marca, ms=5, lw=1.6, label=nombre)
            if j == 0:
                x.set_ylabel(etiqueta)
            if i == 0:
                x.set_title(tramo, loc="left")
            x.set_xticks(range(1, 11))
    ejes[0, 0].legend(loc="lower left", fontsize=8.5)
    fig.supxlabel("Decil de anomalía de la temperatura mínima del día objetivo (1 = noche más fresca, 10 = más cálida)",
                  fontsize=9.5, color=TINTA2)
    fig.suptitle("¿Fallan más en noches cálidas? Promedio de las tres áreas, 24 h", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(destino / "2_calor_por_decil.png", dpi=150)
    plt.close(fig)


def autocorrelacion(destino):
    a = _leer("autocorrelacion")
    d = _leer("diario")
    a = a[(a["modelo"] == "c2") & (a["horizonte"] == "24h")]
    fig, ejes = plt.subplots(1, 3, figsize=(10, 3.4), sharey=True)
    rezagos = np.arange(1, 15)
    for x, tramo in zip(ejes, ["2025", "2026", "vivo"]):
        n = d[(d["tramo"] == tramo) & (d["modelo"] == "c2") & (d["horizonte"] == "24h")]["dia"].nunique()
        banda = 1.96 / np.sqrt(n)
        x.axhspan(-banda, banda, color="#efeeea", zorder=0)
        x.axhline(0, color=TINTA2, lw=0.8)
        for k, area in enumerate(["NORTE", "CENTRO", "SUR"]):
            fila = a[(a["tramo"] == tramo) & (a["area"] == area)].iloc[0]
            x.plot(rezagos + (k - 1) * 0.15, [fila[f"r{r}"] for r in rezagos], color=COLORES[area],
                   marker=MARCAS[area], ms=4, lw=0, label=NOMBRE_AREA[area])
            x.vlines(rezagos + (k - 1) * 0.15, 0, [fila[f"r{r}"] for r in rezagos], color=COLORES[area], lw=1.2)
        x.set_title({"vivo": f"en vivo ({n} días)"}.get(tramo, f"{tramo} ({n} días)"), loc="left")
        x.set_xlabel("Rezago (días)")
        x.set_xticks([1, 7, 14])
    ejes[0].set_ylabel("Autocorrelación\ndel sesgo diario")
    ejes[0].legend(fontsize=8, loc="upper right")
    fig.suptitle("¿Cuánto dura un sesgo? Chronos-2 ajustado a 24 h (banda gris: ruido, 95 %)", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(destino / "3_autocorrelacion_sesgo.png", dpi=150)
    plt.close(fig)


def correccion(destino):
    g = _leer("grilla_sesgo")
    g = g[g["horizonte"] == "24h"]
    familias = {
        ("aditiva · global · media", "λ=1"): ("aditiva, media, completa", AZUL, "o", "-"),
        ("aditiva · global · media", "λ=0.5"): ("aditiva, media, a la mitad", NARANJA, "s", "-"),
        ("aditiva · global · mediana", "λ=0.5"): ("aditiva, mediana, a la mitad", AGUA, "^", "-"),
        ("aditiva · hora · media", "λ=0.5"): ("por media hora, a la mitad", GRIS, "D", ":"),
    }
    fig, ejes = plt.subplots(1, 3, figsize=(10, 3.6), sharey=True)
    for x, tramo in zip(ejes, ["2025", "2026", "vivo"]):
        s = g[g["tramo"] == tramo]
        x.axhline(1, color=TINTA2, lw=0.8)
        for (prefijo, lam), (nombre, color, marca, estilo) in familias.items():
            filas = []
            for w in (1, 3, 7, 14, 28):
                v = f"{prefijo} · {w} d · {lam}"
                m = s[s["variante"] == v]["razon_mae"]
                if len(m):
                    filas.append((w, m.mean()))
            if filas:
                w, r = zip(*filas)
                x.plot(w, r, color=color, marker=marca, ms=5, lw=1.4, ls=estilo, label=nombre)
        x.set_xscale("log")
        x.set_xticks([1, 3, 7, 14, 28], ["1", "3", "7", "14", "28"])
        x.minorticks_off()
        x.set_xlabel("Ventana (días)")
        x.set_title({"vivo": "en vivo (22 días)"}.get(tramo, tramo), loc="left")
    ejes[0].set_ylabel("MAE corregido / MAE sin corregir\n(promedio de las tres áreas)")
    ejes[0].set_ylim(0.93, 1.22)
    ejes[0].legend(fontsize=7.5, loc="upper right")
    fig.suptitle("Corregir el sesgo con los errores recientes (24 h): por debajo de 1 mejora", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(destino / "4_correccion_sesgo.png", dpi=150)
    plt.close(fig)


def cobertura(destino):
    cob = _leer("cobertura_ic")
    cob = cob[cob["horizonte"] == "24h"]
    filas = [(t, a) for t in ["2025", "2026", "vivo"] for a in ["NORTE", "CENTRO", "SUR"]]
    fig, x = plt.subplots(figsize=(8.5, 4.8))
    x.axvline(80, color=TINTA2, lw=1, ls="--")
    for i, (t, a) in enumerate(filas):
        y = len(filas) - 1 - i
        m = cob[(cob["tramo"] == t) & (cob["area"] == a) & (cob["rango"] == "modelo")].iloc[0]
        r = cob[(cob["tramo"] == t) & (cob["area"] == a) & (cob["rango"] == "adaptativo")].iloc[0]
        x.plot([m["cobertura"], r["cobertura"]], [y, y], color="#d8d7d2", lw=2, zorder=1)
        x.errorbar(m["cobertura"], y + 0.12, xerr=[[m["cobertura"] - m["bajo"]], [m["alto"] - m["cobertura"]]],
                   fmt="o", color=GRIS, ms=6, lw=1, capsize=2, label="cuantiles del modelo" if i == 0 else None)
        x.errorbar(r["cobertura"], y - 0.12, xerr=[[r["cobertura"] - r["bajo"]], [r["alto"] - r["cobertura"]]],
                   fmt="D", color=AZUL, ms=6, lw=1, capsize=2, label="rango adaptativo (ACI)" if i == 0 else None)
        x.text(92.5, y, f"{m['ancho']:.0f} → {r['ancho']:.0f} MW", va="center", fontsize=8, color=TINTA2)
    x.set_yticks(range(len(filas)), [f"{'en vivo' if t == 'vivo' else t} · {NOMBRE_AREA[a]}" for t, a in filas][::-1])
    x.set_xlim(66, 98)
    x.set_xlabel("Cobertura del rango 10–90 a 24 h (%), con IC 95 % por semanas")
    x.text(92.5, len(filas) - 0.35, "ancho medio", fontsize=8, color=TINTA2)
    x.legend(loc="lower left", fontsize=8.5)
    x.set_title("Cobertura antes y después del rango adaptativo (meta: 80 %)", loc="left")
    fig.tight_layout()
    fig.savefig(destino / "5_cobertura.png", dpi=150)
    plt.close(fig)


def main(destino=None):
    destino = Path(destino or c.SALIDA / "graficos")
    destino.mkdir(parents=True, exist_ok=True)
    for f in (vivo_diario, calor_deciles, autocorrelacion, correccion, cobertura):
        f(destino)
        print(f.__name__, "listo")
    return destino


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
