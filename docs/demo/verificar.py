"""Comprueba que la app levantada muestra las cifras que dice el guion de la demo.

Uso (con la app ya levantada; lo llama docs/demo/demo.sh):

    python docs/demo/verificar.py --api http://localhost:8000

Solo usa la biblioteca estándar. Sale con 0 si todo lo que se dice en la demo coincide, con 1 si algo de lo que se
dice no coincide (entonces la demo va al plan B o hay que corregir la frase) y con 2 si la API no responde. Las
cifras de «en vivo» cambian cada día: no se comparan, se imprimen para leerlas de la pantalla.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

LIMA = timezone(timedelta(hours=-5))  # Perú no tiene horario de verano

# Lo que dice el guion (docs/demo/README.md). Si cambian los modelos, cambian estas cifras y las frases.
DIA = "2026-08-27T19:00"  # paso 2: el día de repaso
PICO = "2026-08-28T15:00"  # paso 2: el pico que se toca; desde ahí se abre «¿Y si…?» (paso 3)
RESPALDO = "2026-03-10T19:00"  # el día de respaldo
RESPALDO_PICO = "2026-03-11T14:30"
ESPERADO = {
    DIA: {"dijimos": 4810, "inferior": 4629, "superior": 4974, "fue": 4772},
    PICO: {"dijimos": 5007, "inferior": 4819, "superior": 5178, "fue": 5027},
    RESPALDO: {"dijimos": 4767, "inferior": 4588, "superior": 4929, "fue": 4784},
    RESPALDO_PICO: {"dijimos": 4977, "inferior": 4790, "superior": 5146, "fue": 4961},
}
ESCENARIO = {PICO: 8, RESPALDO_PICO: 20}  # MW que sube el pico con +2 °C (XGBoost base)
CONFIANZA = {"1h": {"mae_modelo": 48.8}, "24h": {"mae_modelo": 71.9, "mae_referencia": 135.4,
                                                "cobertura_pct": 91.1}}
NOMBRES = {"mae_modelo": "error (MW)", "mae_referencia": "referencia (MW)",
           "cobertura_pct": "cobertura del 90 % (%)"}


class Informe:
    def __init__(self):
        self.fallas = 0

    def ok(self, texto):
        print(f"  OK     {texto}")

    def aviso(self, texto):
        print(f"  AVISO  {texto}")

    def falla(self, texto):
        self.fallas += 1
        print(f"  FALLA  {texto}")


def pedir(api, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pedido = urllib.request.Request(api + ruta, data=datos, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=60) as respuesta:
        return json.load(respuesta)


def revisar_salud(api, inf):
    salud = pedir(api, "/salud")
    if salud.get("estado") == "ok" and salud.get("modelo", "").startswith("Combinado"):
        inf.ok(f"Modelo real: {salud['modelo']} ({salud.get('version_datos')})")
        return True
    inf.falla(f"La app no responde con el modelo combinado sino con «{salud.get('modelo')}». Si dice «prueba», "
              "no encontró los datos (TETOUAN_DATA): la demo va al plan B.")
    return False


def revisar_momento(api, inf, origen, critico):
    esperado = ESPERADO[origen]
    d = pedir(api, f"/ahora/centro?origen={origen}&variante=M0")
    a = d.get("ayer") or {}
    visto = {"dijimos": a.get("pronostico"), "inferior": a.get("inferior"), "superior": a.get("superior"),
             "fue": a.get("real")}
    visto = {k: round(v) if v is not None else None for k, v in visto.items()}
    etiqueta = f"Repaso {origen.replace('T', ' ')}"
    if visto == esperado and a.get("dentro") and d.get("modelo") == "combinado":
        inf.ok(f"{etiqueta}: dijimos {visto['dijimos']:,} ({visto['inferior']:,}–{visto['superior']:,}), "
               f"fue {visto['fue']:,}")
    else:
        texto = f"{etiqueta}: se esperaba {esperado}, la app muestra {visto} (modelo {d.get('modelo')})"
        inf.falla(texto) if critico else inf.aviso(texto)


def revisar_escenario(api, inf, origen):
    pedido = {"area": "centro", "origen": origen, "horizonte": "24h", "variante": "M3", "modelo": "XGBoost global"}
    base = pedir(api, "/pronostico", pedido)["pronostico"]
    calor = pedir(api, "/pronostico", {**pedido, "escenario": {"delta_temp_c": 2}})["pronostico"]
    pico = max(range(len(base)), key=base.__getitem__)
    cambio = round(calor[pico] - base[pico])
    if cambio == ESCENARIO[origen]:
        inf.ok(f"«¿Y si…?» desde {origen.replace('T', ' ')}: +2 °C sube el pico {cambio:+d} MW")
    else:
        inf.aviso(f"«¿Y si…?» desde {origen.replace('T', ' ')}: el guion dice {ESCENARIO[origen]:+d} MW y la app "
                  f"calcula {cambio:+d} MW. Di la cifra de la pantalla (¿cambiaron los modelos?).")


def revisar_confianza(api, inf):
    for horizonte, esperado in CONFIANZA.items():
        d = pedir(api, f"/confianza/centro?horizonte={horizonte}&variante=M0")
        total = d["seguimiento"]["total"]
        visto = {k: total.get(k) for k in esperado}
        meses = d["seguimiento"]["meses"]
        ganados = sum(m["mae_modelo"] < m["mae_referencia"] for m in meses)
        texto = ", ".join(f"{NOMBRES[k]} {v}" for k, v in visto.items())
        if visto == esperado and ganados == len(meses) == 10:
            inf.ok(f"Confianza, Centro a {horizonte}: {texto}; le gana a la referencia {ganados} de "
                   f"{len(meses)} meses")
        else:
            inf.falla(f"Confianza, Centro a {horizonte}: se esperaba {esperado} y 10 de 10 meses; la app "
                      f"muestra {texto} y {ganados} de {len(meses)}")


def revisar_en_vivo(api, inf, hoy):
    d = pedir(api, "/en-vivo/centro")
    ultimo = d.get("ultimo")
    if not ultimo:
        inf.aviso("No hay registro en vivo: el paso 1 mostrará el último día del historial. Usa el respaldo del "
                  "README (paso 1 sin dato nuevo).")
        return
    fecha = datetime.strptime(ultimo["fecha"], "%Y-%m-%d").date()
    real_hasta = (fecha - timedelta(days=1)).strftime("%d/%m")
    if fecha == hoy:
        inf.ok(f"En vivo: el pronóstico de hoy se emitió a las {ultimo['emitido_lima'][11:]} con datos del COES "
               f"hasta el {real_hasta}, 24:00")
    elif fecha == hoy - timedelta(days=1):
        inf.aviso(f"En vivo: todavía no hay pronóstico de hoy (el último es del {fecha:%d/%m}). El COES publica "
                  "hacia las 09:45 y la corrida reintenta cada 30 minutos hasta las 17:30. Si sigue así a la "
                  "hora de exponer, di la frase del README para «sin dato nuevo».")
    else:
        dias = (hoy - fecha).days
        inf.aviso(f"En vivo: el registro está atrasado {dias} días (último pronóstico: {fecha:%d/%m}). En esta "
                  "máquina no corre la corrida diaria: actualízalo con docs/demo/demo.sh --descargar.")
    vivo = next((r for r in d.get("resumen", []) if r["grupo"] == "en_vivo" and r["horizonte"] == "24h"), None)
    if vivo:
        print(f"         Para leer en «Confianza» (paso 4): en vivo, {vivo['dias']} días, el rango del 80 % "
              f"cubrió el {vivo['cobertura_pct']:.1f} % (Centro); error {vivo['mae_modelo']:.1f} MW frente a "
              f"{vivo['mae_referencia']:.1f} de la referencia.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", default="http://localhost:8000", help="URL de la API (por defecto :8000)")
    parser.add_argument("--hoy", help="Fecha de hoy en Lima, AAAA-MM-DD (por defecto, la del reloj)")
    args = parser.parse_args(argv)
    api = args.api.rstrip("/")
    hoy = (datetime.strptime(args.hoy, "%Y-%m-%d").date() if args.hoy
           else datetime.now(LIMA).date())
    inf = Informe()
    print(f"Cifras de la demo contra {api}:")
    try:
        if revisar_salud(api, inf):
            revisar_momento(api, inf, DIA, critico=True)
            revisar_momento(api, inf, PICO, critico=True)
            revisar_escenario(api, inf, PICO)
            revisar_confianza(api, inf)
            revisar_momento(api, inf, RESPALDO, critico=False)
            revisar_momento(api, inf, RESPALDO_PICO, critico=False)
            revisar_escenario(api, inf, RESPALDO_PICO)
        revisar_en_vivo(api, inf, hoy)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        print(f"  FALLA  La API no responde en {api}: {error}")
        return 2
    if inf.fallas:
        print(f"{inf.fallas} cifra(s) no coinciden con el guion: revisa arriba antes de exponer.")
        return 1
    print("Todo lo que se dice en la demo coincide con la app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
