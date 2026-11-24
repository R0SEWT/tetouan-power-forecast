"""Captura versiones crudas de los productos públicos de demanda del COES."""

import argparse
import datetime as dt
import fcntl
import hashlib
import io
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from tetouan_power_forecast import coes
from tetouan_power_forecast.en_vivo import metadatos_listado
from tetouan_power_forecast.medallon import _reemplazar

LIMA = ZoneInfo("America/Lima")
DEMANDA = f"{coes.URL_PORTAL}/portalinformacion"
API_AREAS = "https://appserver.coes.org.pe/waMediciones/api/Demanda"
CATALOGOS = {
    "pdo": ("Programa Diario", r"anexo\s*1.*despacho.*\.xlsx"),
    "actualizacion_pdo": ("Actualización del Programa Diario", r".*\.xlsx"),
    "rdo": ("Reprograma Diario Operación", r"(?:anexo\s*1.*despacho|reprog.*)\.xlsx"),
}


def ahora():
    return dt.datetime.now(dt.UTC)


def url_con_fecha(url, fecha):
    return f"{url}?{urllib.parse.urlencode({'dtFecha': fecha.isoformat()})}"


def listar(base, ruta, pedir):
    parametros = {"baseDirectory": base, "url": ruta, "indicador": "S"}
    pagina = pedir(f"{coes.URL_PORTAL}/browser/vistadatos", parametros).decode("utf-8")
    return coes.parsear_listado(pagina), metadatos_listado(pagina)


def anexos_catalogo(fuente, dias, pedir):
    nombre, patron = CATALOGOS[fuente]
    base = f"Operación/Programa de Operación/{nombre}/"

    @lru_cache
    def listado_de(ruta):
        return listar(base, ruta, pedir)

    raiz, _ = listado_de(base)
    resultados = []
    for dia in dias:
        anio = f"{base}{dia.year}/"
        if ("D", anio) not in raiz:
            resultados.append((dia, []))
            continue
        listado_anio, _ = listado_de(anio)
        mes = coes.carpeta_del_mes(listado_anio, dia.month)
        carpeta = None
        if mes:
            listado_mes, _ = listado_de(mes)
            carpeta = coes.carpeta_del_dia(listado_mes, dia.day)
        candidatos = []
        if carpeta:
            listado, firmas = listado_de(carpeta)
            candidatos = [
                (ruta, firmas.get(ruta, ""))
                for tipo, ruta in listado
                if tipo == "F" and re.fullmatch(patron, coes._nombre(ruta), re.IGNORECASE)
            ]
            for tipo, ruta in listado:
                if tipo == "D":
                    sublistado, subfirmas = listado_de(ruta)
                    candidatos.extend(
                        (archivo, subfirmas.get(archivo, ""))
                        for clase, archivo in sublistado
                        if clase == "F"
                        and re.fullmatch(patron, coes._nombre(archivo), re.IGNORECASE)
                    )
        resultados.append((dia, candidatos))
    return resultados


class Archivo:
    def __init__(self, raiz):
        self.raiz = raiz
        self.inicio = ahora()
        self.eventos = []

    def evento(self, fuente, objetivo, estado, **datos):
        self.eventos.append(dict(
            fuente=fuente, objetivo=objetivo, estado=estado,
            observado_utc=ahora().isoformat(), **datos,
        ))

    def guardar(self, fuente, objetivo, url, contenido, extension, **metadatos):
        sha = hashlib.sha256(contenido).hexdigest()
        relativa = Path("objetos") / sha[:2] / f"{sha}.{extension}"
        destino = self.raiz / relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        if not destino.exists():
            _reemplazar(destino, lambda temporal: temporal.write_bytes(contenido))
        elif hashlib.sha256(destino.read_bytes()).hexdigest() != sha:
            raise ValueError(f"Objeto archivado con hash incorrecto: {relativa}")
        self.evento(fuente, objetivo, "capturado", url=url, archivo=str(relativa),
                    sha256=sha, bytes=len(contenido), **metadatos)

    def cerrar(self):
        carpeta = self.raiz / "capturas" / self.inicio.date().isoformat()
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"{self.inicio:%Y%m%dT%H%M%S%fZ}.json"
        contenido = json.dumps(self.eventos, indent=2, ensure_ascii=False) + "\n"
        _reemplazar(ruta, lambda temporal: temporal.write_text(contenido, encoding="utf-8"))
        return ruta


def capturar_json(archivo, fuente, objetivo, url, pedir, parametros=None, campos=()):
    try:
        contenido = pedir(url, parametros)
        datos = json.loads(contenido)
        if not datos:
            archivo.evento(fuente, objetivo, "sin_datos", url=url)
        else:
            if campos and (
                not isinstance(datos, list)
                or any(not isinstance(fila, dict) or set(campos) - fila.keys() for fila in datos)
            ):
                raise ValueError("Respuesta sin los campos esperados")
            archivo.guardar(fuente, objetivo, url, contenido, "json", parametros=parametros)
    except (OSError, ValueError) as error:
        archivo.evento(fuente, objetivo, "error", url=url, error=str(error))


def capturar_sello_pronostico(archivo, hoy, pedir):
    fuente = "actualizacion_pronostico_tiempo_real"
    url = f"{DEMANDA}/ObtenerPronosticoTiempoRealFechaDeActualizacion"
    try:
        contenido = pedir(url)
        sello = dt.datetime.fromisoformat(contenido.decode("utf-8").strip())
        archivo.guardar(fuente, hoy.isoformat(), url, contenido, "txt",
                        publicado_segun_coes=sello.isoformat(), zona_horaria_declarada=None)
    except (OSError, ValueError) as error:
        archivo.evento(fuente, hoy.isoformat(), "error", url=url, error=str(error))


def capturar_anexos(archivo, fuente, dias, pedir):
    try:
        resultados = anexos_catalogo(fuente, dias, pedir)
    except (OSError, ValueError) as error:
        archivo.evento(fuente, ",".join(map(str, dias)), "error", error=str(error))
        return
    for dia, candidatos in resultados:
        if not candidatos:
            archivo.evento(fuente, dia.isoformat(), "sin_datos")
        for ruta, firma in candidatos:
            url = f"{coes.URL_PORTAL}/browser/download?{urllib.parse.urlencode({'url': ruta})}"
            try:
                contenido = pedir(url)
                with zipfile.ZipFile(io.BytesIO(contenido)) as libro:
                    if "xl/workbook.xml" not in libro.namelist() or libro.testzip():
                        raise ValueError("Libro XLSX inválido")
                archivo.guardar(fuente, dia.isoformat(), url, contenido, "xlsx",
                                ruta_coes=ruta, metadatos_catalogo=firma)
            except (OSError, ValueError, zipfile.BadZipFile) as error:
                archivo.evento(fuente, dia.isoformat(), "error", url=url, error=str(error))


def capturar(raiz, hoy, pedir):
    archivo = Archivo(raiz)
    manana = hoy + dt.timedelta(days=1)
    # Volvemos a consultar los dos días cerrados para guardar el Ejecutado
    # completo y observar revisiones posteriores a la primera publicación.
    for desfase in range(3):
        dia = hoy - dt.timedelta(days=desfase)
        fecha = dia.strftime("%d/%m/%Y")
        capturar_json(archivo, "ejecutado_portal", dia.isoformat(), f"{DEMANDA}/Demanda", pedir,
                      {"fechaInicial": fecha, "fechaFinal": fecha})
    capturar_json(archivo, "pronostico_tiempo_real", hoy.isoformat(),
                  f"{DEMANDA}/ObtenerPronosticoTiempoReal", pedir,
                  campos=("fecha", "PronosticoTiempoReal", "PronosticoMinimo", "PronosticoMaximo"))
    capturar_sello_pronostico(archivo, hoy, pedir)
    for dia in (hoy, manana):
        capturar_json(archivo, "demanda_programada_api", dia.isoformat(),
                      url_con_fecha(API_AREAS, dia), pedir)
    capturar_anexos(archivo, "pdo", (hoy, manana), pedir)
    capturar_anexos(archivo, "actualizacion_pdo", (hoy, manana), pedir)
    capturar_anexos(archivo, "rdo", (hoy,), pedir)
    ruta = archivo.cerrar()
    for evento in archivo.eventos:
        if evento["estado"] == "error":
            print(json.dumps(evento, ensure_ascii=False), file=sys.stderr)
    print(f"{ruta} · {len(archivo.eventos)} observaciones")
    return int(any(evento["estado"] == "error" for evento in archivo.eventos))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archivo", required=True, type=Path)
    args = parser.parse_args()
    args.archivo.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (args.archivo / ".captura.lock").open("a") as bloqueo:
        fcntl.flock(bloqueo, fcntl.LOCK_EX)
        return capturar(
            args.archivo, ahora().astimezone(LIMA).date(),
            lambda url, datos=None: coes._pedir(url, datos, timeout=8, intentos=2, espera=2),
        )


if __name__ == "__main__":
    sys.exit(main())
