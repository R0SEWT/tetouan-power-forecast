"""API de la app: pronóstico de demanda por área del SEIN.

Correr en local (desde la raíz del repo):

    uv sync --extra dev --extra app
    uv run uvicorn app.backend.main:app --reload

Variables de entorno:
- ``TPF_CORS_ORIGENES``: orígenes extra separados por comas, además de localhost y 127.0.0.1
  (por ejemplo la IP del celular en la red local o el dominio de Tailscale).
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
    Area,
    Diagnostico,
    Horizonte,
    PedidoPronostico,
    PedidoSensibilidad,
    Pronostico,
    Resumen,
    Salud,
    Sensibilidad,
    Serie,
    Variante,
)
from .pronosticador import Pronosticador, PronosticadorDePrueba

ORIGENES_LOCALES = r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?"


def _validar_area(area: str) -> None:
    if area not in IDS_AREAS:
        disponibles = ", ".join(sorted(IDS_AREAS))
        raise HTTPException(404, f"El área «{area}» no existe. Usa una de: {disponibles}.")


def _validar_fecha(fecha: date) -> None:
    if not FECHA_MIN <= fecha <= FECHA_MAX:
        raise HTTPException(
            422,
            f"La fecha {fecha.isoformat()} está fuera del rango con datos: "
            f"de {FECHA_MIN.isoformat()} a {FECHA_MAX.isoformat()}.",
        )


def _leer_origen(origen: str) -> datetime:
    try:
        momento = datetime.strptime(origen, FORMATO_FECHA_HORA)
    except ValueError as error:
        raise HTTPException(422, f"El origen «{origen}» no es una fecha válida.") from error
    _validar_fecha(momento.date())
    return momento


def crear_app(pronosticador: Pronosticador | None = None) -> FastAPI:
    """Arma la API con el pronosticador dado; por defecto, el de prueba."""
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

    def modelo(request: Request) -> Pronosticador:
        return request.app.state.pronosticador

    @app.get("/salud", response_model=Salud)
    def salud(request: Request) -> Salud:
        p = modelo(request)
        return Salud(modelo=p.modelo, version_datos=p.version_datos)

    @app.get("/areas", response_model=list[Area])
    def areas() -> list[Area]:
        return AREAS

    @app.get("/resumen", response_model=Resumen)
    def resumen(request: Request) -> Resumen:
        return modelo(request).resumen()

    @app.get("/series/{area}", response_model=Serie)
    def series(
        request: Request,
        area: str,
        fecha: Annotated[date, Query(description="Día, AAAA-MM-DD")],
        horizonte: Horizonte = "1h",
        variante: Variante = "M3",
    ) -> Serie:
        _validar_area(area)
        _validar_fecha(fecha)
        return modelo(request).serie(area, fecha, horizonte, variante)

    @app.post("/pronostico", response_model=Pronostico)
    def pronostico(request: Request, pedido: PedidoPronostico) -> Pronostico:
        _validar_area(pedido.area)
        origen = _leer_origen(pedido.origen)
        if pedido.horizonte == "1h" and not pedido.escenario.es_base:
            raise HTTPException(422, MENSAJE_ESCENARIO_1H)
        return modelo(request).pronosticar(
            pedido.area, origen, pedido.horizonte, pedido.variante, pedido.escenario
        )

    @app.post("/sensibilidad", response_model=Sensibilidad)
    def sensibilidad(request: Request, pedido: PedidoSensibilidad) -> Sensibilidad:
        _validar_area(pedido.area)
        origen = _leer_origen(pedido.origen)
        return modelo(request).sensibilidad(pedido.area, origen, pedido.variable)

    @app.get("/diagnostico/{area}", response_model=Diagnostico)
    def diagnostico(request: Request, area: str) -> Diagnostico:
        _validar_area(area)
        return modelo(request).diagnostico(area)

    return app


app = crear_app()
