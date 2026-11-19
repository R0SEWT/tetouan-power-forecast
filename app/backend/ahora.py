"""«Ahora» y «Confianza»: las dos pantallas de entrada, armadas con lo que ya calcula cada pronosticador.

**Ahora.** Un solo gráfico desde las 00:00 del día del origen hasta 24 h después del origen, más la fila de cifras.
El origen es el inicio del último periodo con dato real. Cada periodo lleva su pronóstico directo a 24 h, emitido 24 h
antes de ese periodo: los anteriores al origen se comparan con lo real y los siguientes ya estaban emitidos en el
origen, igual que en ``/pico`` (de donde salen el pico y la mayor subida, con la misma función).

Dos fuentes:

- el historial de un modelo (``repaso``): ``serie`` del día del origen hasta el origen y ``pronosticar`` a 24 h desde
  el origen; «en 1 hora» es el pronóstico a 1 h desde el origen;
- el registro de la tubería diaria (``LectorEnVivo.ahora``): el último pronóstico emitido o, en repaso, cualquier
  momento del tramo en vivo.

**Confianza.** El día a día del pico, el sesgo, el MAPE y el WAPE de 2026, con la serie del día de cada modelo.
La causa probable de un día fallido sale solo del calendario de feriados de Perú, y se dice que es probable.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from .contrato import (
    FORMATO_FECHA_HORA,
    Ahora,
    AyerParaEstaHora,
    CifraAhora,
    DiaPico,
    ErrorTramo,
    Escenario,
    Intervalo,
    Pronostico,
    Sesgo,
    Variante,
)
from .pico import pico_rampa

PERIODOS_DIA = 48
MEDIA_HORA = pd.Timedelta(minutes=30)
INICIO_PRUEBA = date(2026, 1, 1)
UMBRAL_PICO_PCT = 3.0
NIVEL_HISTORIAL = 90  # el rango de los modelos de la app: cuantiles 5 y 95 %
MOTIVO_MANANA_EN_VIVO = ("El pronóstico de mañana se emite cuando el COES publique la demanda de hoy, mañana hacia "
                         "las 10:00.")


def _texto(t) -> str:
    return pd.Timestamp(t).strftime(FORMATO_FECHA_HORA)


def _o_nulo(x) -> float | None:
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 1)


def _mae(real: np.ndarray, otro: np.ndarray) -> tuple[float | None, int]:
    bien = np.isfinite(real) & np.isfinite(otro)
    if not bien.any():
        return None, 0
    return round(float(np.abs(real[bien] - otro[bien]).mean()), 1), int(bien.sum())


def _tramo(inicios: pd.DatetimeIndex, a: int, b: int, real, pred, ref) -> ErrorTramo | None:
    """Error medio de los periodos ``a`` a ``b`` (inclusive) que tienen real."""
    sl = slice(a, b + 1)
    mae_m, n = _mae(real[sl], pred[sl])
    if mae_m is None:
        return None
    mae_r, _ = _mae(real[sl], ref[sl])
    return ErrorTramo(desde=_texto(inicios[a]), hasta=_texto(inicios[b]), periodos=n, mae_modelo=mae_m,
                      mae_referencia=mae_r)


def armar_ahora(*, area: str, modo: str, modelo: str, modelo_nombre: str, nivel: int, inicios: pd.DatetimeIndex,
                i_origen: int, i_ahora: int, pred, inferior, superior, real, referencia, referencia_nombre: str,
                tipo: list[str] | None = None, fuente_ayer: str = "historial", en_1h: CifraAhora | None = None,
                futuro: Pronostico | None = None, umbral: float | None = None, emitido_en: str | None = None,
                avisos: list[str] | None = None, error_dia: ErrorTramo | None = None) -> Ahora:
    """Arma la respuesta a partir de la ventana ya alineada (un valor por periodo, NaN si falta).

    ``real`` trae todo lo que se conoce, también después del origen: en repaso va a ``real_despues``. ``futuro`` es el
    pronóstico a 24 h desde el origen tal como lo devuelve ``pronosticar`` (si no se da, se arma con la ventana).
    """
    pred, inferior, superior = (np.asarray(x, dtype=float) for x in (pred, inferior, superior))
    real, referencia = np.asarray(real, dtype=float), np.asarray(referencia, dtype=float)
    n = len(inicios)
    antes = np.arange(n) <= i_origen
    real_hasta = np.where(antes, real, np.nan)
    textos = [_texto(t) for t in inicios]

    if futuro is None:
        sl = slice(i_origen + 1, i_origen + 1 + PERIODOS_DIA)
        futuro = Pronostico(fecha_hora=textos[sl], pronostico=[round(float(x), 1) for x in pred[sl]],
                            referencia=[0.0] * len(textos[sl]), real=[None] * len(textos[sl]),
                            intervalo=Intervalo(inferior=[round(float(x), 1) for x in inferior[sl]],
                                                superior=[round(float(x), 1) for x in superior[sl]]),
                            frase="")
    pr = pico_rampa(futuro, umbral)

    def cifra(i: int, permitir_real: bool = True) -> CifraAhora:
        if permitir_real and i <= i_origen and np.isfinite(real[i]):
            return CifraAhora(fecha_hora=textos[i], valor=round(float(real[i]), 1), fuente="real")
        return CifraAhora(fecha_hora=textos[i], valor=round(float(pred[i]), 1), fuente="pronostico_24h",
                          inferior=round(float(inferior[i]), 1), superior=round(float(superior[i]), 1))

    cifra_ahora = cifra(i_ahora)
    if en_1h is None and i_ahora + 2 < n:
        en_1h = cifra(i_ahora + 2, permitir_real=False)
    manana, motivo = None, None
    if i_ahora + PERIODOS_DIA < n:
        manana = cifra(i_ahora + PERIODOS_DIA, permitir_real=False)
    else:
        motivo = MOTIVO_MANANA_EN_VIVO if modo == "en_vivo" else "Fuera de la ventana con pronóstico."

    # Lo que se dijo 24 h antes: para «ahora» si ya tiene real; si no (en vivo), para ayer a esta misma hora
    ayer = None
    for i in (i_ahora, i_ahora - PERIODOS_DIA):
        if 0 <= i <= i_origen and np.isfinite(real[i]) and np.isfinite(pred[i]):
            dif = float(pred[i] - real[i])
            ayer = AyerParaEstaHora(
                fecha_hora=textos[i], emitido=_texto(inicios[i] - pd.Timedelta(days=1)),
                pronostico=round(float(pred[i]), 1), inferior=round(float(inferior[i]), 1),
                superior=round(float(superior[i]), 1), real=round(float(real[i]), 1), diferencia=round(dif, 1),
                dentro=bool(inferior[i] <= real[i] <= superior[i]),
                fuente=(tipo[i] if tipo is not None else fuente_ayer))
            break

    # El día del origen: hasta el origen (lo que se sabía) y, en repaso, completo (ya pasó)
    dia0 = int(np.searchsorted(inicios, inicios[i_origen].normalize()))
    error_hasta = _tramo(inicios, dia0, i_origen, real_hasta, pred, referencia)
    if error_dia is None and modo == "repaso" and dia0 + PERIODOS_DIA <= n:
        error_dia = _tramo(inicios, dia0, dia0 + PERIODOS_DIA - 1, real, pred, referencia)

    return Ahora(
        area=area, modo=modo, modelo=modelo, modelo_nombre=modelo_nombre, nivel_rango_pct=nivel,
        origen=textos[i_origen], datos_hasta=_texto(inicios[i_origen] + MEDIA_HORA), ahora=textos[i_ahora],
        emitido_en=emitido_en, referencia_nombre=referencia_nombre, fecha_hora=textos,
        real=[_o_nulo(x) for x in real_hasta],
        real_despues=[None if a else _o_nulo(x) for a, x in zip(antes, real)] if modo == "repaso" else None,
        pronostico=[round(float(x), 1) for x in pred], inferior=[round(float(x), 1) for x in inferior],
        superior=[round(float(x), 1) for x in superior], referencia=[_o_nulo(x) for x in referencia], tipo=tipo,
        i_origen=i_origen, i_ahora=i_ahora, cifra_ahora=cifra_ahora, en_1h=en_1h, pico=pr.pico, rampa=pr.rampa,
        manana=manana, manana_motivo=motivo, ayer=ayer, error_hasta_origen=error_hasta, error_dia=error_dia,
        avisos=list(avisos or []),
    )


def desde_historial(p, area: str, origen: datetime, variante: Variante, *, modelo: str, modelo_nombre: str,
                    umbral: float | None = None, avisos: list[str] | None = None) -> Ahora:
    """Un momento del historial de un modelo: la serie del día hasta el origen y lo emitido a 24 h desde el origen."""
    serie = p.serie(area, origen.date(), "24h", variante)
    futuro = p.pronosticar(area, origen, "24h", variante, Escenario())
    una_hora = p.pronosticar(area, origen, "1h", variante, Escenario())
    i0 = serie.fecha_hora.index(origen.strftime(FORMATO_FECHA_HORA))
    sl = slice(0, i0 + 1)
    inicios = pd.DatetimeIndex([*serie.fecha_hora[sl], *futuro.fecha_hora])
    iv = serie.intervalo or Intervalo(inferior=serie.pronostico, superior=serie.pronostico)

    def nan(xs):
        return [np.nan if x is None else x for x in xs]

    en_1h = CifraAhora(fecha_hora=una_hora.fecha_hora[-1], valor=una_hora.pronostico[-1], fuente="pronostico_1h",
                       inferior=una_hora.intervalo.inferior[-1], superior=una_hora.intervalo.superior[-1])
    # El día completo se mide con la serie del día (cada periodo a 24 h), como «¿qué tan bueno es?» de la vista del área
    real_dia = np.array(nan(serie.real), dtype=float)
    error_dia = _tramo(pd.DatetimeIndex(serie.fecha_hora), 0, PERIODOS_DIA - 1, real_dia,
                       np.asarray(serie.pronostico, dtype=float), np.asarray(serie.referencia, dtype=float))
    resultado = armar_ahora(
        area=area, modo="repaso", modelo=modelo, modelo_nombre=modelo_nombre, nivel=NIVEL_HISTORIAL, inicios=inicios,
        i_origen=i0, i_ahora=i0, pred=[*serie.pronostico[sl], *futuro.pronostico],
        inferior=[*iv.inferior[sl], *futuro.intervalo.inferior], superior=[*iv.superior[sl], *futuro.intervalo.superior],
        real=nan([*serie.real[sl], *futuro.real]), referencia=[*serie.referencia[sl], *futuro.referencia],
        referencia_nombre=serie.referencia_nombre, en_1h=en_1h, futuro=futuro, umbral=umbral, avisos=avisos,
        error_dia=error_dia)
    if resultado.ayer is not None and serie.componentes:
        # La ficha del número: de qué piezas sale lo que se dijo para el origen
        piezas = [c.model_copy(update={"valores": [c.valores[i0]]}) for c in serie.componentes]
        resultado.ayer.componentes = piezas
    return resultado


# ---- Día a día del pico, con una causa probable sacada del calendario -------------------------------------------


def _calendario(desde: date, hasta: date) -> dict[date, str]:
    try:
        import holidays
    except ImportError:  # sin el extra app: no se infiere ninguna causa
        return {}
    return dict(holidays.country_holidays("PE", years=range(desde.year - 1, hasta.year + 2), language="es"))


def causas_probables(fechas: list[date]) -> dict[date, str]:
    """La causa que el calendario sugiere para cada día, si la hay: feriado, fin de semana largo o el día siguiente.

    Un fin de semana largo son tres o más días libres seguidos (sábados, domingos y feriados) con algún feriado.
    No se usan los días no laborables que el Gobierno decreta sobre la marcha: no están en el calendario.
    """
    if not fechas:
        return {}
    cal = _calendario(min(fechas), max(fechas))
    if not cal:
        return {}
    uno = timedelta(days=1)

    def libre(d: date) -> bool:
        return d.weekday() >= 5 or d in cal

    def tramo_largo(d: date) -> list[date] | None:
        if not libre(d):
            return None
        a, b = d, d
        while libre(a - uno):
            a -= uno
        while libre(b + uno):
            b += uno
        dias = [a + k * uno for k in range((b - a).days + 1)]
        return dias if len(dias) >= 3 and any(x in cal for x in dias) else None

    def nombre(d: date) -> str:
        return cal[d].replace("Todos Los Santos", "Todos los Santos")

    salida = {}
    for d in fechas:
        largo = tramo_largo(d)
        if d in cal:
            salida[d] = f"feriado ({nombre(d)}){', en un fin de semana largo' if largo else ''}"
        elif largo:
            feriado = next(x for x in largo if x in cal)
            salida[d] = f"fin de semana largo (feriado de {nombre(feriado)})"
        elif libre(d - uno) and (d - uno in cal or tramo_largo(d - uno)):
            antes = tramo_largo(d - uno)
            previo = next(x for x in antes if x in cal) if antes else d - uno
            salida[d] = f"día siguiente a un {'fin de semana largo' if antes else 'feriado'} ({nombre(previo)})"
    return salida


def dias_pico(fechas: list[date], pred: np.ndarray, real: np.ndarray) -> list[DiaPico]:
    """Una fila por día con sus 48 reales: el pico real y el pronosticado (cada uno a su hora), con signo."""
    pred, real = np.asarray(pred, dtype=float), np.asarray(real, dtype=float)
    completos = [k for k in range(len(fechas)) if np.isfinite(real[k]).all() and np.isfinite(pred[k]).all()]
    causas = causas_probables([fechas[k] for k in completos])
    salida = []
    for k in completos:
        jr, jp = int(np.argmax(real[k])), int(np.argmax(pred[k]))
        pico_r, pico_p = float(real[k][jr]), float(pred[k][jp])
        salida.append(DiaPico(
            fecha=fechas[k].isoformat(), pico_real=round(pico_r, 1), hora_real=f"{jr // 2:02d}:{30 * (jr % 2):02d}",
            pico_pronostico=round(pico_p, 1), hora_pronostico=f"{jp // 2:02d}:{30 * (jp % 2):02d}",
            error_pct=round(100 * (pico_p - pico_r) / pico_r, 2), causa_probable=causas.get(fechas[k])))
    return salida


def metricas_confianza(p, area: str, horizonte: str, variante: Variante, fecha_max: date):
    """MAPE, WAPE y sesgo de 2026 con todas las medias horas, y el día a día del pico a 24 h, con ``serie``."""
    fechas = [INICIO_PRUEBA + timedelta(days=k) for k in range((fecha_max - INICIO_PRUEBA).days + 1)]
    pred24, real24, pred_h, real_h = [], [], [], []
    for f in fechas:
        s = p.serie(area, f, "24h", variante)
        real = np.array([np.nan if x is None else x for x in s.real], dtype=float)
        pred24.append(np.asarray(s.pronostico, dtype=float))
        real24.append(real)
        if horizonte != "24h":
            s = p.serie(area, f, horizonte, variante)
        pred_h.append(np.asarray(s.pronostico, dtype=float))
        real_h.append(np.array([np.nan if x is None else x for x in s.real], dtype=float))
    pred, real = np.concatenate(pred_h), np.concatenate(real_h)
    bien = np.isfinite(pred) & np.isfinite(real) & (real > 0)
    error = pred[bien] - real[bien]
    sesgo = Sesgo(periodos=int(bien.sum()), subestima_pct=round(100 * float((error < 0).mean()), 1),
                  sesgo_mw=round(float(error.mean()), 1))
    mape = round(100 * float(np.mean(np.abs(error) / real[bien])), 2)
    wape = round(100 * float(np.abs(error).sum() / real[bien].sum()), 2)
    return mape, wape, sesgo, dias_pico(fechas, np.array(pred24), np.array(real24))
