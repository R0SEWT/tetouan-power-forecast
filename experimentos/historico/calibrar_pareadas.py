"""Piloto de tamaño para el bootstrap circular centrado de una diferencia diaria."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DIAS = (55, 62)
BLOQUES = (1, 3, 7, 14)
RHO = (0.0, 0.3, 0.6, 0.8)
ALFA = 0.05


def series_nulas(dias, n, rho, innovacion, rng):
    """AR(1) centrado, descartando un calentamiento antes de la ventana."""
    calentamiento = 200
    forma = (n, dias + calentamiento)
    ruido = rng.normal(size=forma) if innovacion == "normal" else rng.standard_t(5, size=forma)
    for i in range(1, ruido.shape[1]):
        ruido[:, i] += rho * ruido[:, i - 1]
    return ruido[:, calentamiento:]


def pesos_circulares(dias, bloque, n, rng):
    """Frecuencia de cada día en una réplica de bloques consecutivos con retorno."""
    bloques = (dias + bloque - 1) // bloque
    comienzos = rng.integers(0, dias, size=(n, bloques, 1))
    indices = ((comienzos + np.arange(bloque)) % dias).reshape(n, -1)[:, :dias]
    pesos = np.zeros((n, dias))
    np.add.at(pesos, (np.arange(n)[:, None], indices), 1 / dias)
    return pesos


def simular(n, replicas, rng):
    filas = []
    for dias in DIAS:
        pesos = {largo: pesos_circulares(dias, largo, replicas, rng) for largo in BLOQUES}
        for innovacion in ("normal", "t5"):
            for rho in RHO:
                serie = series_nulas(dias, n, rho, innovacion, rng)
                observada = serie.mean(axis=1, keepdims=True)
                centrada = serie - observada
                for largo, frecuencia in pesos.items():
                    bootstrap = centrada @ frecuencia.T
                    extremos = (np.abs(bootstrap) >= np.abs(observada)).sum(axis=1)
                    p = (1 + extremos) / (replicas + 1)
                    tasa = np.mean(p <= ALFA)
                    filas.append({
                        "dias": dias, "innovacion": innovacion, "rho": rho, "bloque": largo,
                        "n_simulaciones": n, "n_replicas": replicas,
                        "tasa_rechazo": tasa,
                        "pasa_03_07": 0.03 <= tasa <= 0.07,
                    })
    return pd.DataFrame(filas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--simulaciones", type=int, default=2000)
    parser.add_argument("--replicas", type=int, default=1999)
    parser.add_argument("--semilla", type=int, default=20261123)
    parametros = parser.parse_args()
    if parametros.simulaciones < 1 or parametros.replicas < 1:
        parser.error("Las simulaciones y réplicas deben ser positivas")
    tabla = simular(
        parametros.simulaciones, parametros.replicas, np.random.default_rng(parametros.semilla),
    )
    parametros.salida.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(parametros.salida, index=False)
    resumen = tabla.groupby("bloque")["tasa_rechazo"].agg(["min", "median", "max"])
    print(resumen.join(tabla.groupby("bloque")["pasa_03_07"].sum()).to_string())


if __name__ == "__main__":
    main()
