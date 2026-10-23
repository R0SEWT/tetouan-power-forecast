"""La transferencia del 25-oct vista en la cuota de la Zona 1 dentro de Zona 1 + Zona 2 (docs/historico.md, opción 4).

Calcula la cuota diaria, el único punto de quiebre que mejor la parte (mínimos cuadrados), los días con
cambios en espejo entre las dos zonas y un detector simple de caídas de la cuota.
Uso: python -m experimentos.historico.cuota
"""

import numpy as np
import pandas as pd

from experimentos.historico import rolling as R

UMBRAL_ESPEJO = -0.9  # correlación diaria entre los cambios de ambas zonas frente al día anterior
UMBRAL_DETECTOR = -2.5  # desviaciones de la cuota diaria frente a las 4 semanas anteriores


def cuota_diaria(df):
    diario = df.set_index("DateTime")[[R.ZC[1], R.ZC[2]]].resample("D").mean()
    return diario[R.ZC[1]] / diario.sum(axis=1)


def quiebre_minimos_cuadrados(serie):
    """El día que, al partir la serie en dos tramos de media constante, deja el menor error cuadrático."""
    x = serie.to_numpy()
    errores = [((x[:k] - x[:k].mean()) ** 2).sum() + ((x[k:] - x[k:].mean()) ** 2).sum()
               for k in range(7, len(x) - 7)]
    k = 7 + int(np.argmin(errores))
    return serie.index[k], x[:k].mean(), x[k:].mean()


def dias_en_espejo(df):
    """Correlación, día por día, entre el cambio de la Zona 1 y el de la Zona 2 frente al día anterior."""
    s = df.set_index("DateTime")[[R.ZC[1], R.ZC[2]]]
    cambio = (s - s.shift(R.DAY)).dropna()
    return cambio.groupby(cambio.index.normalize()).apply(lambda d: d[R.ZC[1]].corr(d[R.ZC[2]]))


def detector(cuota):
    """Cuota de cada día frente a la media y la desviación de las 4 semanas anteriores."""
    historia = cuota.shift(1).rolling(28)
    return (cuota - historia.mean()) / historia.std()


def main():
    df = R.base_frame()
    cuota = cuota_diaria(df)
    dia, antes, despues = quiebre_minimos_cuadrados(cuota)
    semanal = cuota.resample("W").mean()
    corte = pd.Timestamp("2017-10-25")
    espejo = dias_en_espejo(df)
    z = detector(cuota)
    print(f"Quiebre por mínimos cuadrados: {dia:%d-%b} (cuota media {antes:.3f} antes, {despues:.3f} después)")
    print(f"Cuota semanal antes del 25-oct: {semanal[semanal.index < corte].min():.3f} a "
          f"{semanal[semanal.index < corte].max():.3f}")
    despues_completas = semanal[semanal.index - pd.Timedelta(days=6) >= corte]  # semanas enteras después
    print(f"Cuota semanal desde el 25-oct (semanas completas): {despues_completas.min():.3f} a "
          f"{despues_completas.max():.3f}")
    diario = df.set_index("DateTime")[[R.ZC[1], R.ZC[2]]].resample("D").mean()
    diario["suma"] = diario.sum(axis=1)
    abril = diario.loc["2017-04-20"] / diario.loc["2017-04-13"] - 1  # frente al mismo día de la semana anterior
    print("20-abr frente al 13-abr:", {k: f"{v:+.1%}" for k, v in abril.items()})
    print("Días en espejo (correlación < -0.9):", [f"{d:%d-%b}" for d in espejo[espejo < UMBRAL_ESPEJO].index])
    print("Días que marca el detector (< -2.5 desviaciones):", [f"{d:%d-%b}" for d in z[z < UMBRAL_DETECTOR].index])
    R.guardar(pd.DataFrame({"cuota": cuota, "correlacion_espejo": espejo, "detector_z": z})
              .rename_axis("fecha").reset_index(), "resultados_cuota.csv")


if __name__ == "__main__":
    main()
