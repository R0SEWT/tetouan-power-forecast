"""Lo que la app muestra del pronóstico en vivo: lee el registro y el seguimiento de la tubería diaria.

La tubería (``python -m tetouan_power_forecast.en_vivo diario``) escribe en ``reportes/sein/en_vivo/`` de la carpeta
de datos. Aquí solo se leen esos archivos, sin modelo ni red; se vuelven a leer cuando cambian.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tetouan_power_forecast.en_vivo import GRUPOS, PASO, rutas

from .contrato import FORMATO_FECHA_HORA, DiaEnVivo, EnVivo, PerfilEnVivo, ResumenEnVivo

NOMBRES = {"chronos2ftcal": "Chronos-2 ajustado con feriados"}


def _fecha(valor) -> str:
    return pd.Timestamp(valor).strftime("%Y-%m-%d")


def _hora(valor) -> str:
    return pd.Timestamp(valor).strftime(FORMATO_FECHA_HORA)


class LectorEnVivo:
    """Lee los archivos de la tubería en vivo de una carpeta (por defecto, la de ``TETOUAN_DATA``)."""

    def __init__(self, carpeta: Path | None = None):
        self.carpeta = Path(carpeta) if carpeta is not None else rutas().reportes
        self._cache: dict[str, tuple[float, pd.DataFrame]] = {}

    def _leer(self, nombre: str) -> pd.DataFrame | None:
        ruta = self.carpeta / nombre
        if not ruta.exists():
            return None
        marca = ruta.stat().st_mtime
        if nombre not in self._cache or self._cache[nombre][0] != marca:
            self._cache[nombre] = (marca, pd.read_parquet(ruta))
        return self._cache[nombre][1]

    def area(self, area: str) -> EnVivo:
        registro = self._leer("pronosticos.parquet")
        if registro is None or registro.empty:
            return EnVivo(area=area)
        codigo = area.upper()
        propio = registro[registro["area"] == codigo]
        if propio.empty:
            return EnVivo(area=area)
        # El modelo y la versión de la última emisión; lo demás se muestra solo de ellos
        ultima = propio.loc[propio["emitido_en"].idxmax()]
        modelo, version = ultima["modelo"], ultima["version_pesos"]
        propio = propio[(propio["modelo"] == modelo) & (propio["version_pesos"] == version)]
        seguimiento = self._leer("seguimiento.parquet")
        if seguimiento is not None and not seguimiento.empty:
            seguimiento = seguimiento[(seguimiento["area"] == codigo) & (seguimiento["modelo"] == modelo)
                                      & (seguimiento["version_pesos"] == version)]
        resumen = self._leer("resumen.parquet")
        if resumen is not None and not resumen.empty:
            resumen = resumen[(resumen["area"] == codigo) & (resumen["modelo"] == modelo)
                              & (resumen["version_pesos"] == version)]
        a24 = propio[propio["horizonte"] == "24h"]
        dias_vivo = sorted(a24.loc[a24["tipo"].isin(GRUPOS["en_vivo"]), "fecha_objetivo"].unique())
        dias_reconstruidos = a24.loc[a24["tipo"] == "reconstruido", "fecha_objetivo"].nunique()
        return EnVivo(
            area=area,
            modelo=NOMBRES.get(modelo, modelo),
            version_pesos=version,
            ultimo=self._ultimo(a24, seguimiento),
            verificado=self._verificado(resumen),
            resumen=self._resumen(resumen),
            dias_en_vivo=len(dias_vivo),
            primer_dia_en_vivo=_fecha(dias_vivo[0]) if dias_vivo else None,
            dias_reconstruidos=int(dias_reconstruidos),
        )

    @staticmethod
    def _ultimo(a24: pd.DataFrame, seguimiento: pd.DataFrame | None) -> PerfilEnVivo | None:
        if a24.empty:
            return None
        dia = a24[a24["fecha_objetivo"] == a24["fecha_objetivo"].max()].sort_values("objetivo")
        real = pd.Series(dtype=float)
        if seguimiento is not None and not seguimiento.empty:
            real = seguimiento[seguimiento["horizonte"] == "24h"].set_index("objetivo")["real"]
        reales = real.reindex(dia["objetivo"]).to_numpy()
        emitido = pd.Timestamp(dia["emitido_en"].max())
        return PerfilEnVivo(
            fecha=_fecha(dia["fecha_objetivo"].iloc[0]),
            horizonte="24h",
            emitido_en=emitido.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
            emitido_lima=emitido.tz_convert("America/Lima").strftime(FORMATO_FECHA_HORA),
            datos_hasta=_hora(dia["datos_hasta"].max()),
            fecha_hora=[_hora(t - PASO) for t in dia["objetivo"]],  # la API marca el inicio de cada periodo
            pronostico=[round(float(x), 1) for x in dia["pred"]],
            inferior=[round(float(x), 1) for x in dia["q10"]],
            superior=[round(float(x), 1) for x in dia["q90"]],
            real=[None if pd.isna(x) else round(float(x), 1) for x in reales],
            tipo=list(dia["tipo"]),
        )

    @staticmethod
    def _verificado(resumen: pd.DataFrame | None) -> list[DiaEnVivo]:
        if resumen is None or resumen.empty:
            return []
        dias = resumen[resumen["nivel"] == "dia"]
        ex_ante = dias[dias["grupo"] == "ex_ante_estricto"].set_index(["horizonte", "fecha"])["periodos"]
        salida = []
        for f in dias[dias["grupo"].isin(["en_vivo", "reconstruido"])].sort_values("fecha", ascending=False).itertuples():
            salida.append(DiaEnVivo(
                fecha=_fecha(f.fecha), horizonte=f.horizonte, tipo=f.grupo, periodos=int(f.periodos),
                periodos_ex_ante=int(ex_ante.get((f.horizonte, f.fecha), 0)) if f.grupo == "en_vivo" else 0,
                mae_modelo=round(f.mae_modelo, 1), mae_referencia=round(f.mae_referencia, 1),
                referencia_nombre=f.referencia, cobertura_pct=round(f.cobertura_pct, 1),
            ))
        return salida

    @staticmethod
    def _resumen(resumen: pd.DataFrame | None) -> list[ResumenEnVivo]:
        if resumen is None or resumen.empty:
            return []
        acumulado = resumen[resumen["nivel"] == "acumulado"].sort_values(["horizonte", "grupo"], ascending=[False, True])
        return [ResumenEnVivo(
            grupo=f.grupo, horizonte=f.horizonte, desde=_fecha(f.desde), hasta=_fecha(f.hasta), dias=int(f.dias),
            periodos=int(f.periodos), mae_modelo=round(f.mae_modelo, 1), mae_referencia=round(f.mae_referencia, 1),
            referencia_nombre=f.referencia, sesgo=round(f.sesgo, 1), cobertura_pct=round(f.cobertura_pct, 1),
        ) for f in acumulado.itertuples()]
