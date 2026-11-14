"""Lo que la app muestra del pronóstico en vivo: lee el registro y el seguimiento de la tubería diaria.

La tubería (``python -m tetouan_power_forecast.en_vivo diario``) escribe en ``reportes/sein/en_vivo/`` de la carpeta
de datos. Aquí solo se leen esos archivos, sin modelo ni red; se vuelven a leer cuando cambian.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tetouan_power_forecast.en_vivo import GRUPOS, LIMA, PASO, es_paralelo, rutas

from .ahora import armar_ahora
from .ahora import dias_pico as calcular_dias_pico
from .contrato import (
    FORMATO_FECHA_HORA,
    Ahora,
    CifraAhora,
    DiaEnVivo,
    DiaPico,
    EnVivo,
    PerfilEnVivo,
    ResumenEnVivo,
)

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

    def _propio(self, area: str):
        """Las filas del área del modelo y la versión de la última emisión (lo demás no se mezcla), o None.

        Los modelos en paralelo (como «chronos2ftcal+rango») se registran para compararlos en vivo; no se muestran.
        """
        registro = self._leer("pronosticos.parquet")
        if registro is None or registro.empty:
            return None
        codigo = area.upper()
        propio = registro[(registro["area"] == codigo) & ~registro["modelo"].map(es_paralelo).astype(bool)]
        if propio.empty:
            return None
        ultima = propio.loc[propio["emitido_en"].idxmax()]
        modelo, version = ultima["modelo"], ultima["version_pesos"]
        propio = propio[(propio["modelo"] == modelo) & (propio["version_pesos"] == version)]

        def filtrar(nombre):
            tabla = self._leer(nombre)
            if tabla is None or tabla.empty:
                return tabla
            return tabla[(tabla["area"] == codigo) & (tabla["modelo"] == modelo) & (tabla["version_pesos"] == version)]

        return propio, modelo, version, filtrar("seguimiento.parquet"), filtrar("resumen.parquet")

    def area(self, area: str) -> EnVivo:
        datos = self._propio(area)
        if datos is None:
            return EnVivo(area=area)
        propio, modelo, version, seguimiento, resumen = datos
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

    # ---- «Ahora» y «Confianza» con el registro --------------------------------------------------------------------

    @staticmethod
    def _reales(seguimiento: pd.DataFrame | None) -> pd.Series:
        """El real de cada periodo verificado, indexado por su final (como el registro)."""
        if seguimiento is None or seguimiento.empty:
            return pd.Series(dtype=float)
        real = seguimiento.dropna(subset=["real"]).drop_duplicates("objetivo").set_index("objetivo")["real"]
        return real.sort_index().astype(float)

    @staticmethod
    def _mejor_referencia(resumen: pd.DataFrame | None) -> str:
        """La mejor referencia a 24 h del acumulado en vivo (o del reconstruido, si aún no hay días en vivo)."""
        if resumen is not None and not resumen.empty:
            acumulado = resumen[(resumen["nivel"] == "acumulado") & (resumen["horizonte"] == "24h")]
            for grupo in ("en_vivo", "reconstruido"):
                fila = acumulado[acumulado["grupo"] == grupo]
                if not fila.empty:
                    return str(fila["referencia"].iloc[0])
        return "semana_pasada"

    def tramo_repaso(self, area: str) -> tuple[str, str] | None:
        """El primer y el último día que se pueden repasar con el registro: con real y con el pronóstico de 24 h."""
        datos = self._propio(area)
        if datos is None:
            return None
        propio, _, _, seguimiento, _ = datos
        real = self._reales(seguimiento)
        a24 = propio[propio["horizonte"] == "24h"]
        if real.empty or a24.empty:
            return None
        primero = max(a24["objetivo"].min(), real.index.min()) - PASO
        return _fecha(primero), _fecha(real.index.max() - PASO)

    def ahora(self, area: str, origen: pd.Timestamp | None = None, reloj: pd.Timestamp | None = None,
              umbral: float | None = None) -> Ahora | None:
        """«Ahora» con el registro. Sin ``origen``, en vivo: el origen es el último real y ``reloj`` (por defecto, la
        hora de Lima) marca «ahora» dentro del pronóstico. Con ``origen``, el repaso de ese momento del tramo en vivo.

        Devuelve None si el registro no cubre la ventana (sin datos, o un origen fuera del tramo).
        """
        datos = self._propio(area)
        if datos is None:
            return None
        propio, modelo, _, seguimiento, resumen = datos
        real = self._reales(seguimiento)
        a24 = propio[propio["horizonte"] == "24h"].drop_duplicates("objetivo").set_index("objetivo").sort_index()
        a1 = propio[propio["horizonte"] == "1h"].drop_duplicates("origen").set_index("origen").sort_index()
        if real.empty or a24.empty:
            return None
        ultimo = real.index.max() - PASO  # inicio del último periodo con real
        en_vivo = origen is None
        origen = ultimo if en_vivo else pd.Timestamp(origen)
        if origen > ultimo:
            return None
        inicios = pd.date_range(origen.normalize(), origen + pd.Timedelta(days=1), freq="30min")
        finales = inicios + PASO
        filas = a24.reindex(finales)
        if filas["pred"].isna().any():
            return None
        i_origen = int(inicios.get_loc(origen))
        nombre_ref = self._mejor_referencia(resumen)
        atras = pd.Timedelta(days=7 if nombre_ref == "semana_pasada" else 1)
        avisos, i_ahora, en_1h, emitido = [], i_origen, None, None
        if en_vivo:
            emitido = pd.Timestamp(filas["emitido_en"].max()).tz_convert(LIMA).strftime(FORMATO_FECHA_HORA)
            if reloj is None:
                reloj = pd.Timestamp.now(tz=LIMA).tz_localize(None)
            reloj = pd.Timestamp(reloj).floor("30min")
            if inicios[i_origen] < reloj <= inicios[-1]:
                i_ahora = int(inicios.get_loc(reloj))
            elif reloj > inicios[-1]:
                avisos.append(f"Todavía no llega la demanda del {_fecha(inicios[-1])} del COES (suele publicarse "
                              "hacia las 09:45): se muestra el último pronóstico emitido.")
        else:
            fila = a1.reindex([origen + PASO])  # el registro marca el origen por el final del último periodo
            if fila["pred"].notna().all():
                f = fila.iloc[0]
                en_1h = CifraAhora(fecha_hora=_hora(origen + 2 * PASO), valor=round(float(f["pred"]), 1),
                                   fuente="pronostico_1h", inferior=round(float(f["q10"]), 1),
                                   superior=round(float(f["q90"]), 1))
        return armar_ahora(
            area=area, modo="en_vivo" if en_vivo else "repaso", modelo=f"en_vivo:{modelo}",
            modelo_nombre=NOMBRES.get(modelo, modelo), nivel=80, inicios=inicios, i_origen=i_origen, i_ahora=i_ahora,
            pred=filas["pred"].to_numpy(), inferior=filas["q10"].to_numpy(), superior=filas["q90"].to_numpy(),
            real=real.reindex(finales).to_numpy(), referencia=real.reindex(finales - atras).to_numpy(),
            referencia_nombre=nombre_ref, tipo=list(filas["tipo"]), en_1h=en_1h, umbral=umbral, emitido_en=emitido,
            avisos=avisos)

    def dias_pico(self, area: str) -> list[DiaPico]:
        """El día a día del pico con el registro a 24 h: los días con sus 48 reales."""
        datos = self._propio(area)
        if datos is None:
            return []
        propio, _, _, seguimiento, _ = datos
        real = self._reales(seguimiento)
        a24 = propio[propio["horizonte"] == "24h"].drop_duplicates("objetivo").set_index("objetivo").sort_index()
        if real.empty or a24.empty:
            return []
        dias = sorted({(t - PASO).normalize() for t in a24.index})
        finales = [pd.date_range(d + PASO, periods=48, freq="30min") for d in dias]
        pred = [a24["pred"].reindex(f).to_numpy() for f in finales]
        reales = [real.reindex(f).to_numpy() for f in finales]
        return calcular_dias_pico([d.date() for d in dias], pred, reales)
