"""El pronosticador detrás de la API y su versión de prueba con datos sintéticos.

La API solo conoce el ``Protocol`` ``Pronosticador``. Hoy lo cumple ``PronosticadorDePrueba``,
que genera en memoria tres series sintéticas (Norte, Centro y Sur) y pronostica con persistencia,
el ciclo diario y ruido. Cuando exista el modelo real, basta con otra clase que cumpla el mismo
``Protocol`` y pasarla a ``crear_app``.

Las validaciones del contrato (área, rango de fechas, escenarios a 1 h) las hace la API antes de
llamar al pronosticador, así que aquí las entradas llegan ya validadas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol, runtime_checkable

import numpy as np

from .contrato import (
    FECHA_MAX,
    FECHA_MIN,
    FORMATO_FECHA_HORA,
    IDS_AREAS,
    PASOS,
    Ablacion,
    Adaptacion,
    Diagnostico,
    Escenario,
    EstadoNino,
    Horizonte,
    Importancia,
    Intervalo,
    MaeRegimen,
    MetricaPrueba,
    Pronostico,
    Referencia,
    RegimenNino,
    Residuos,
    Resumen,
    Sensibilidad,
    Serie,
    VariableSensibilidad,
    Variante,
)


@runtime_checkable
class Pronosticador(Protocol):
    """Lo que la API necesita de un modelo. Las entradas llegan validadas."""

    modelo: str
    version_datos: str

    def resumen(self) -> Resumen: ...

    def serie(self, area: str, fecha: date, horizonte: Horizonte, variante: Variante) -> Serie: ...

    def pronosticar(
        self,
        area: str,
        origen: datetime,
        horizonte: Horizonte,
        variante: Variante,
        escenario: Escenario,
    ) -> Pronostico: ...

    def sensibilidad(
        self, area: str, origen: datetime, variable: VariableSensibilidad
    ) -> Sensibilidad: ...

    def diagnostico(self, area: str) -> Diagnostico: ...


# --------------------------------------------------------------------------------------------
# Frases en texto llano (las puede reutilizar el pronosticador real)
# --------------------------------------------------------------------------------------------

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip

NOMBRE_REFERENCIA: dict[str, str] = {
    "persistencia": "la persistencia (el último dato)",
    "ayer": "«ayer a la misma hora»",
    "semana_pasada": "«la semana pasada a la misma hora»",
}


def _mw(x: float) -> str:
    """MW con coma de miles, como se escribe en Perú: 4,512 MW."""
    return f"{x:,.0f} MW"


def _cuando(momento: datetime, con_dia: bool) -> str:
    hora = momento.strftime("%H:%M")
    if not con_dia:
        return f"a las {hora}"
    return f"a las {hora} del {momento.day} de {MESES[momento.month - 1]}"


def frase_base(
    momentos: list[datetime],
    pronostico: list[float],
    referencia: list[float],
    nombre_referencia: str,
    horizonte: Horizonte,
) -> str:
    """El pronóstico en la hora de mayor demanda frente a la mejor referencia."""
    if horizonte == "1h":
        p = len(pronostico) - 1
        inicio = f"{_cuando(momentos[p], con_dia=False).capitalize()}, dentro de 1 h,"
    else:
        p = int(np.argmax(pronostico))
        inicio = (
            f"{_cuando(momentos[p], con_dia=True).capitalize()}, "
            "la hora de mayor demanda de las próximas 24 h,"
        )
    diferencia = pronostico[p] - referencia[p]
    if abs(diferencia) < 1:
        comparacion = f"lo mismo que {nombre_referencia}"
    else:
        sentido = "más" if diferencia > 0 else "menos"
        comparacion = f"{_mw(abs(diferencia))} {sentido} que {nombre_referencia}"
    return f"{inicio} el modelo espera {_mw(pronostico[p])}: {comparacion}."


def describir_escenario(escenario: Escenario) -> str:
    """«hiciera 2 °C más de lo pronosticado, El Niño fuera neutro y no hubiera falla en curso»."""
    partes = []
    if escenario.delta_temp_c:
        sentido = "más" if escenario.delta_temp_c > 0 else "menos"
        partes.append(f"hiciera {abs(escenario.delta_temp_c)} °C {sentido} de lo pronosticado")
    if escenario.nino == "neutro":
        partes.append("El Niño fuera neutro")
    if escenario.falla == "ninguna":
        partes.append("no hubiera falla en curso")
    if len(partes) == 1:
        return partes[0]
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def frase_escenario(
    momentos: list[datetime],
    base: list[float],
    escenario_mw: list[float],
    escenario: Escenario,
) -> str:
    """El cambio del escenario frente a la base, en la hora de mayor demanda de la base."""
    p = int(np.argmax(base))
    cambio = np.asarray(escenario_mw) - np.asarray(base)
    inicio = f"Si {describir_escenario(escenario)}, {_cuando(momentos[p], con_dia=True)}"
    if abs(cambio[p]) < 1:
        frase = f"{inicio} (la hora de mayor demanda) la demanda casi no cambia: menos de 1 MW."
    else:
        sentido = "más" if cambio[p] > 0 else "menos"
        pct = 100 * cambio[p] / base[p]
        frase = (
            f"{inicio} (la hora de mayor demanda) el modelo espera {_mw(escenario_mw[p])}: "
            f"{_mw(abs(cambio[p]))} {sentido} que en el escenario base ({pct:+.1f} %)."
        )
    q = int(np.argmax(np.abs(cambio)))
    if q != p and abs(cambio[q]) >= 1 and abs(cambio[q]) > abs(cambio[p]) + 1:
        frase += f" El mayor cambio es {_cuando(momentos[q], con_dia=False)}: {cambio[q]:+,.0f} MW."
    return frase


FRASE_M0_SIN_ESCENARIOS = (
    "La variante M0 no usa clima, El Niño ni fallas, así que el escenario no cambia su "
    "pronóstico. Elige M3 para ver el efecto."
)


# --------------------------------------------------------------------------------------------
# Datos sintéticos
# --------------------------------------------------------------------------------------------

PASO = timedelta(minutes=30)
DIA = 48
SEMANA = 7 * DIA
INICIO = datetime(2024, 12, 1)  # margen para los rezagos de una semana antes de FECHA_MIN
FIN = datetime(2026, 11, 3)  # margen para los 48 pasos desde el último origen válido

# ICEN mensual sintético. Agosto de 2026 coincide con el dato real (3.98, extraordinario).
ICEN_MENSUAL = {
    "2024-09": -0.4, "2024-10": -0.3, "2024-11": -0.3, "2024-12": -0.2,
    "2025-01": -0.1, "2025-02": 0.1, "2025-03": 0.3, "2025-04": 0.2,
    "2025-05": 0.0, "2025-06": -0.1, "2025-07": 0.1, "2025-08": 0.2,
    "2025-09": 0.3, "2025-10": 0.3, "2025-11": 0.5, "2025-12": 0.7,
    "2026-01": 0.9, "2026-02": 1.2, "2026-03": 1.6, "2026-04": 2.1,
    "2026-05": 2.6, "2026-06": 3.1, "2026-07": 3.6, "2026-08": 3.98,
    "2026-09": 3.9, "2026-10": 3.8, "2026-11": 3.7,
}  # fmt: skip

FERIADOS = {(1, 1), (5, 1), (6, 29), (7, 28), (7, 29), (8, 30), (10, 8), (11, 1), (12, 8), (12, 25)}

GRUPOS: dict[str, frozenset[str]] = {
    "M0": frozenset(),
    "M1": frozenset({"clima"}),
    "M2": frozenset({"clima", "nino"}),
    "M3": frozenset({"clima", "nino", "fallas"}),
    "M4": frozenset({"clima", "nino", "fallas", "saidi"}),
    "M3_sin_clima": frozenset({"nino", "fallas"}),
    "M3_sin_nino": frozenset({"clima", "fallas"}),
    "M3_sin_fallas": frozenset({"clima", "nino"}),
}


def estado_nino(icen: float) -> EstadoNino:
    """Clasificación de ENFEN para el lado cálido del ICEN."""
    if icen > 3.0:
        return "extraordinario"
    if icen > 1.7:
        return "fuerte"
    if icen > 1.0:
        return "moderado"
    if icen > 0.4:
        return "debil"
    return "neutro"


@dataclass(frozen=True)
class _ParamsArea:
    nivel: float  # MW medios a inicios de 2025
    valle: float  # profundidad del valle de madrugada, en fracción del nivel
    mediodia: float  # pico del mediodía
    tarde: float  # pico de la tarde-noche
    sabado: float
    domingo: float  # también feriados
    temp_media: float  # °C
    temp_anual: float  # amplitud estacional, con el máximo a mediados de febrero
    temp_diaria: float  # amplitud del ciclo diario, con el máximo a las 14:30
    umbral_temp: float  # °C desde donde el calor sube la demanda
    coef_temp: float  # fracción de demanda por °C sobre el umbral
    coef_nino: float  # fracción por unidad de ICEN positivo: en el Norte, las lluvias la bajan
    anomalia_nino: float  # °C de anomalía por unidad de ICEN
    semilla: int


PARAMS: dict[str, _ParamsArea] = {
    "norte": _ParamsArea(1250, 0.16, 0.06, 0.10, 0.04, 0.09, 25.5, 3.0, 4.0, 26, 0.012, -0.008, 0.7, 11),
    "centro": _ParamsArea(4200, 0.20, 0.10, 0.07, 0.05, 0.12, 19.5, 3.8, 3.5, 22, 0.014, 0.004, 0.6, 22),
    "sur": _ParamsArea(1750, 0.05, 0.02, 0.03, 0.01, 0.02, 17.0, 2.5, 6.0, 24, 0.003, 0.0, 0.2, 33),
}  # fmt: skip

# Eventos fijos para la demo: un hueco y una falla en el Centro el 26 de febrero de 2026.
HUECOS_FIJOS = {"centro": [(datetime(2026, 2, 26, 8, 0), 4)]}
FALLAS_FIJAS = {"centro": [(datetime(2026, 2, 26, 13, 0), 8, 0.06)]}


def _indice(momento: datetime) -> int:
    return int((momento - INICIO) / PASO)


def _momento(i: int) -> datetime:
    return INICIO + int(i) * PASO


def _texto(i: int) -> str:
    return _momento(i).strftime(FORMATO_FECHA_HORA)


def _campana(h: np.ndarray, centro: float, ancho: float) -> np.ndarray:
    d = np.abs(h - centro)
    d = np.minimum(d, 24 - d)
    return np.exp(-0.5 * (d / ancho) ** 2)


def _ar1(rng: np.random.Generator, n: int, phi: float, sigma: float) -> np.ndarray:
    innov = rng.standard_normal(n) * sigma * np.sqrt(1 - phi**2)
    x = np.empty(n)
    x[0] = innov[0] / np.sqrt(1 - phi**2)
    for j in range(1, n):
        x[j] = phi * x[j - 1] + innov[j]
    return x


@dataclass
class _DatosArea:
    calendario: np.ndarray  # nivel x perfil diario x semana x tendencia: se conoce de antemano
    verdad: np.ndarray  # demanda "real" completa, sin huecos
    observado: np.ndarray  # lo publicado: NaN en los huecos y después de FECHA_MAX
    preliminar: np.ndarray
    temp: np.ndarray
    efecto_temp: np.ndarray
    efecto_nino: np.ndarray
    icen: np.ndarray  # ICEN del mes (ex post), para los regímenes
    falla: np.ndarray  # fracción de demanda perdida por fallas en curso
    z_modelo: np.ndarray
    z_temp: np.ndarray
    z_prog: np.ndarray
    params: _ParamsArea

    def efecto_temperatura(self, temp: np.ndarray | float) -> np.ndarray:
        p = self.params
        return p.coef_temp * np.maximum(np.asarray(temp) - p.umbral_temp, 0.0)

    def efecto_icen(self, icen: np.ndarray | float) -> np.ndarray:
        return self.params.coef_nino * np.maximum(np.asarray(icen, dtype=float), 0.0)


def _generar_area(nombre: str) -> _DatosArea:
    p = PARAMS[nombre]
    rng = np.random.default_rng(p.semilla)
    t64 = np.arange(np.datetime64(INICIO), np.datetime64(FIN), np.timedelta64(30, "m"))
    n = len(t64)
    dias64 = t64.astype("datetime64[D]")
    hora = (t64 - dias64).astype("timedelta64[m]").astype(int) / 60
    dow = (dias64.astype(int) + 3) % 7  # 1970-01-01 fue jueves; lunes = 0
    doy = (dias64 - t64.astype("datetime64[Y]")).astype(int)
    meses64 = t64.astype("datetime64[M]")
    mes_dia = [(int(m), int(d)) for m, d in zip(
        (meses64.astype(int) % 12) + 1,
        (dias64 - meses64.astype("datetime64[D]")).astype(int) + 1,
        strict=True,
    )]  # fmt: skip
    feriado = np.array([md in FERIADOS for md in mes_dia])

    perfil = (
        1
        - p.valle * _campana(hora, 4.5, 2.5)
        + p.mediodia * _campana(hora, 13.0, 2.5)
        + p.tarde * _campana(hora, 19.5, 1.8)
    )
    semana = 1 - p.sabado * (dow == 5) - p.domingo * ((dow == 6) | feriado)
    anios = (t64 - np.datetime64("2025-01-01")).astype("timedelta64[m]").astype(float) / 525_960
    calendario = p.nivel * perfil * semana * (1 + 0.03 * anios)

    icen_por_mes = {np.datetime64(k, "M"): v for k, v in ICEN_MENSUAL.items()}
    icen = np.array([icen_por_mes[m] for m in meses64])

    dias = n // DIA
    temp_dia = np.repeat(_ar1(rng, dias, 0.6, 1.5), DIA)[:n]
    temp = (
        p.temp_media
        + p.temp_anual * np.cos(2 * np.pi * (doy - 45) / 365.25)
        + p.temp_diaria * np.cos(2 * np.pi * (hora - 14.5) / 24)
        + p.anomalia_nino * np.maximum(icen, 0)
        + temp_dia
        + 0.3 * rng.standard_normal(n)
    )

    falla = np.zeros(n)
    i0, i1 = _indice(datetime.combine(FECHA_MIN, datetime.min.time())), n - SEMANA
    for _ in range(40):
        ini, dur, caida = rng.integers(i0, i1), rng.integers(2, 11), rng.uniform(0.02, 0.07)
        falla[ini : ini + dur] = np.maximum(falla[ini : ini + dur], caida)
    for momento, dur, caida in FALLAS_FIJAS.get(nombre, []):
        ini = _indice(momento)
        falla[ini : ini + dur] = caida

    efecto_temp = p.coef_temp * np.maximum(temp - p.umbral_temp, 0)
    efecto_nino = p.coef_nino * np.maximum(icen, 0)
    choque_dia = np.repeat(_ar1(rng, dias, 0.8, 0.02), DIA)[:n]  # carga industrial, eventos
    ruido = _ar1(rng, n, 0.95, 0.008)
    verdad = calendario * (1 + efecto_temp + efecto_nino + choque_dia) * (1 - falla) * (1 + ruido)

    observado = verdad.copy()
    for _ in range(10):
        ini, dur = rng.integers(i0, i1), rng.integers(2, 17)
        observado[ini : ini + dur] = np.nan
    for momento, dur in HUECOS_FIJOS.get(nombre, []):
        ini = _indice(momento)
        observado[ini : ini + dur] = np.nan
    fin_datos = _indice(datetime.combine(FECHA_MAX + timedelta(days=1), datetime.min.time()))
    observado[fin_datos:] = np.nan

    preliminar = np.zeros(n, dtype=bool)
    preliminar[fin_datos - 7 * DIA : fin_datos] = True  # la última semana aún no está validada
    for _ in range(5):
        ini, dur = rng.integers(i0, i1), rng.integers(6, 25)
        preliminar[ini : ini + dur] = True
    preliminar &= ~np.isnan(observado)

    return _DatosArea(
        calendario=calendario,
        verdad=verdad,
        observado=observado,
        preliminar=preliminar,
        temp=temp,
        efecto_temp=efecto_temp,
        efecto_nino=efecto_nino,
        icen=icen,
        falla=falla,
        z_modelo=rng.standard_normal(n),
        z_temp=rng.standard_normal(n),
        z_prog=rng.standard_normal(n),
        params=p,
    )


def _redondear(x: np.ndarray) -> list[float]:
    return [round(float(v), 1) for v in x]


def _con_nulos(x: np.ndarray) -> list[float | None]:
    return [None if np.isnan(v) else round(float(v), 1) for v in x]


# --------------------------------------------------------------------------------------------
# Pronosticador de prueba
# --------------------------------------------------------------------------------------------


class PronosticadorDePrueba:
    """Persistencia, ciclo diario y ruido sobre datos sintéticos generados en memoria.

    - M0 mezcla la persistencia (con peso que decae con el paso) con «ayer» y «la semana pasada»,
      corregidos por el calendario.
    - M3 suma lo que aportan el clima, El Niño y las fallas. A 1 h casi no los usa, porque la
      demanda reciente ya los contiene; a 24 h sí.
    - El diagnóstico se calcula a 24 h sobre la prueba de 2026. La adaptación (reentrenar) no
      se simula: sus factores son ilustrativos.
    """

    modelo = "prueba"
    version_datos = "sin-datos"

    def __init__(self) -> None:
        self._datos = {area: _generar_area(area) for area in sorted(IDS_AREAS)}
        self._mejor_referencia = {
            (area, h): self._elegir_referencia(area, h) for area in self._datos for h in PASOS
        }
        self._diagnosticos: dict[str, Diagnostico] = {}
        self._resumen: Resumen | None = None

    # ---- núcleo ----------------------------------------------------------------------------

    def _predecir(
        self,
        area: str,
        o: np.ndarray,
        k: np.ndarray,
        grupos: frozenset[str],
        *,
        delta_temp: float = 0.0,
        nino_neutro: bool = False,
        sin_falla: bool = False,
        temp_fija: float | None = None,
        icen_fijo: float | None = None,
    ) -> np.ndarray:
        """Pronóstico del periodo o + k emitido en el origen o (k en pasos de 30 min)."""
        d = self._datos[area]
        o, k = np.asarray(o), np.asarray(k)
        i = o + k
        cal = d.calendario
        demanda = d.verdad / (1 - d.falla) if sin_falla else d.verdad
        w = np.exp(-k / 6.0)

        def mezcla(x: np.ndarray) -> np.ndarray:
            return w * x[o] + (1 - w) * (0.85 * x[i - DIA] + 0.15 * x[i - SEMANA])

        pred = mezcla(demanda / cal) * cal[i]
        if grupos:
            peso = 0.85 * (1 - np.exp(-k / 12.0))  # a 1 h, la demanda reciente ya trae el clima
            cambio = np.zeros_like(pred)
            if "clima" in grupos:
                error_previsto = d.z_temp[i] * (0.2 + 0.5 * np.sqrt(k / DIA))
                temp = d.temp[i] + error_previsto + delta_temp
                if temp_fija is not None:
                    temp = np.full_like(pred, temp_fija)
                cambio += peso * (d.efecto_temperatura(temp) - mezcla(d.efecto_temp))
            if "nino" in grupos:
                objetivo = d.efecto_nino[i]
                if nino_neutro:
                    objetivo = np.zeros_like(pred)
                if icen_fijo is not None:
                    objetivo = np.full_like(pred, d.efecto_icen(icen_fijo))
                cambio += peso * (objetivo - mezcla(d.efecto_nino))
            pred = pred * (1 + cambio)
            if "fallas" in grupos and not sin_falla:
                # Sabe qué rezagos cayeron por una falla y que la falla en curso se recupera.
                pred = pred / (1 - mezcla(d.falla)) * (1 - d.falla[o] * np.exp(-k / 6.0))
        escala = 1.0 - 0.05 * len(grupos & {"clima", "nino", "fallas"}) + 0.01 * ("saidi" in grupos)
        return pred * (1 + escala * d.z_modelo[i] * self._sigma(k))

    @staticmethod
    def _sigma(k: np.ndarray) -> np.ndarray:
        return 0.002 + 0.004 * np.sqrt(np.asarray(k) / DIA)

    def _referencia(
        self, area: str, nombre: Referencia, o: np.ndarray, i: np.ndarray
    ) -> np.ndarray:
        v = self._datos[area].verdad
        if nombre == "persistencia":
            return v[o]
        return v[i - DIA] if nombre == "ayer" else v[i - SEMANA]

    def _elegir_referencia(self, area: str, horizonte: Horizonte) -> Referencia:
        """La referencia ingenua con menor MAE en la validación de 2025."""
        h = PASOS[horizonte]
        i = np.arange(_indice(datetime(2025, 1, 1)), _indice(datetime(2026, 1, 1)))
        v = self._datos[area].verdad
        candidatas: list[Referencia] = ["persistencia", "ayer", "semana_pasada"]
        if horizonte == "24h":
            candidatas = ["ayer", "semana_pasada"]  # a 24 h la persistencia es «ayer»
        mae = {c: np.mean(np.abs(v[i] - self._referencia(area, c, i - h, i))) for c in candidatas}
        return min(mae, key=mae.get)

    # ---- contrato ----------------------------------------------------------------------------

    def serie(self, area: str, fecha: date, horizonte: Horizonte, variante: Variante) -> Serie:
        d = self._datos[area]
        h = PASOS[horizonte]
        i = _indice(datetime.combine(fecha, datetime.min.time())) + np.arange(DIA)
        o = i - h
        pred = self._predecir(area, o, np.full_like(i, h), GRUPOS[variante])
        nombre_ref = self._mejor_referencia[(area, horizonte)]
        ref = self._referencia(area, nombre_ref, o, i)
        programacion = None
        if horizonte == "24h":
            programacion = _con_nulos(d.verdad[i] * (1 + 0.008 + 0.015 * d.z_prog[i]))
        real = d.observado[i]
        return Serie(
            fecha_hora=[_texto(j) for j in i],
            real=_con_nulos(real),
            pronostico=_redondear(pred),
            referencia=_redondear(ref),
            referencia_nombre=nombre_ref,
            programacion_diaria=programacion,
            hueco=[bool(x) for x in np.isnan(real)],
            preliminar=[bool(x) for x in d.preliminar[i]],
        )

    def pronosticar(
        self,
        area: str,
        origen: datetime,
        horizonte: Horizonte,
        variante: Variante,
        escenario: Escenario,
    ) -> Pronostico:
        d = self._datos[area]
        h = PASOS[horizonte]
        o0 = _indice(origen)
        k = np.arange(1, h + 1)
        o = np.full_like(k, o0)
        i = o0 + k
        grupos = GRUPOS[variante]
        base = self._predecir(area, o, k, grupos)
        pred = base
        if not escenario.es_base and grupos:
            pred = self._predecir(
                area,
                o,
                k,
                grupos,
                delta_temp=float(escenario.delta_temp_c),
                nino_neutro=escenario.nino == "neutro",
                sin_falla=escenario.falla == "ninguna",
            )
        nombre_ref = self._mejor_referencia[(area, horizonte)]
        ref = self._referencia(area, nombre_ref, o, i)
        escala = 1.0 - 0.05 * len(grupos & {"clima", "nino", "fallas"})
        ancho = 1.645 * np.hypot(escala * self._sigma(k), 0.006 + 0.02 * np.sqrt(k / DIA))
        momentos = [_momento(j) for j in i]

        if escenario.es_base:
            frase = frase_base(
                momentos, list(pred), list(ref), NOMBRE_REFERENCIA[nombre_ref], horizonte
            )
        elif not grupos:
            frase = FRASE_M0_SIN_ESCENARIOS
        else:
            frase = frase_escenario(momentos, list(base), list(pred), escenario)

        return Pronostico(
            fecha_hora=[_texto(j) for j in i],
            pronostico=_redondear(pred),
            referencia=_redondear(ref),
            real=_con_nulos(d.observado[i]),
            intervalo=Intervalo(
                inferior=_redondear(pred * (1 - ancho)), superior=_redondear(pred * (1 + ancho))
            ),
            frase=frase,
        )

    def sensibilidad(
        self, area: str, origen: datetime, variable: VariableSensibilidad
    ) -> Sensibilidad:
        d = self._datos[area]
        o0 = _indice(origen)
        k = PASOS["1h"]
        if variable == "temperatura":
            centro = round(float(d.temp[o0 + k]) * 2) / 2
            valores = centro + np.arange(-6.0, 6.5, 1.0)
            preds = [
                self._predecir(area, np.array([o0]), np.array([k]), GRUPOS["M3"], temp_fija=v)[0]
                for v in valores
            ]
        else:
            valores = np.arange(-1.5, 4.51, 0.5)
            preds = [
                self._predecir(area, np.array([o0]), np.array([k]), GRUPOS["M3"], icen_fijo=v)[0]
                for v in valores
            ]
        return Sensibilidad(
            valores=[round(float(v), 2) for v in valores], pronostico=_redondear(np.array(preds))
        )

    # ---- resumen y diagnóstico ----------------------------------------------------------------

    def _prueba(self, area: str) -> np.ndarray:
        """Índices de la prueba de 2026 con dato real."""
        d = self._datos[area]
        i = np.arange(_indice(datetime(2026, 1, 1)), _indice(datetime(2026, 11, 1)))
        return i[~np.isnan(d.observado[i])]

    def _errores_24h(self, area: str, i: np.ndarray, variante: str) -> np.ndarray:
        h = PASOS["24h"]
        pred = self._predecir(area, i - h, np.full_like(i, h), GRUPOS[variante])
        return np.abs(self._datos[area].observado[i] - pred)

    def resumen(self) -> Resumen:
        if self._resumen is None:
            metricas = {}
            for area, d in self._datos.items():
                i = self._prueba(area)
                err = self._errores_24h(area, i, "M3")
                metricas[area] = MetricaPrueba(
                    mae_mw=round(float(err.mean()), 1),
                    mape_pct=round(float(np.mean(err / d.observado[i]) * 100), 2),
                    mejor_referencia=self._mejor_referencia[(area, "24h")],
                )
            ultimo = FECHA_MAX
            publicado = (ultimo.year * 12 + ultimo.month - 1) - (2 if ultimo.day >= 20 else 3)
            mes = f"{publicado // 12}-{publicado % 12 + 1:02d}"
            icen = ICEN_MENSUAL[mes]
            self._resumen = Resumen(
                fechas_corte={
                    "entrenamiento_hasta": "2024-12-31",
                    "validacion_hasta": "2025-12-31",
                    "prueba_hasta": FECHA_MAX.isoformat(),
                    "demanda": FECHA_MAX.isoformat(),
                    "clima": (FECHA_MAX - timedelta(days=5)).isoformat(),
                    "icen": mes,
                    "nino12": (FECHA_MAX - timedelta(days=9)).isoformat(),
                    "fallas": FECHA_MAX.isoformat(),
                    "saidi": "2026-03",
                },
                regimen_nino=RegimenNino(estado=estado_nino(icen), icen=icen, mes=mes),
                metricas_prueba=metricas,
                modelo=self.modelo,
                version_datos=self.version_datos,
            )
        return self._resumen

    def diagnostico(self, area: str) -> Diagnostico:
        if area not in self._diagnosticos:
            self._diagnosticos[area] = self._calcular_diagnostico(area)
        return self._diagnosticos[area]

    def _calcular_diagnostico(self, area: str) -> Diagnostico:
        d = self._datos[area]
        h = PASOS["24h"]
        rng = np.random.default_rng(d.params.semilla + 1000)
        nombre_ref = self._mejor_referencia[(area, "24h")]

        # MAE por régimen: 2025 y 2026, porque 2026 casi no tiene régimen neutro.
        i = np.arange(_indice(datetime(2025, 1, 1)), _indice(datetime(2026, 11, 1)))
        i = i[~np.isnan(d.observado[i])]
        err_modelo = self._errores_24h(area, i, "M3")
        err_ref = np.abs(d.observado[i] - self._referencia(area, nombre_ref, i - h, i))
        estados = np.array([estado_nino(x) for x in d.icen[i]])
        por_regimen = []
        mascaras = [(e, estados == e) for e in ("neutro", "debil", "moderado", "fuerte")]
        mascaras += [
            ("extraordinario", estados == "extraordinario"),
            ("falla_en_curso", d.falla[i] > 0),
        ]
        for regimen, m in mascaras:
            if m.sum() >= DIA:
                por_regimen.append(
                    MaeRegimen(
                        regimen=regimen,
                        modelo=round(float(err_modelo[m].mean()), 1),
                        referencia=round(float(err_ref[m].mean()), 1),
                    )
                )

        # Ablación en la prueba de 2026, con intervalo por bootstrap de días.
        i = self._prueba(area)
        dias = (i - _indice(datetime(2026, 1, 1))) // DIA
        mae: dict[str, float] = {}
        ablacion = []
        remuestras = rng.integers(0, dias.max() + 1, size=(300, dias.max() + 1))
        for variante in GRUPOS:
            err = self._errores_24h(area, i, variante)
            por_dia = np.bincount(dias, weights=err) / np.maximum(np.bincount(dias), 1)
            boot = por_dia[remuestras].mean(axis=1)
            mae[variante] = float(err.mean())
            ablacion.append(
                Ablacion(
                    variante=variante,
                    mae=round(mae[variante], 1),
                    ic_inf=round(float(np.percentile(boot, 2.5)), 1),
                    ic_sup=round(float(np.percentile(boot, 97.5)), 1),
                )
            )

        factores = [("fijo", False, 1.0), ("fijo", True, 1.0), ("semanal", False, 0.94),
                    ("semanal", True, 0.95), ("alerta_enfen", True, 0.92)]  # fmt: skip
        adaptacion = [
            Adaptacion(
                politica=politica,
                exogenas=exo,
                mae=round(mae["M3" if exo else "M0"] * f, 1),
            )
            for politica, exo, f in factores
        ]

        nivel = np.nanmean(d.observado[i] / d.calendario[i])
        solo_calendario = float(np.mean(np.abs(d.observado[i] - nivel * d.calendario[i])))
        importancias = [
            Importancia(variable="demanda_reciente", valor=round(solo_calendario - mae["M3"], 1)),
            Importancia(variable="clima", valor=round(mae["M3_sin_clima"] - mae["M3"], 1)),
            Importancia(variable="nino", valor=round(mae["M3_sin_nino"] - mae["M3"], 1)),
            Importancia(variable="fallas", valor=round(mae["M3_sin_fallas"] - mae["M3"], 1)),
            Importancia(variable="saidi", valor=round(mae["M3"] - mae["M4"], 1)),
        ]
        importancias.sort(key=lambda x: x.valor, reverse=True)

        muestra = i[np.linspace(0, len(i) - 1, 240).astype(int)]
        predicho = self._predecir(area, muestra - h, np.full_like(muestra, h), GRUPOS["M3"])
        return Diagnostico(
            mae_por_regimen=por_regimen,
            ablacion=ablacion,
            adaptacion=adaptacion,
            importancias=importancias,
            residuos=Residuos(real=_redondear(d.observado[muestra]), predicho=_redondear(predicho)),
        )
