"""Pruebas de la tubería en vivo con datos sintéticos: un portal del COES falso y un modelo falso, sin red ni torch."""

import datetime as dt
import html
import io
import json
import urllib.parse

import numpy as np
import openpyxl
import pandas as pd
import pytest

from tetouan_power_forecast import en_vivo as ev

LIMA_10_05 = pd.Timestamp("2026-10-26 15:05", tz="UTC")  # 10:05 en Lima
BASE = "Post Operación/Reportes/IEOD/"
MESES = {10: "10_Octubre", 11: "11_Noviembre"}


def _demanda(fechas, ruido=0.0, desplazamiento=0.0):
    """Norte, Centro y Sur con un ciclo diario y otro semanal; el SEIN es su suma."""
    fechas = pd.DatetimeIndex(fechas)
    hora = (fechas.hour + fechas.minute / 60).to_numpy()
    dia_semana = fechas.day_of_week.to_numpy()
    rng = np.random.default_rng(int(fechas[0].timestamp()) % 1000)
    ciclo = 1 + 0.08 * np.sin(2 * np.pi * (hora - 6) / 24) - 0.03 * (dia_semana >= 5)
    df = pd.DataFrame({"DateTime": fechas})
    for area, base in {"NORTE": 1100.0, "CENTRO": 4300.0, "SUR": 1850.0}.items():
        df[area] = base * ciclo + rng.normal(0, ruido, len(fechas)) + desplazamiento
    df["SEIN"] = df[["NORTE", "CENTRO", "SUR"]].sum(axis=1)
    return df[["DateTime", "SEIN", "NORTE", "CENTRO", "SUR"]]


def _periodos(dia):
    return pd.date_range(pd.Timestamp(dia) + ev.PASO, periods=48, freq="30min")


def _anexo(dia, desplazamiento=0.0, descuadre=0.0):
    """El anexo de 2026: la hora y los números como texto en DEMANDA_AREAS."""
    df = _demanda(_periodos(dia), ruido=3.0, desplazamiento=desplazamiento)
    libro = openpyxl.Workbook()
    libro.active.title = "RESUMEN"
    hoja = libro.create_sheet("DEMANDA_AREAS")
    hoja.append(["FECHA HORA", "DEMANDA", "AREA", "SUBAREAS"])
    hoja.append([None, "INTERCAMBIOS INTERNACIONALES", "SEIN", "NORTE", "CENTRO", "SUR", "ELECTROANDES"])
    for t, fila in zip(df["DateTime"], df.itertuples()):
        hora = "24:00" if t.hour == 0 and t.minute == 0 else f"{t:%H:%M}"
        hoja.append([hora, "0", f"{fila.SEIN + descuadre:.2f}", f"{fila.NORTE:.2f}", f"{fila.CENTRO:.2f}",
                     f"{fila.SUR:.2f}", "280"])
    hoja.append(["ENERGÍA", None, "150000"])
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


class COESFalso:
    """Responde como el navegador de archivos: carpetas del año, del mes y del día, y la descarga del anexo."""

    def __init__(self, publicados, firmas=None):
        self.publicados = dict(publicados)  # fecha -> bytes del anexo
        self.firmas = dict(firmas or {})
        self.pedidos = []

    @staticmethod
    def _ruta_dia(dia):
        return f"{BASE}{dia.year}/{MESES[dia.month]}/{dia.day:02d}/"

    def _anexo_de(self, dia):
        return f"{self._ruta_dia(dia)}AnexoA_{dia:%d%m}.xlsx"

    def __call__(self, url, datos=None, timeout=120):
        self.pedidos.append(url)
        if "download" in url:
            ruta = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["url"][0]
            dia = next(d for d in self.publicados if self._anexo_de(d) == ruta)
            return self.publicados[dia]
        ruta = datos["url"]
        if ruta == f"{BASE}2026/":
            return self._carpetas([f"{BASE}2026/{m}/" for m in MESES.values()])
        mes = next((m for m, nombre in MESES.items() if ruta == f"{BASE}2026/{nombre}/"), None)
        if mes is not None:
            return self._carpetas([self._ruta_dia(d) for d in self.publicados if d.month == mes])
        dia = next(d for d in self.publicados if self._ruta_dia(d) == ruta)
        return self._archivo(self._anexo_de(dia), self.firmas.get(dia, ("1,245.25 KB", "", "")))

    @staticmethod
    def _carpetas(rutas):
        return "".join(f"<li onclick=\"openBlob('{html.escape(r)}', 'D', '')\">x</li>" for r in rutas).encode()

    @staticmethod
    def _archivo(ruta, firma):
        celda = f"onclick=\"openBlob('{html.escape(ruta)}', 'F', '.xlsx')\""
        tamano, observacion, modificado = firma
        filas = [f'<td {celda}><img src="/x.png" /></td>', f"<td {celda}>{ruta.rsplit('/', 1)[1]}</td>",
                 f"<td style=text-align:right {celda}>{tamano}</td>", f"<td {celda}></td>", f"<td {celda}></td>",
                 f"<td {celda}>{observacion}</td>", f"<td {celda}>{modificado}</td>", f"<td {celda}></td>",
                 f"<td {celda}></td>"]
        return ("<table><tbody><tr>" + "\n".join(filas) + "</tr></tbody></table>").encode()

    def descargas(self):
        return sum("download" in u for u in self.pedidos)


class ModeloFalso:
    """Pronostica «la semana pasada a la misma hora» del objetivo, con un rango de ±50 MW."""

    nombre = "falso"

    def __init__(self, version="v1"):
        self.version = version
        self.origenes = []

    def pronosticar(self, demanda, origenes, progreso=print):
        self.origenes.append(len(origenes))
        filas = []
        for area in ev.AREAS:
            for origen in origenes:
                fila = {"DateTime": origen, "area": area}
                for p in ev.PASOS.values():
                    v = float(demanda.loc[origen + p * ev.PASO - 7 * ev.DIA, area])
                    fila.update({f"pred_{p}": v, f"q10_{p}": v - 50, f"q90_{p}": v + 50})
                filas.append(fila)
        return pd.DataFrame(filas)


def _dias(desde, n):
    return [desde + dt.timedelta(days=k) for k in range(n)]


@pytest.fixture
def raiz(tmp_path):
    """Una silver histórica de 60 días que termina, como la real, el 23 de octubre de 2026 a las 00:00."""
    fechas = pd.date_range("2026-08-24 00:30", "2026-10-23 00:00", freq="30min")
    destino = tmp_path / "coes" / "silver" / "demanda_areas.parquet"
    destino.parent.mkdir(parents=True)
    _demanda(fechas, ruido=3.0).to_parquet(destino, index=False)
    return tmp_path


def _portal(coes_falso):
    return ev.Portal(pedir=coes_falso, pausa=0)


def _silencio(*_):
    pass


# ---- Ingesta ------------------------------------------------------------------------------------------------------


def test_metadatos_del_listado_traen_tamano_y_observaciones():
    texto = COESFalso._archivo(f"{BASE}2026/11_Noviembre/11/AnexoA_1111.xlsx",
                               ("1,300.10 KB", "Se actualizó el despacho", "12/11/2026")).decode()
    firmas = ev.metadatos_listado(texto)
    assert list(firmas) == [f"{BASE}2026/11_Noviembre/11/AnexoA_1111.xlsx"]
    assert firmas[f"{BASE}2026/11_Noviembre/11/AnexoA_1111.xlsx"].startswith("1,300.10 KB")
    assert "Se actualizó el despacho" in next(iter(firmas.values()))


def test_ingesta_baja_lo_que_falta_y_empalma(raiz):
    falso = COESFalso({d: _anexo(d) for d in _dias(dt.date(2026, 10, 23), 3)})
    resultado = ev.ingerir(raiz, hoy=dt.date(2026, 10, 26), portal=_portal(falso), progreso=_silencio)
    assert resultado["nuevos"] == _dias(dt.date(2026, 10, 23), 3) and resultado["faltante"] is None
    vivo = ev.cargar_en_vivo(raiz)
    assert len(vivo) == 3 * 48 and vivo["DateTime"].iloc[0] == pd.Timestamp("2026-10-23 00:30")
    assert vivo["sha256"].str.len().eq(64).all()
    serie = ev.serie_completa(raiz)
    assert serie["DateTime"].iloc[-1] == pd.Timestamp("2026-10-26 00:00")
    assert (serie["DateTime"].diff().dropna() == ev.PASO).all()
    procedencia = [json.loads(x) for x in ev.rutas(raiz).procedencia.read_text().splitlines()]
    assert [x["fecha"] for x in procedencia] == ["2026-10-23", "2026-10-24", "2026-10-25"]
    assert (raiz / "coes/bronze/ieod_diario/2026-10-24/AnexoA_2410.xlsx").exists()
    # La silver histórica no se toca
    assert pd.read_parquet(raiz / "coes/silver/demanda_areas.parquet")["DateTime"].max() == pd.Timestamp("2026-10-23")
    # Una segunda corrida el mismo día no pide nada
    otro = COESFalso(falso.publicados)
    assert ev.ingerir(raiz, hoy=dt.date(2026, 10, 26), portal=_portal(otro), progreso=_silencio)["nuevos"] == []
    assert otro.pedidos == []


def test_ingesta_se_detiene_en_el_dia_sin_publicar(raiz):
    falso = COESFalso({d: _anexo(d) for d in (dt.date(2026, 10, 23), dt.date(2026, 10, 25))})
    resultado = ev.ingerir(raiz, hoy=dt.date(2026, 10, 26), portal=_portal(falso), progreso=_silencio)
    assert resultado["nuevos"] == [dt.date(2026, 10, 23)]
    assert resultado["faltante"] == dt.date(2026, 10, 24)
    assert falso.descargas() == 1  # el 25 espera: la serie no puede tener huecos
    assert "2026-10-24" in str(ev.AnexoNoPublicado(resultado["faltante"]))


def test_anexo_cuyas_areas_no_suman_el_sein_no_entra(raiz):
    falso = COESFalso({dt.date(2026, 10, 23): _anexo(dt.date(2026, 10, 23), descuadre=40.0)})
    with pytest.raises(ev.AnexoInvalido, match="no suman el SEIN"):
        ev.ingerir(raiz, hoy=dt.date(2026, 10, 24), portal=_portal(falso), progreso=_silencio)
    assert ev.cargar_en_vivo(raiz).empty


def test_salto_en_el_empalme_se_rechaza(raiz):
    falso = COESFalso({dt.date(2026, 10, 23): _anexo(dt.date(2026, 10, 23), desplazamiento=900.0)})
    with pytest.raises(ev.AnexoInvalido, match="salto en el empalme"):
        ev.ingerir(raiz, hoy=dt.date(2026, 10, 24), portal=_portal(falso), progreso=_silencio)


def test_capa_en_vivo_que_no_empalma_con_la_silver(raiz):
    df = _demanda(_periodos(dt.date(2026, 10, 24))).assign(sha256="x", archivo="x", descargado_utc="x")
    df.to_parquet(ev.rutas(raiz).en_vivo, index=False)
    with pytest.raises(ev.AnexoInvalido, match="no empalman"):
        ev.serie_completa(raiz)


def test_correccion_del_coes_cambia_el_real_y_guarda_las_dos_versiones(raiz):
    dias = _dias(dt.date(2026, 10, 23), 2)
    falso = COESFalso({d: _anexo(d) for d in dias})
    ev.ingerir(raiz, hoy=dt.date(2026, 10, 25), portal=_portal(falso), progreso=_silencio)
    antes = ev.cargar_en_vivo(raiz)
    # El COES corrige el 24 (cambia la firma del listado y el archivo) y publica el 25
    falso.publicados[dt.date(2026, 10, 24)] = _anexo(dt.date(2026, 10, 24), desplazamiento=5.0)
    falso.firmas[dt.date(2026, 10, 24)] = ("1,246.00 KB", "Se actualizó el despacho ejecutado", "25/10/2026")
    falso.publicados[dt.date(2026, 10, 25)] = _anexo(dt.date(2026, 10, 25))
    resultado = ev.ingerir(raiz, hoy=dt.date(2026, 10, 26), portal=_portal(falso), progreso=_silencio)
    assert resultado["nuevos"] == [dt.date(2026, 10, 25)]
    assert resultado["corregidos"] == [dt.date(2026, 10, 24)]
    despues = ev.cargar_en_vivo(raiz)
    del24 = (despues["DateTime"] > "2026-10-24") & (despues["DateTime"] <= "2026-10-25")
    assert np.allclose(despues.loc[del24, "NORTE"].to_numpy(), antes.loc[del24[:96], "NORTE"].to_numpy() + 5, atol=0.02)
    assert len(list((raiz / "coes/bronze/ieod_diario/2026-10-24").glob("*.xlsx"))) == 2
    estados = [json.loads(x)["estado"] for x in ev.rutas(raiz).procedencia.read_text().splitlines()]
    assert estados.count("corregido") == 1


# ---- Pronóstico y registro ----------------------------------------------------------------------------------------


def test_clasificar_por_el_sello_de_emision():
    objetivos = pd.DatetimeIndex(["2026-11-13 10:30", "2026-11-13 11:00", "2026-11-14 00:00", "2026-11-12 12:00"])
    emitido = pd.Timestamp("2026-11-13 15:00", tz="UTC")  # 10:00 en Lima: el periodo de 10:00 a 10:30 ya empezó
    assert list(ev.clasificar(emitido, objetivos)) == ["en_vivo", "ex_ante_estricto", "ex_ante_estricto",
                                                       "reconstruido"]


def _con_tres_dias(raiz):
    falso = COESFalso({d: _anexo(d) for d in _dias(dt.date(2026, 10, 23), 3)})
    ev.ingerir(raiz, hoy=dt.date(2026, 10, 26), portal=_portal(falso), progreso=_silencio)


def test_emision_registra_cada_tipo_y_no_se_repite(raiz):
    _con_tres_dias(raiz)
    modelo = ModeloFalso()
    agregadas = ev.emitir(raiz, modelo, ahora=lambda: LIMA_10_05, progreso=_silencio)
    registro = ev.leer_registro(raiz)
    # 24 h: del 23 al 26 (con datos hasta el 25); 1 h: del 23 al 25. Tres áreas, 48 periodos.
    assert agregadas == len(registro) == (4 + 3) * 3 * 48
    hoy = registro[registro["fecha_objetivo"] == pd.Timestamp("2026-10-26")]
    assert set(hoy["horizonte"]) == {"24h"}
    assert (hoy["origen"] == hoy["objetivo"] - ev.DIA).all()
    assert (hoy["datos_hasta"] == pd.Timestamp("2026-10-26")).all()
    # A las 10:05 ya empezaron los periodos de 00:00 a 10:00 (21): en vivo; el resto, ex ante estricto
    assert hoy.groupby("tipo").size().to_dict() == {"en_vivo": 21 * 3, "ex_ante_estricto": 27 * 3}
    antes = registro[registro["fecha_objetivo"] < pd.Timestamp("2026-10-26")]
    assert set(antes["tipo"]) == {"reconstruido"}
    una_hora = registro[registro["horizonte"] == "1h"]
    assert (una_hora["origen"] == una_hora["objetivo"] - pd.Timedelta(hours=1)).all()
    assert set(una_hora["tipo"]) == {"reconstruido"}
    assert registro["emitido_en"].dt.tz is not None
    assert registro["datos_sha256"].notna().sum() == len(registro) - 3 * 48  # el 23 a 24 h usa la silver histórica
    # Otra corrida no agrega nada ni toca lo emitido, y ni siquiera llama al modelo
    assert ev.emitir(raiz, modelo, ahora=lambda: LIMA_10_05 + pd.Timedelta(hours=3), progreso=_silencio) == 0
    pd.testing.assert_frame_equal(ev.leer_registro(raiz), registro)
    assert len(modelo.origenes) == 1
    # Una versión nueva de los pesos es otra serie de filas: no reescribe la anterior
    ev.emitir(raiz, ModeloFalso("v2"), desde=dt.date(2026, 10, 26), ahora=lambda: LIMA_10_05, progreso=_silencio)
    nuevo = ev.leer_registro(raiz)
    assert len(nuevo) == len(registro) + 3 * 48
    pd.testing.assert_frame_equal(nuevo.iloc[:len(registro)], registro)


def test_relleno_no_emite_el_dia_de_hoy(raiz):
    _con_tres_dias(raiz)
    ev.emitir(raiz, ModeloFalso(), hasta_objetivo=dt.date(2026, 10, 25), ahora=lambda: LIMA_10_05,
              progreso=_silencio)
    registro = ev.leer_registro(raiz)
    assert registro["fecha_objetivo"].max() == pd.Timestamp("2026-10-25")
    assert set(registro["tipo"]) == {"reconstruido"}


def test_feriados_fechados_por_el_inicio_del_periodo():
    pytest.importorskip("holidays")
    fechas = pd.DatetimeIndex(["2026-05-01 00:00", "2026-05-01 00:30", "2026-05-02 00:00", "2026-05-02 00:30"])
    assert list(ev.feriados(fechas)) == [0, 1, 1, 0]  # el 1 de mayo; las 00:00 del 2 cierran el día 1
    assert ev.feriados(pd.DatetimeIndex(["2031-12-25 12:00"]))[0] == 1  # sin años fijos


# ---- Evaluación y comando diario ----------------------------------------------------------------------------------


def test_evaluacion_separa_tipos_y_compara_con_la_referencia(raiz):
    _con_tres_dias(raiz)
    ev.emitir(raiz, ModeloFalso(), ahora=lambda: LIMA_10_05, progreso=_silencio)
    seguimiento, resumen = ev.evaluar(raiz, _silencio)
    # El 26 todavía no tiene real: solo se evalúa lo que ya llegó
    assert seguimiento["fecha_objetivo"].max() == pd.Timestamp("2026-10-25")
    assert len(seguimiento) == (3 + 3) * 3 * 48
    assert np.allclose(seguimiento["pred"], seguimiento["semana_pasada"])
    assert seguimiento["dentro"].mean() == 1.0  # el ruido es de 3 MW y el rango de ±50
    acum = resumen[(resumen["nivel"] == "acumulado") & (resumen["grupo"] == "reconstruido")]
    assert set(acum["horizonte"]) == {"1h", "24h"} and len(acum) == 6
    fila = acum[(acum["horizonte"] == "24h") & (acum["area"] == "CENTRO")].iloc[0]
    assert fila["dias"] == 3 and fila["periodos"] == 144
    assert fila["mae_modelo"] == pytest.approx(fila["mae_semana_pasada"])
    assert fila["referencia"] in ev.REFERENCIAS["24h"]
    assert np.isnan(fila["mae_persistencia"])  # a 24 h es lo mismo que «ayer»
    dias = resumen[(resumen["nivel"] == "dia") & (resumen["grupo"] == "reconstruido") & (resumen["area"] == "SUR")
                   & (resumen["horizonte"] == "24h")]
    assert len(dias) == 3 and (dias["referencia"] == fila["referencia"]).all()
    assert "en_vivo" not in set(resumen["grupo"])  # las filas en vivo (el 26) todavía no tienen real
    assert ev.rutas(raiz).seguimiento.exists() and ev.rutas(raiz).resumen.exists()


def test_diario_sale_con_75_si_el_anexo_de_ayer_no_esta(raiz):
    falso = COESFalso({d: _anexo(d) for d in _dias(dt.date(2026, 10, 23), 2)})
    codigo = ev.correr("diario", raiz, portal=_portal(falso), modelo=ModeloFalso(), hoy=dt.date(2026, 10, 26),
                       ahora=lambda: LIMA_10_05, progreso=_silencio)
    assert codigo == ev.SIN_PUBLICAR
    corrida = json.loads(ev.rutas(raiz).corridas.read_text().splitlines()[-1])
    assert corrida["codigo"] == 75 and "2026-10-25" in corrida["mensaje"] and corrida["duracion_s"] >= 0
    # Con lo que sí llegó, emite: 24 h hasta el 25 y 1 h hasta el 24
    assert ev.leer_registro(raiz)["fecha_objetivo"].max() == pd.Timestamp("2026-10-25")
    falso.publicados[dt.date(2026, 10, 25)] = _anexo(dt.date(2026, 10, 25))
    assert ev.correr("diario", raiz, portal=_portal(falso), modelo=ModeloFalso(), hoy=dt.date(2026, 10, 26),
                     ahora=lambda: LIMA_10_05, progreso=_silencio) == 0
    assert ev.leer_registro(raiz)["fecha_objetivo"].max() == pd.Timestamp("2026-10-26")


def test_diario_sale_con_3_si_el_anexo_es_invalido(raiz):
    falso = COESFalso({dt.date(2026, 10, 23): _anexo(dt.date(2026, 10, 23), descuadre=40.0)})
    codigo = ev.correr("diario", raiz, portal=_portal(falso), modelo=ModeloFalso(), hoy=dt.date(2026, 10, 24),
                       progreso=_silencio)
    assert codigo == ev.INVALIDO
    assert ev.leer_registro(raiz).empty


# ---- API: GET /en-vivo/{area} -------------------------------------------------------------------------------------


def _cliente(raiz):
    pytest.importorskip("fastapi")
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # Starlette recomienda httpx2; con httpx funciona igual
        from fastapi.testclient import TestClient
    from app.backend.main import crear_app
    from app.backend.pronosticador import PronosticadorDePrueba

    return TestClient(crear_app(PronosticadorDePrueba(), web=None, en_vivo=ev.rutas(raiz).reportes))


def test_api_en_vivo_muestra_el_ultimo_perfil_y_lo_verificado(raiz):
    _con_tres_dias(raiz)
    ev.emitir(raiz, ModeloFalso(), ahora=lambda: LIMA_10_05, progreso=_silencio)
    ev.evaluar(raiz, _silencio)
    cliente = _cliente(raiz)
    d = cliente.get("/en-vivo/centro").json()
    ultimo = d["ultimo"]
    assert ultimo["fecha"] == "2026-10-26" and ultimo["horizonte"] == "24h"
    assert len(ultimo["pronostico"]) == len(ultimo["inferior"]) == len(ultimo["superior"]) == 48
    assert ultimo["fecha_hora"][0] == "2026-10-26T00:00"  # la API marca el inicio del periodo
    assert ultimo["emitido_en"] == "2026-10-26T15:05:00Z" and ultimo["emitido_lima"] == "2026-10-26T10:05"
    assert ultimo["datos_hasta"] == "2026-10-26T00:00"
    assert ultimo["real"] == [None] * 48  # el real del 26 todavía no llega
    assert ultimo["tipo"].count("en_vivo") == 21 and ultimo["tipo"].count("ex_ante_estricto") == 27
    assert d["dias_en_vivo"] == 1 and d["primer_dia_en_vivo"] == "2026-10-26" and d["dias_reconstruidos"] == 3
    assert d["nivel_rango_pct"] == 80 and d["version_pesos"] == "v1"
    assert {(r["grupo"], r["horizonte"]) for r in d["resumen"]} == {("reconstruido", "24h"), ("reconstruido", "1h")}
    a24 = [v for v in d["verificado"] if v["horizonte"] == "24h"]
    assert [v["fecha"] for v in a24] == ["2026-10-25", "2026-10-24", "2026-10-23"]
    assert all(v["tipo"] == "reconstruido" and v["periodos"] == 48 for v in a24)
    assert cliente.get("/en-vivo/oeste").status_code == 404


def test_api_en_vivo_sin_registro(tmp_path):
    d = _cliente(tmp_path).get("/en-vivo/norte").json()
    assert d["ultimo"] is None and d["resumen"] == [] and d["verificado"] == [] and d["dias_en_vivo"] == 0
