#!/usr/bin/env python3
"""Prueba de humo de Curva publicada: pide desde afuera la salud, los endpoints principales y la web.

Solo usa la biblioteca estándar, así que corre en cualquier máquina con Python (sin el entorno del proyecto):

    python despliegue/humo.py https://curva-sein.azurewebsites.net
    python despliegue/humo.py https://curva-sein.azurewebsites.net --esperar 900   # tras un despliegue o reinicio

Falla (código 1) si la app no responde, si ``/salud`` trae un aviso (por ejemplo, que se cayó a los datos de prueba
porque no bajaron los reales) o si algún pedido no da lo esperado. Muestra cuánto tardó cada pedido.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

AREAS = ("norte", "centro", "sur")
AGENTE = "curva-humo/1"


class ErrorHumo(AssertionError):
    """Un pedido no dio lo esperado."""


def pedir(base: str, ruta: str, cuerpo: dict | None = None, timeout: float = 60) -> tuple[int, object, float, int]:
    """El código, la respuesta (JSON o texto), los segundos y los bytes de un pedido."""
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pedido = urllib.request.Request(base.rstrip("/") + ruta, data=datos, method="POST" if datos else "GET",
                                    headers={"User-Agent": AGENTE, "Accept-Encoding": "identity",
                                             **({"Content-Type": "application/json"} if datos else {})})
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as r:
            codigo, texto = r.status, r.read()
    except urllib.error.HTTPError as error:
        codigo, texto = error.code, error.read()
    segundos = time.perf_counter() - inicio
    try:
        valor = json.loads(texto)
    except ValueError:
        valor = texto.decode(errors="replace")
    return codigo, valor, segundos, len(texto)


def esperar_salud(base: str, segundos: float) -> dict:
    """Pide ``/salud`` hasta que responda 200 o se acabe el plazo. Devuelve la salud."""
    limite, ultimo = time.monotonic() + segundos, "sin respuesta"
    while True:
        try:
            codigo, valor, _, _ = pedir(base, "/salud", timeout=30)
            if codigo == 200 and isinstance(valor, dict):
                return valor
            ultimo = f"HTTP {codigo}"
        except OSError as error:  # todavía arrancando (502/503 de la plataforma, conexión cortada)
            ultimo = str(error)
        if time.monotonic() >= limite:
            raise ErrorHumo(f"/salud no respondió en {segundos:.0f} s (último: {ultimo})")
        time.sleep(10)


def comprobar(base: str, mostrar=print) -> list[tuple[str, int, float, int]]:
    """Los pedidos de la prueba. Devuelve (ruta, código, segundos, bytes) de cada uno; falla en el primero que no va."""
    filas = []

    def get(ruta, cuerpo=None, tipo=dict):
        codigo, valor, segundos, peso = pedir(base, ruta, cuerpo)
        filas.append((("POST " if cuerpo else "GET ") + ruta, codigo, segundos, peso))
        mostrar(f"  {codigo}  {segundos * 1000:7.0f} ms  {peso / 1024:8.1f} KB  {filas[-1][0]}")
        if codigo != 200 or not isinstance(valor, tipo):
            raise ErrorHumo(f"{filas[-1][0]}: HTTP {codigo} {str(valor)[:200]}")
        return valor

    salud = get("/salud")
    if salud.get("aviso"):
        raise ErrorHumo(f"/salud trae un aviso: {salud['aviso']}")
    if salud.get("modelo") == "prueba":
        raise ErrorHumo("/salud dice que corre el modelo de prueba (datos sintéticos), no el real")
    modelos = get("/modelos", tipo=list)
    if not modelos:
        raise ErrorHumo("/modelos vino vacío")
    if len(get("/areas", tipo=list)) != len(AREAS):
        raise ErrorHumo("/areas no trae las tres áreas")
    get("/resumen")
    fecha = modelos[0].get("fecha_max") or "2026-02-26"
    for area in AREAS:
        ahora = get(f"/ahora/{area}")
        if not ahora:
            raise ErrorHumo(f"/ahora/{area} vino vacío")
        get(f"/confianza/{area}")
    get(f"/series/norte?fecha={fecha}&horizonte=24h")
    get("/pronostico", {"area": "centro", "origen": f"{fecha}T12:00", "horizonte": "24h"})
    get("/en-vivo/sur")
    html = get("/", tipo=str)
    if "<html" not in html.lower():
        raise ErrorHumo("/ no devolvió la web")
    for recurso in sorted(set(re.findall(r'(?:src|href)="(?:\./|/)?([\w.-]+\.(?:js|css))(?=["?])', html))):
        get(f"/{recurso}", tipo=str)
    return filas


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Prueba de humo de Curva publicada (salud, endpoints y web).")
    p.add_argument("url", help="la URL pública, por ejemplo https://curva-sein.azurewebsites.net")
    p.add_argument("--esperar", type=float, default=60,
                   help="segundos máximos esperando a que /salud responda (60; tras un reinicio, 900)")
    args = p.parse_args(argv)
    try:
        inicio = time.monotonic()
        salud = esperar_salud(args.url, args.esperar)
        print(f"Salud tras {time.monotonic() - inicio:.0f} s: modelo {salud.get('modelo')}, "
              f"datos {salud.get('version_datos')}, aviso {salud.get('aviso')}")
        filas = comprobar(args.url)
    except (ErrorHumo, OSError) as error:
        print(f"FALLA: {error}", file=sys.stderr)
        return 1
    tiempos = sorted(s for _, _, s, _ in filas)
    print(f"OK: {len(filas)} pedidos; mediana {tiempos[len(tiempos) // 2] * 1000:.0f} ms, "
          f"máximo {tiempos[-1] * 1000:.0f} ms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
