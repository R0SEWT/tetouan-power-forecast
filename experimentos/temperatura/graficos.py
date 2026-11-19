"""Los gráficos del informe (PNG, paleta apta para daltónicos: azul, naranja y aguamarina validadas en orden).

Uso: python -m experimentos.temperatura.graficos CARPETA_DESTINO
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experimentos.temperatura import comun as c

SUPERFICIE, TEXTO, TEXTO2, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
AZUL, NARANJA, AGUA, GRIS = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
TRAMOS = {"2025": AZUL, "2026": NARANJA, "vivo": AGUA}
NOMBRE_TRAMO = {"2025": "2025 (validación)", "2026": "2026 (prueba)", "vivo": "En vivo (23-oct → 17-nov)"}
CANDIDATOS = [  # (modelo, base, etiqueta)
    ("c2linea_tp_cdd", "c2", "Chronos-2 + corrección en línea\n(grados sobre 23 °C)"),
    ("c2fija_tp_cdd", "c2", "Chronos-2 + corrección fija\n(errores zero-shot 2016–2024)"),
    ("c2cdd", "c2", "Chronos-2 reajustado con\nlos grados como covariable"),
    ("xgb_s_tobs", "xgb_s", "XGBoost + Simons + temperatura\n(frente a XGBoost + Simons)"),
    ("comb_tmix", "c2", "Combinación con el XGBoost\ncon temperatura"),
]


def _estilo(ax):
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(REJILLA)
    ax.tick_params(colors=TEXTO2, labelsize=9)
    ax.grid(axis="y", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)


def _figura(*args, **kw):
    fig, ax = plt.subplots(*args, **kw)
    fig.patch.set_facecolor(SUPERFICIE)
    return fig, ax


def pico_dias_calidos(comp, destino):
    """Δ del error absoluto del pico, Centro a 24 h, en el 10 % y 20 % de días más cálidos, con IC por semanas."""
    sel = comp[(comp["area"] == "CENTRO") & (comp["horizonte"] == "24h")]
    filas = []
    for modelo, base, etiqueta in CANDIDATOS:
        for sub in ("top10", "top20"):
            filas.append((modelo, base, sub, etiqueta))
    fig, ax = _figura(figsize=(9, 7.2))
    _estilo(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=REJILLA, linewidth=0.8)
    y, etiquetas, posiciones = 0, [], []
    for modelo, base, sub, etiqueta in filas:
        for k, (tramo, color) in enumerate(TRAMOS.items()):
            f = sel[(sel["modelo"] == modelo) & (sel["base"] == base) & (sel["subconjunto"] == sub)
                    & (sel["tramo"] == tramo)]
            if f.empty:
                continue
            f = f.iloc[0]
            yy = y + (k - 1) * 0.24
            ax.plot([f["d_error_pico_abs_bajo"], f["d_error_pico_abs_alto"]], [yy, yy], color=color, linewidth=2,
                    solid_capstyle="round")
            ax.plot(f["d_error_pico_abs"], yy, "o", color=color, markersize=8, markeredgecolor=SUPERFICIE,
                    markeredgewidth=2, label=NOMBRE_TRAMO[tramo] if y == 0 else None)
        etiquetas.append(f"{etiqueta.splitlines()[0]}\n{'10 %' if sub == 'top10' else '20 %'} más cálidos")
        posiciones.append(y)
        y += 1
    ax.axvline(0, color=TEXTO2, linewidth=1)
    ax.set_yticks(posiciones, etiquetas, fontsize=8.5, color=TEXTO)
    ax.invert_yaxis()
    ax.set_xlabel("Cambio en el error absoluto del pico diario (MW); negativo = mejora", color=TEXTO2, fontsize=9)
    ax.set_title("Pico del Centro a 24 h en los días más cálidos: cambio frente a la base, con IC 95 % por semanas",
                 color=TEXTO, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="lower left", labelcolor=TEXTO)
    fig.tight_layout()
    fig.savefig(destino / "1_pico_dias_calidos.png", dpi=150)
    plt.close(fig)


def vivo_pico(d, destino, temp_pron):
    """El tramo en vivo, día por día: pico real y pronosticado del Centro a 24 h, y la temperatura pronosticada."""
    x = d[(d["tramo"] == "vivo") & (d["area"] == "CENTRO") & (d["horizonte"] == "24h")]
    real = x[x["modelo"] == "c2"].set_index("dia")["real_max"]
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    fig.patch.set_facecolor(SUPERFICIE)
    for a in (ax, ax2):
        _estilo(a)
    ax.plot(real.index, real, color=TEXTO, linewidth=2, label="Real")
    series = [("c2", "Chronos-2 ajustado (en vivo)", AZUL), ("c2linea_tp_cdd", "Chronos-2 + corrección por calor",
                                                             NARANJA)]
    for m, nombre, color in series:
        s = x[x["modelo"] == m].set_index("dia")["pred_max"]
        ax.plot(s.index, s, color=color, linewidth=2, marker="o", markersize=4, label=nombre)
    ax.set_ylabel("Pico diario (MW)", color=TEXTO2, fontsize=9)
    ax.legend(frameon=False, fontsize=9, loc="upper left", labelcolor=TEXTO)
    ax.set_title("Centro a 24 h en vivo: el pico de cada día", color=TEXTO, fontsize=11, loc="left")
    t = temp_pron.reindex(real.index)
    ax2.plot(t.index, t, color=AGUA, linewidth=2, label="Media diaria pronosticada en Lima (GFS, nivel ERA5)")
    ax2.axhline(c.UMBRAL["centro"], color=TEXTO2, linewidth=1, linestyle="--")
    ax2.text(real.index[0], c.UMBRAL["centro"] + 0.1, "umbral 23 °C", color=TEXTO2, fontsize=8, va="bottom")
    ax2.set_ylabel("°C", color=TEXTO2, fontsize=9)
    ax2.legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=TEXTO)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    fig.tight_layout()
    fig.savefig(destino / "2_vivo_pico_diario.png", dpi=150)
    plt.close(fig)


def temperatura(destino):
    """Lima: media diaria ERA5 y la pronosticada (desfase 2, GFS llevado al nivel de ERA5), 2024 → noviembre 2026."""
    era5 = c.era5_horaria()
    pron = c.pronostico_ajustado(era5=era5)
    obs = c.diarias(era5)["centro"]["media"]
    p2 = c.diarias(pron[2])["centro"]["media"]
    desde = pd.Timestamp("2024-01-01")
    fig, ax = _figura(figsize=(9, 4.2))
    _estilo(ax)
    o, p = obs[obs.index >= desde], p2[p2.index >= desde]
    ax.plot(o.index, o.rolling(3, center=True, min_periods=1).mean(), color=AZUL, linewidth=1.6,
            label="ERA5 (observada del proyecto)")
    ax.plot(p.index, p.rolling(3, center=True, min_periods=1).mean(), color=NARANJA, linewidth=1.6,
            label="Pronosticada con 2 días de antelación")
    ax.axhline(c.UMBRAL["centro"], color=TEXTO2, linewidth=1, linestyle="--")
    ax.text(desde, c.UMBRAL["centro"] + 0.15, "umbral de enfriamiento: 23 °C (estimado con 2016–2024)", color=TEXTO2,
            fontsize=8, va="bottom")
    for x0, x1, nombre in (("2025-01-01", "2026-01-01", "validación"), ("2026-01-01", "2026-10-23", "prueba")):
        ax.axvspan(pd.Timestamp(x0), pd.Timestamp(x1), color=REJILLA, alpha=0.35 if nombre == "validación" else 0.15,
                   linewidth=0)
    ax.set_ylabel("Media diaria en Lima (°C, media móvil de 3 días)", color=TEXTO2, fontsize=9)
    ax.set_title("Lima: temperatura observada y pronosticada", color=TEXTO, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper center", labelcolor=TEXTO, ncol=2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    fig.tight_layout()
    fig.savefig(destino / "3_temperatura_lima.png", dpi=150)
    plt.close(fig)


def contrapartida(d, destino):
    """El precio de la corrección: error con signo del pico y sesgo del día en el 20 % más cálido, antes y después."""
    x = d[(d["area"] == "CENTRO") & (d["horizonte"] == "24h") & d["modelo"].isin(["c2", "c2linea_tp_cdd"])]
    x = x[x["top20"] | (x["tramo"] == "vivo")]
    tabla = x.groupby(["tramo", "modelo"])[["error_pico", "sesgo", "mae"]].mean()
    fig, ejes = plt.subplots(1, 3, figsize=(10, 3.9), sharey=False)
    fig.patch.set_facecolor(SUPERFICIE)
    nombres = {"error_pico": "Error con signo del pico (MW)", "sesgo": "Sesgo del día (MW)", "mae": "MAE del día (MW)"}
    ancho = 0.36
    for ax, metrica in zip(ejes, nombres, strict=True):
        _estilo(ax)
        for k, (m, nombre, color) in enumerate((("c2", "Chronos-2 ajustado", AZUL),
                                                ("c2linea_tp_cdd", "+ corrección por calor", NARANJA))):
            valores = [tabla.loc[(t, m), metrica] for t in TRAMOS]
            pos = np.arange(len(TRAMOS)) + (k - 0.5) * ancho
            ax.bar(pos, valores, width=ancho - 0.04, color=color, label=nombre)
            for xx, v in zip(pos, valores, strict=True):
                ax.text(xx, v + (2 if v >= 0 else -2), f"{v:+.0f}" if metrica != "mae" else f"{v:.0f}",
                        ha="center", va="bottom" if v >= 0 else "top", fontsize=7.5, color=TEXTO)
        ax.axhline(0, color=TEXTO2, linewidth=1)
        ax.set_xticks(np.arange(len(TRAMOS)), ["2025", "2026", "En vivo"], fontsize=9, color=TEXTO)
        ax.set_title(nombres[metrica], color=TEXTO, fontsize=9.5, loc="left")
    ejes[0].legend(frameon=False, fontsize=8.5, loc="lower left", labelcolor=TEXTO)
    fig.suptitle("Centro a 24 h, 20 % de días más cálidos (en vivo, todos): la corrección acerca el pico y sube el día",
                 color=TEXTO, fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(destino / "4_contrapartida.png", dpi=150)
    plt.close(fig)


def main(destino):
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    comp = pd.read_csv(c.SALIDA / "comparacion.csv")
    d = pd.read_parquet(c.SALIDA / "diario.parquet")
    pron = c.pronostico_ajustado()
    tp2 = c.diarias(pron[2])["centro"]["media"]
    pico_dias_calidos(comp, destino)
    vivo_pico(d, destino, tp2)
    temperatura(destino)
    contrapartida(d, destino)
    print("gráficos en", destino)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else c.SALIDA / "graficos")
