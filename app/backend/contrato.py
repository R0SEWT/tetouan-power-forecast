"""Contrato de la API de la app: modelos de entrada y salida.

Reglas comunes:
- JSON en español y snake_case.
- Fechas y horas en ISO 8601, en hora de Lima y sin zona, con minutos en punto o y media
  (``"2026-02-26T15:00"``). Cada ``fecha_hora`` marca el inicio de su periodo de 30 minutos.
- Demanda en MW.
- Errores: 404 si el área no existe; 422 si la fecha cae fuera de ``FECHA_MIN``-``FECHA_MAX``,
  si un campo no cumple su formato o si se pide un escenario a 1 h.

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
        description="Programación Diaria del COES; solo a 24 h, null a 1 h"
    )
    hueco: list[bool] = Field(description="True si no hay dato real en ese periodo")
    preliminar: list[bool] = Field(description="True si el COES marcó el dato como preliminar")


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


class Intervalo(BaseModel):
    inferior: list[float]
    superior: list[float]


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


class PedidoSensibilidad(BaseModel):
    area: str
    origen: str = Field(pattern=PATRON_ORIGEN, examples=["2026-02-26T15:00"])
    variable: VariableSensibilidad


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
