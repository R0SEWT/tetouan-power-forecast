"""Cruza capturas crudas del COES por fecha objetivo y media hora de Lima."""

import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

PASO = pd.Timedelta(minutes=30)
PDO_COLUMNAS = {
    "Demanda COES": "pdo_coes",
    "Demanda YUPANA": "pdo_yupana",
    "Demanda Centro": "pdo_centro",
    "Demanda Norte": "pdo_norte",
    "Demanda Sur": "pdo_sur",
    "Demanda Electroandes": "pdo_electroandes",
    "Demanda Ecuador": "pdo_ecuador",
}
API_PUNTOS = {1210: "sein", 1211: "centro", 1212: "norte", 1213: "sur", 1214: "electroandes"}
PARES = [
    ("pdo_coes", "api_sein"),
    ("pdo_yupana", "api_sein"),
    ("pdo_coes", "portal_programacion_diaria"),
    ("pdo_yupana", "portal_programacion_diaria"),
    ("api_sein", "portal_programacion_diaria"),
    ("ieod_sein", "portal_ejecutado"),
    *((f"pdo_{area}", f"api_{area}") for codigo, area in API_PUNTOS.items() if codigo != 1210),
]


def rejilla(dia):
    return pd.date_range(pd.Timestamp(dia) + PASO, periods=48, freq=PASO, name="objetivo")


def leer_pdo(contenido, dia):
    """Lee las columnas de demanda del anexo de despacho, con 23:59 como H48."""
    libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    try:
        filas = list(libro.active.values)
    finally:
        libro.close()
    for numero, fila in enumerate(filas):
        nombres = [valor.strip() if isinstance(valor, str) else valor for valor in fila]
        if "Día Hora" in nombres and "Demanda COES" in nombres:
            break
    else:
        raise ValueError(f"Cabecera de demanda ausente en el PDO de {dia}")
    hora = nombres.index("Día Hora")
    intervalos = filas[numero + 1:numero + 49]
    marcas = [str(fila[hora])[:5] for fila in intervalos]
    esperado = rejilla(dia).strftime("%H:%M").tolist()
    if len(marcas) != 48 or marcas[:-1] != esperado[:-1] or marcas[-1] not in {
        "23:59", "24:00", "00:00",
    }:
        raise ValueError(f"Rejilla inesperada en el PDO de {dia}")
    return pd.DataFrame({
        columna: [fila[nombres.index(nombre)] for fila in intervalos]
        for nombre, columna in PDO_COLUMNAS.items() if nombre in nombres
    }, index=rejilla(dia), dtype=float)


def leer_api(contenido, dia):
    series = {}
    for fila in json.loads(contenido):
        punto = int(fila["PTOMEDICODI"])
        if punto not in API_PUNTOS:
            continue
        if dt.datetime.fromisoformat(fila["MEDIFECHA"]).date() != dt.date.fromisoformat(dia):
            raise ValueError(f"Respuesta de la API con fecha distinta de {dia}")
        valores = {llave.lower(): valor for llave, valor in fila.items()}
        nombre = "api_" + API_PUNTOS[punto]
        if nombre in series:
            raise ValueError(f"Punto duplicado en la API del COES: {punto}")
        series[nombre] = [valores[f"h{i}"] for i in range(1, 49)]
    return pd.DataFrame(series, index=rejilla(dia), dtype=float)


def leer_portal(contenido, dia):
    etiquetas = {"Programación Diaria": "portal_programacion_diaria", "Ejecutado": "portal_ejecutado"}
    series = {}
    for serie in json.loads(contenido)["Chart"]["Series"]:
        if serie["Name"] in etiquetas:
            filas = pd.DataFrame(serie["Data"])
            if not filas.empty:
                fechas = pd.to_datetime(filas["Nombre"], format="%Y/%m/%d %H:%M:%S")
                series[etiquetas[serie["Name"]]] = pd.Series(filas["Valor"].to_numpy(), index=fechas)
    return pd.DataFrame(series, index=rejilla(dia), dtype=float)


LECTORES = {"pdo": leer_pdo, "demanda_programada_api": leer_api, "ejecutado_portal": leer_portal}


def conciliar(raices, dias, ieod):
    eventos = {}
    for raiz in raices:
        for manifiesto in sorted(raiz.glob("capturas/*/*.json")):
            for evento in json.loads(manifiesto.read_text(encoding="utf-8")):
                fuente, dia = evento["fuente"], evento["objetivo"]
                if fuente not in LECTORES or dia not in dias or evento["estado"] != "capturado":
                    continue
                clave = dia, fuente
                anterior = eventos.get(clave)
                if anterior is None or evento["observado_utc"] < anterior[1]["observado_utc"]:
                    eventos[clave] = (raiz, evento)

    tablas = []
    for dia in sorted(dias):
        tabla = pd.DataFrame(index=rejilla(dia))
        for fuente, lector in LECTORES.items():
            seleccion = eventos.get((dia, fuente))
            if seleccion is None:
                continue
            raiz, evento = seleccion
            contenido = (raiz / evento["archivo"]).read_bytes()
            if hashlib.sha256(contenido).hexdigest() != evento["sha256"]:
                raise ValueError(f"Hash inválido para {evento['archivo']}")
            tabla = tabla.join(lector(contenido, dia), validate="one_to_one")
            tabla[f"{fuente}_observado_utc"] = evento["observado_utc"]
            tabla[f"{fuente}_sha256"] = evento["sha256"]
        if ieod is not None:
            tabla["ieod_sein"] = ieod.reindex(tabla.index)
        tablas.append(tabla.assign(dia=dia).reset_index())
    return pd.concat(tablas, ignore_index=True)


def resumen(tabla):
    filas = []
    for dia, datos in tabla.groupby("dia"):
        for primera, segunda in PARES:
            if {primera, segunda} <= set(datos):
                diferencia = datos[primera] - datos[segunda]
            else:
                diferencia = pd.Series(dtype=float)
            valida = diferencia.dropna()
            filas.append({
                "dia": dia, "primera": primera, "segunda": segunda, "n": len(valida),
                "diferencia_media_MW": valida.mean(),
                "diferencia_absoluta_media_MW": valida.abs().mean(),
                "maxima_absoluta_MW": valida.abs().max(),
            })
    return pd.DataFrame(filas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archivo", type=Path, action="append", required=True)
    parser.add_argument(
        "--dias", nargs="+", required=True, type=lambda s: dt.date.fromisoformat(s).isoformat(),
    )
    parser.add_argument("--ieod", type=Path, action="append", default=[])
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    ieod = None
    for ruta in args.ieod:
        serie = pd.read_parquet(ruta, columns=["DateTime", "SEIN"]).set_index("DateTime")["SEIN"]
        ieod = serie if ieod is None else ieod.combine_first(serie)
    tabla = conciliar(args.archivo, set(args.dias), ieod)
    metricas = resumen(tabla)
    args.salida.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(args.salida / "media_hora.csv", index=False)
    metricas.to_csv(args.salida / "resumen.csv", index=False)
    print(metricas[metricas["n"] > 0].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
