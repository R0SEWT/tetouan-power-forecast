"""API de la app: pronóstico de demanda por área del SEIN.

Correr en local (desde la raíz del repo):

    uv sync --extra dev --extra app
    uv run uvicorn app.backend.main:app --reload

Variables de entorno:
- ``TPF_CORS_ORIGENES``: orígenes extra separados por comas, además de localhost y 127.0.0.1
  (por ejemplo la IP del celular en la red local o el dominio de Tailscale).
- ``TPF_PRONOSTICADOR``: ``real`` para servir el modelo entrenado sobre las capas del SEIN
  (``pronosticador_real.py``, con ``TETOUAN_DATA`` apuntando a la carpeta de datos); si no, el de prueba.
  Si además están los archivos de los modelos híbrido y combinado (``pronosticador_hibrido.py``), se ofrecen
  como opciones del selector de modelo, y el combinado pasa a ser el de por defecto: es el de menor error en
  2026. Fuera de su rango de fechas (los días sin pronósticos precalculados) responde el modelo base, y las
  respuestas lo dicen en ``modelo``.
"""

import os
from datetime import date, datetime
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .contrato import (
    AREAS,
    FECHA_MAX,
    FECHA_MIN,
    FORMATO_FECHA_HORA,
    IDS_AREAS,
    MENSAJE_ESCENARIO_1H,
    PATRON_ORIGEN,
    Area,
    Diagnostico,
    Escenario,
    Horizonte,
    ModeloDisponible,
    PedidoPronostico,
    PedidoSensibilidad,
    PicoRampa,
    Pronostico,
    Resumen,
    Salud,
    Seguimiento,
    Sensibilidad,
    Serie,
    Variante,
)
from .pico import pico_rampa
from .pronosticador import Pronosticador, PronosticadorDePrueba

ORIGENES_LOCALES = r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?"


def _validar_area(area: str) -> None:
    if area not in IDS_AREAS:
        disponibles = ", ".join(sorted(IDS_AREAS))
        raise HTTPException(404, f"El área «{area}» no existe. Usa una de: {disponibles}.")


def _rango(pronosticador: Pronosticador) -> tuple[date, date]:
    # El pronosticador real conoce el rango que cubren sus datos; el de prueba usa el del contrato
    return getattr(pronosticador, "fecha_min", FECHA_MIN), getattr(pronosticador, "fecha_max", FECHA_MAX)


def _validar_fecha(fecha: date, pronosticador: Pronosticador) -> None:
    minimo, maximo = _rango(pronosticador)
    if not minimo <= fecha <= maximo:
        raise HTTPException(
            422,
            f"La fecha {fecha.isoformat()} está fuera del rango con datos: "
            f"de {minimo.isoformat()} a {maximo.isoformat()}.",
        )


def _leer_origen(origen: str) -> datetime:
    try:
        return datetime.strptime(origen, FORMATO_FECHA_HORA)
    except ValueError as error:
        raise HTTPException(422, f"El origen «{origen}» no es una fecha válida.") from error


def _id(pronosticador: Pronosticador) -> str:
    return getattr(pronosticador, "id", pronosticador.modelo)


def crear_app(pronosticador: Pronosticador | None = None, otros: list[Pronosticador] | None = None) -> FastAPI:
    """Arma la API con el pronosticador dado (por defecto, el de prueba) y, si los hay, otros modelos elegibles."""
    app = FastAPI(
        title="Demanda por área del SEIN",
        description="Pronóstico a 1 h y a 24 h de la demanda de Norte, Centro y Sur.",
        version="0.1.0",
    )
    extra = [o.strip() for o in os.environ.get("TPF_CORS_ORIGENES", "").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=extra,
        allow_origin_regex=ORIGENES_LOCALES,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.state.pronosticador = pronosticador or PronosticadorDePrueba()
    app.state.pronosticadores = {_id(p): p for p in [app.state.pronosticador, *(otros or [])]}

    def respaldo(request: Request, p: Pronosticador) -> Pronosticador | None:
        """El modelo que responde por ``p`` fuera de su rango, si la API también lo sirve."""
        r = getattr(p, "respaldo", None)
        return r if r is not None and request.app.state.pronosticadores.get(_id(r)) is r else None

    def modelo(request: Request, pedido: str | None = None, fecha: date | None = None) -> Pronosticador:
        """El modelo pedido. Sin pedir ninguno, el primero; si la fecha cae fuera de su rango, su respaldo."""
        if pedido is None:
            p = request.app.state.pronosticador
            minimo, maximo = _rango(p)
            r = respaldo(request, p)
            if fecha is not None and r is not None and not minimo <= fecha <= maximo:
                return r
            return p
        disponibles = request.app.state.pronosticadores
        if pedido not in disponibles:
            raise HTTPException(404, f"El modelo «{pedido}» no existe. Usa uno de: {', '.join(disponibles)}.")
        return disponibles[pedido]

    PARAMETRO_MODELO = Query(default=None, alias="modelo", description="Id de GET /modelos; si falta, el primero")

    @app.get("/salud", response_model=Salud)
    def salud(request: Request) -> Salud:
        p = modelo(request)
        return Salud(modelo=p.modelo, version_datos=p.version_datos)

    @app.get("/modelos", response_model=list[ModeloDisponible])
    def modelos(request: Request) -> list[ModeloDisponible]:
        """Los modelos disponibles; el primero es el que se usa cuando no se envía ``modelo``."""

        def fecha(p, nombre):
            valor = getattr(p, nombre, None)
            return valor.isoformat() if valor else None

        def id_respaldo(p):
            r = respaldo(request, p)
            return _id(r) if r is not None else None

        return [
            ModeloDisponible(id=_id(p), nombre=getattr(p, "nombre", p.modelo), descripcion=getattr(p, "descripcion", ""),
                             variantes=list(getattr(p, "variantes", ("M0", "M3"))),
                             fecha_min=fecha(p, "fecha_min"), fecha_max=fecha(p, "fecha_max"), respaldo=id_respaldo(p),
                             composicion=getattr(p, "origen_pesos", None))
            for p in request.app.state.pronosticadores.values()
        ]

    @app.get("/areas", response_model=list[Area])
    def areas() -> list[Area]:
        return AREAS

    @app.get("/resumen", response_model=Resumen)
    def resumen(request: Request, id_modelo: str | None = PARAMETRO_MODELO) -> Resumen:
        return modelo(request, id_modelo).resumen()

    @app.get("/series/{area}", response_model=Serie)
    def series(
        request: Request,
        area: str,
        fecha: Annotated[date, Query(description="Día, AAAA-MM-DD")],
        horizonte: Horizonte = "1h",
        variante: Variante = "M3",
        id_modelo: str | None = PARAMETRO_MODELO,
    ) -> Serie:
        _validar_area(area)
        p = modelo(request, id_modelo, fecha)
        _validar_fecha(fecha, p)
        return p.serie(area, fecha, horizonte, variante).model_copy(update={"modelo": _id(p)})

    def modelo_y_origen(request: Request, pedido: str | None, texto: str) -> tuple[Pronosticador, datetime]:
        origen = _leer_origen(texto)
        p = modelo(request, pedido, origen.date())
        _validar_fecha(origen.date(), p)
        return p, origen

    @app.post("/pronostico", response_model=Pronostico)
    def pronostico(request: Request, pedido: PedidoPronostico) -> Pronostico:
        _validar_area(pedido.area)
        p, origen = modelo_y_origen(request, pedido.modelo, pedido.origen)
        if pedido.horizonte == "1h" and not pedido.escenario.es_base:
            raise HTTPException(422, MENSAJE_ESCENARIO_1H)
        resultado = p.pronosticar(pedido.area, origen, pedido.horizonte, pedido.variante, pedido.escenario)
        return resultado.model_copy(update={"modelo": _id(p)})

    @app.post("/sensibilidad", response_model=Sensibilidad)
    def sensibilidad(request: Request, pedido: PedidoSensibilidad) -> Sensibilidad:
        _validar_area(pedido.area)
        p, origen = modelo_y_origen(request, pedido.modelo, pedido.origen)
        return p.sensibilidad(pedido.area, origen, pedido.variable)

    @app.get("/diagnostico/{area}", response_model=Diagnostico)
    def diagnostico(request: Request, area: str, id_modelo: str | None = PARAMETRO_MODELO) -> Diagnostico:
        _validar_area(area)
        return modelo(request, id_modelo).diagnostico(area)

    @app.get("/seguimiento/{area}", response_model=Seguimiento)
    def seguimiento(
        request: Request,
        area: str,
        horizonte: Horizonte = "24h",
        variante: Variante = "M3",
        id_modelo: str | None = PARAMETRO_MODELO,
    ) -> Seguimiento:
        """MAE por mes y cobertura del rango probable en la prueba de 2026, frente a la mejor referencia."""
        _validar_area(area)
        return modelo(request, id_modelo).seguimiento(area, horizonte, variante)

    @app.get("/pico/{area}", response_model=PicoRampa)
    def pico(
        request: Request,
        area: str,
        origen: Annotated[str, Query(pattern=PATRON_ORIGEN, description="AAAA-MM-DDTHH:MM")],
        variante: Variante = "M3",
        id_modelo: str | None = PARAMETRO_MODELO,
    ) -> PicoRampa:
        """El máximo y la mayor subida en una hora de las 24 h siguientes al origen (pronóstico a 24 h)."""
        _validar_area(area)
        p, momento = modelo_y_origen(request, id_modelo, origen)
        resultado = p.pronosticar(area, momento, "24h", variante, Escenario())
        umbral = p.umbral_rampa(area) if hasattr(p, "umbral_rampa") else None
        acierto = p.acierto_pico(area, variante) if hasattr(p, "acierto_pico") else None
        return pico_rampa(resultado, umbral, acierto, modelo=_id(p))

    return app


def _pronosticadores_por_defecto() -> tuple[Pronosticador | None, list[Pronosticador]]:
    """El modelo real y, si están sus archivos, el híbrido y el combinado (que va primero).

    Sin ``TPF_PRONOSTICADOR=real``, el de prueba.
    """
    if os.environ.get("TPF_PRONOSTICADOR") != "real":
        return None, []
    from .pronosticador_hibrido import (
        PronosticadorCombinado,
        PronosticadorHibrido,
        combinado_disponible,
        hibrido_disponible,
    )
    from .pronosticador_real import PronosticadorReal

    base = PronosticadorReal()
    if not hibrido_disponible():
        return base, []
    hibrido = PronosticadorHibrido(base)
    if not combinado_disponible():
        return base, [hibrido]
    # El combinado primero: es el de por defecto. Fuera de su rango responde el base (su respaldo).
    return PronosticadorCombinado(hibrido), [base, hibrido]


app = crear_app(*_pronosticadores_por_defecto())
