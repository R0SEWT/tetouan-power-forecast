"""Contrato de la API de la app: modelos de entrada y salida.

Reglas comunes:
- JSON en español y snake_case.
- Fechas y horas en ISO 8601, en hora de Lima y sin zona, con minutos en punto o y media
  (``"2026-02-26T15:00"``). Cada ``fecha_hora`` marca el inicio de su periodo de 30 minutos.
- Demanda en MW.
- Errores: 404 si el área o el modelo no existen; 422 si la fecha cae fuera de ``FECHA_MIN``-``FECHA_MAX``,
  si un campo no cumple su formato o si se pide un escenario a 1 h.
- Sin el parámetro ``modelo`` responde el primero de ``GET /modelos``; si la fecha cae fuera de su rango y tiene
  ``respaldo``, responde el respaldo. ``Serie`` y ``Pronostico`` dicen en ``modelo`` cuál respondió.

Este archivo es la fuente de verdad del contrato: el frontend y las pruebas trabajan contra él.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

FECHA_MIN = date(2025, 1, 1)
FECHA_MAX = date(2026, 10, 31)
FORMATO_FECHA_HORA = "%Y-%m-%dT%H:%M"
PATRON_ORIGEN = r"^\d{4}-\d{2}-\d{2}T\d{2}:(00|30)$"

Horizonte = Literal["1h", "24h"]
Variante = Literal["M0", "M3"]
Referencia = Literal["persistencia", "ayer", "semana_pasada"]
VariableSensibilidad = Literal["temperatura", "icen"]
EstadoNino = Literal["neutro", "debil", "moderado", "fuerte", "extraordinario"]

PASOS = {"1h": 2, "24h": 48}  # pasos de 30 minutos de cada horizonte

MENSAJE_ESCENARIO_1H = (
    "A 1 h no hay escenarios: la demanda reciente ya contiene el clima del momento, así que "
    "cambiar el clima o El Niño no es un escenario creíble. Usa el horizonte de 24 h para los "
    "escenarios o POST /sensibilidad para ver cómo responde el modelo a 1 h."
)


class Salud(BaseModel):
    estado: Literal["ok"] = "ok"
    modelo: str
    version_datos: str


class ModeloDisponible(BaseModel):
    """Un modelo que el backend puede servir. El primero de la lista es el que se usa si no se pide otro."""

    id: str
    nombre: str
    descripcion: str = ""
    variantes: list[Variante] = Field(default=["M0", "M3"], description="Las variantes que el modelo distingue")
    fecha_min: str | None = Field(default=None, description="Primer día que puede pronosticar, AAAA-MM-DD")
    fecha_max: str | None = Field(default=None, description="Último día que puede pronosticar, AAAA-MM-DD")
    respaldo: str | None = Field(
        default=None, description="Id del modelo que responde por este fuera de su rango de fechas"
    )
    composicion: str | None = Field(
        default=None, description="Si es una mezcla, de dónde salen sus pesos (la app lo muestra en la ficha)"
    )


class Area(BaseModel):
    id: str
    nombre: str
    color: str


AREAS: list[Area] = [
    Area(id="norte", nombre="Norte", color="#E69F00"),
    Area(id="centro", nombre="Centro", color="#0072B2"),
    Area(id="sur", nombre="Sur", color="#009E73"),
]
IDS_AREAS = frozenset(a.id for a in AREAS)


class RegimenNino(BaseModel):
    """Último ICEN publicado y su clasificación según ENFEN."""

    estado: EstadoNino
    icen: float
    mes: str = Field(description="Mes del ICEN, AAAA-MM")


class MetricaPrueba(BaseModel):
    """Error del modelo en la prueba de 2026, a 24 h y con la variante M3."""

    mae_mw: float
    mape_pct: float
    mejor_referencia: Referencia


class Resumen(BaseModel):
    fechas_corte: dict[str, str] = Field(
        description="Último dato disponible de cada fuente y límites de la partición"
    )
    regimen_nino: RegimenNino
    metricas_prueba: dict[str, MetricaPrueba] = Field(description="Por id de área")
    modelo: str
    version_datos: str


class Intervalo(BaseModel):
    inferior: list[float]
    superior: list[float]


class Componente(BaseModel):
    """Una pieza de un pronóstico combinado: ``pronostico ≈ Σ peso · valores`` (± el redondeo a 0.1 MW)."""

    id: str
    nombre: str
    peso: float
    valores: list[float | None] = Field(description="Un valor por periodo; nulo si la pieza falta ahí")


class Serie(BaseModel):
    """Los 48 periodos de un día. El pronóstico de cada periodo se emitió H pasos antes."""

    fecha_hora: list[str]
    real: list[float | None]
    pronostico: list[float]
    referencia: list[float] = Field(description="La mejor referencia ingenua del horizonte")
    referencia_nombre: Referencia = Field(
        description="Cuál es la mejor referencia (agregado al contrato: la app la nombra)"
    )
    programacion_diaria: list[float | None] | None = Field(
        description="Reservado para la Programación Diaria del COES. La app no lo muestra: el "
        "proyecto no hizo esa comparación"
    )
    hueco: list[bool] = Field(description="True si no hay dato real en ese periodo")
    preliminar: list[bool] = Field(description="True si el COES marcó el dato como preliminar")
    intervalo: Intervalo | None = Field(
        default=None,
        description="Rango probable (90 %) de cada periodo, emitido H pasos antes como el "
        "pronóstico (agregado al contrato: la app lo muestra junto al número y en la curva)",
    )
    modelo: str | None = Field(default=None, description="Id del modelo que respondió")
    componentes: list[Componente] | None = Field(
        default=None, description="Si el modelo es una mezcla, sus piezas y pesos (la app arma la ficha)"
    )


class Escenario(BaseModel):
    delta_temp_c: Literal[-2, 0, 2, 4] = 0
    nino: Literal["observado", "neutro"] = "observado"
    falla: Literal["observada", "ninguna"] = "observada"

    @property
    def es_base(self) -> bool:
        return self.delta_temp_c == 0 and self.nino == "observado" and self.falla == "observada"


class PedidoPronostico(BaseModel):
    area: str
    origen: str = Field(pattern=PATRON_ORIGEN, examples=["2026-02-26T15:00"])
    horizonte: Horizonte
    variante: Variante = "M3"
    escenario: Escenario = Field(default_factory=Escenario)
    modelo: str | None = Field(default=None, description="Id de GET /modelos; si falta, el primero")


class Pronostico(BaseModel):
    """Los H periodos siguientes al origen (2 a 1 h, 48 a 24 h).

    Cada valor usa solo información disponible hasta el origen.
    """

    fecha_hora: list[str]
    pronostico: list[float]
    referencia: list[float]
    real: list[float | None]
    intervalo: Intervalo
    frase: str = Field(description="El cambio en la hora de mayor demanda, en texto llano")
    modelo: str | None = Field(default=None, description="Id del modelo que respondió")


class PedidoSensibilidad(BaseModel):
    area: str
    origen: str = Field(pattern=PATRON_ORIGEN, examples=["2026-02-26T15:00"])
    variable: VariableSensibilidad
    modelo: str | None = Field(default=None, description="Id de GET /modelos; si falta, el primero")


class Sensibilidad(BaseModel):
    """Dependencia parcial a 1 h: el pronóstico de t+2 al mover una variable, con las demás fijas."""

    valores: list[float]
    pronostico: list[float]


class MaeRegimen(BaseModel):
    regimen: str
    modelo: float
    referencia: float


class Ablacion(BaseModel):
    variante: str
    mae: float
    ic_inf: float
    ic_sup: float


class Adaptacion(BaseModel):
    politica: Literal["fijo", "semanal", "alerta_enfen"]
    exogenas: bool
    mae: float


class Importancia(BaseModel):
    variable: str
    valor: float = Field(description="Aumento del MAE, en MW, al quitar la variable")


class Residuos(BaseModel):
    real: list[float]
    predicho: list[float]


class Diagnostico(BaseModel):
    """Diagnóstico a 24 h del área. Los MAE van en MW."""

    mae_por_regimen: list[MaeRegimen]
    ablacion: list[Ablacion]
    adaptacion: list[Adaptacion]
    importancias: list[Importancia]
    residuos: Residuos


class MesSeguimiento(BaseModel):
    """El error y la cobertura de un mes de la prueba de 2026 (o de todo el año, con ``mes="2026"``)."""

    mes: str = Field(description="AAAA-MM del periodo pronosticado, o AAAA para el total")
    mae_modelo: float
    mae_referencia: float
    cobertura_pct: float = Field(description="% de periodos cuyo valor real cayó dentro del rango probable")
    periodos: int


class Seguimiento(BaseModel):
    """Seguimiento del error y de la cobertura en la prueba de 2026, solo con pronósticos fuera de muestra.

    El modelo y la referencia se miden en los mismos periodos: los que tienen dato real, pronóstico del modelo y
    valor de la referencia.
    """

    horizonte: Horizonte
    referencia_nombre: Referencia
    meta_cobertura_pct: float = Field(default=90.0, description="Lo que el rango promete cubrir")
    meses: list[MesSeguimiento]
    total: MesSeguimiento


class Pico(BaseModel):
    fecha_hora: str = Field(description="Inicio del periodo con la mayor demanda pronosticada")
    valor: float
    inferior: float
    superior: float


class Rampa(BaseModel):
    """La mayor subida en una hora: del periodo ``desde`` al que empieza una hora después (``hasta``)."""

    desde: str
    hasta: str
    subida_mw: float
    fuerte: bool = Field(description="True si supera ``umbral_mw``")
    umbral_mw: float | None = Field(
        default=None,
        description="Percentil 95 de la mayor subida horaria de cada día del área en 2016-2024 (lo real)",
    )


class AciertoPico(BaseModel):
    """Qué tan bien ubica el máximo de cada día de la prueba de 2026, a 24 h."""

    dias: int = Field(description="Días con los 48 periodos reales")
    pct_hora: float = Field(description="% de días con la hora del máximo pronosticado a ±1 h de la real")
    pct_hora_referencia: float
    mae_pico_mw: float = Field(description="Error medio del máximo diario, en MW")
    mae_pico_referencia_mw: float


class PicoRampa(BaseModel):
    """El máximo y la mayor subida de las 24 h siguientes al origen, según el pronóstico a 24 h.

    No es un pronóstico de varios pasos: cada periodo es el pronóstico directo a 24 h emitido 24 h antes de
    ese periodo, como en la serie del día. Todos ya estaban emitidos en el origen.
    """

    desde: str = Field(description="Primer periodo de la ventana")
    hasta: str = Field(description="Último periodo de la ventana")
    pico: Pico
    rampa: Rampa | None = Field(description="Nula si la ventana no sube en ninguna hora")
    acierto: AciertoPico | None = Field(default=None, description="El del modelo y el área en 2026")
    modelo: str | None = Field(default=None, description="Id del modelo que respondió")


# ---- En vivo: lo que registra la tubería diaria (tetouan_power_forecast.en_vivo) ----------------------------------

TipoEnVivo = Literal["ex_ante_estricto", "en_vivo", "reconstruido"]
GrupoEnVivo = Literal["en_vivo", "ex_ante_estricto", "reconstruido"]


class PerfilEnVivo(BaseModel):
    """El último perfil a 24 h que emitió la tubería: los 48 periodos de un día, cada uno desde su origen 24 h antes.

    Todos se emitieron juntos, en ``emitido_en``, con los datos hasta ``datos_hasta``.
    """

    fecha: str = Field(description="Día pronosticado, AAAA-MM-DD")
    horizonte: Horizonte
    emitido_en: str = Field(description="Sello de la corrida, ISO 8601 en UTC (termina en Z)")
    emitido_lima: str = Field(description="El mismo sello en hora de Lima, AAAA-MM-DDTHH:MM")
    datos_hasta: str = Field(description="Fin del último periodo con dato que se usó, hora de Lima")
    fecha_hora: list[str] = Field(description="Inicio de cada periodo")
    pronostico: list[float]
    inferior: list[float] = Field(description="Cuantil 10 %")
    superior: list[float] = Field(description="Cuantil 90 %")
    real: list[float | None] = Field(description="Nulo mientras el COES no publique el real")
    tipo: list[TipoEnVivo] = Field(description="Cuándo se emitió cada periodo frente a su real (ver EnVivo)")


class DiaEnVivo(BaseModel):
    """Un día ya verificado contra el real."""

    fecha: str
    horizonte: Horizonte
    tipo: Literal["en_vivo", "reconstruido"] = Field(
        description="«en_vivo» si se emitió antes de que el COES publicara el real; «reconstruido» si después"
    )
    periodos: int
    periodos_ex_ante: int = Field(description="Periodos que todavía no empezaban al emitirse")
    mae_modelo: float
    mae_referencia: float
    referencia_nombre: Referencia
    cobertura_pct: float = Field(description="% de periodos con el real dentro del rango 10–90 %")


class ResumenEnVivo(BaseModel):
    """El error acumulado de un grupo de filas, frente a la mejor referencia ingenua en esas mismas filas."""

    grupo: GrupoEnVivo = Field(description="«en_vivo» incluye las ex ante estrictas; «ex_ante_estricto» las separa")
    horizonte: Horizonte
    desde: str
    hasta: str
    dias: int
    periodos: int
    mae_modelo: float
    mae_referencia: float
    referencia_nombre: Referencia
    sesgo: float = Field(description="Media de pronóstico − real, en MW")
    cobertura_pct: float


class EnVivo(BaseModel):
    """El pronóstico en vivo de un área: el último perfil emitido, lo ya verificado y el acumulado por tipo.

    Tipos de cada periodo, según su sello de emisión:
    - ``ex_ante_estricto``: el periodo todavía no empezaba.
    - ``en_vivo``: ya había empezado, pero el COES aún no podía haber publicado su real (sale al día siguiente).
    - ``reconstruido``: se emitió después de conocerse el real (el relleno inicial y todo el 1 h, que no puede ser
      en vivo con un día de retraso), usando solo los datos hasta su origen.

    Sin registro todavía, ``ultimo`` es nulo y las listas van vacías.
    """

    area: str
    modelo: str | None = Field(default=None, description="Nombre del modelo que emite")
    version_pesos: str | None = Field(default=None, description="sha256 de los pesos")
    nivel_rango_pct: int = Field(default=80, description="El rango va del cuantil 10 al 90: cubre 8 de cada 10")
    ultimo: PerfilEnVivo | None = None
    verificado: list[DiaEnVivo] = Field(default_factory=list, description="Del más reciente al más antiguo")
    resumen: list[ResumenEnVivo] = Field(default_factory=list)
    dias_en_vivo: int = Field(default=0, description="Días con pronóstico a 24 h emitido en vivo (verificados o no)")
    primer_dia_en_vivo: str | None = None
    dias_reconstruidos: int = Field(default=0, description="Días con pronóstico a 24 h reconstruido")
