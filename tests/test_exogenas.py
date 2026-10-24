import datetime as dt
import json

import openpyxl
import pandas as pd
import pytest

from tetouan_power_forecast.exogenas import (
    bronze_era5,
    fallas_en_curso,
    icen_disponible,
    leer_eventos,
    leer_icen,
    leer_nino12_semanal,
    leer_saidi,
    nino12_disponible,
    saidi_por_area,
    temperatura_por_area,
)

ICEN = """% Índice Costero El Niño (ICEN; ENFEN, 2024)
% yy   mm   ICEN
2026   5    1.90
2026   6    2.66
2026   7    3.38
2026   8    3.98
"""

NINO12 = """ Weekly SST data starts week centered on 2Sept1981

                Nino1+2      Nino3        Nino34        Nino4
 Week          SST SSTA     SST SSTA     SST SSTA     SST SSTA
 30SEP2026     25.9 5.3     28.8 3.9     29.9 3.2     29.8 1.2
 07OCT2026     26.1 5.2     29.0 4.1     30.0 3.3     29.9 1.3
 14OCT2026     26.2-0.2     29.2 4.2     30.0 3.3     29.7 1.1
"""


def test_icen_entra_segun_su_publicacion():
    icen = leer_icen(ICEN)
    assert icen["icen"].iloc[-1] == 3.98 and icen["mes"].iloc[-1] == pd.Timestamp("2026-08-01")
    # El 25 de octubre ya salió el definitivo de agosto (m−2); el 10 de octubre todavía no: se usa julio (m−3)
    serie = icen_disponible(pd.to_datetime(["2026-10-25 12:00", "2026-10-10 12:00"]), icen)
    assert list(serie) == [3.98, 3.38]


def test_nino12_semanal_con_columnas_pegadas_y_rezago():
    nino = leer_nino12_semanal(NINO12)
    assert len(nino) == 3 and nino["nino12_ssta"].tolist() == [5.3, 5.2, -0.2]
    serie = nino12_disponible(pd.to_datetime(["2026-10-15", "2026-10-16"]), nino)
    # La semana del 7-oct se publica el 16-oct; el 15 solo se conoce la del 30-sep
    assert serie.tolist() == [5.3, 5.2]


def test_era5_por_area_es_la_media_de_sus_ciudades(tmp_path):
    def descargar(url):
        lat = float(url.split("latitude=")[1].split("&")[0])
        horas = pd.date_range("2026-01-01", periods=3, freq="h")
        return json.dumps({"hourly": {"time": [f"{h:%Y-%m-%dT%H:%M}" for h in horas],
                                      "temperature_2m": [abs(lat)] * 3, "apparent_temperature": [0] * 3,
                                      "relative_humidity_2m": [50] * 3}}).encode()

    ciudades = {"norte": {"A": (-5.0, -80.0), "B": (-7.0, -79.0)}, "centro": {"Lima": (-12.0, -77.0)}}
    bronze_era5(tmp_path, ciudades=ciudades, desde=dt.date(2026, 1, 1), hasta=dt.date(2026, 1, 1),
                descargar=descargar, progreso=lambda texto: None)
    tabla = temperatura_por_area(tmp_path, ciudades=ciudades)
    assert tabla["norte"].tolist() == [6.0] * 3 and tabla["centro"].tolist() == [12.0] * 3
    ponderada = temperatura_por_area(tmp_path, ciudades=ciudades, pesos={"norte": {"A": 3, "B": 1}})
    assert ponderada["norte"].iloc[0] == pytest.approx(5.5)

    def falla(url):
        raise AssertionError("no debía volver a descargar")

    bronze_era5(tmp_path, ciudades=ciudades, descargar=falla, progreso=lambda texto: None)


def test_saidi_por_area_con_la_mediana_y_lo_no_asignado():
    csv = ("﻿FECHA_CORTE,FECHA_EMISION,AÑO,MES,CODIGO_EMPRESA,NOMBRE_EMPRESA,COD_SIST_ELEC,NOM_SIST_ELEC,"
           "SAIDI,SAIDI_GEN,SAIDI_TRA,SAIDI_DIS,SAIFI,SAIFI_GEN,SAIFI_TRA,SAIFI_DIS\n"
           "20260507,20260331,2026,202603,ENO,ENOSA,S1,A,7.0,0,0,7.0,1,0,0,1\n"
           "20260507,20260331,2026,202603,ENO,ENOSA,S2,B,1.0,0,0,1.0,1,0,0,1\n"
           "20260507,20260331,2026,202603,ENO,ENOSA,S3,C,3.0,0,0,3.0,1,0,0,1\n"
           "20260507,20260331,2026,202603,LDS,LUZ DEL SUR S.A.A.,S4,D,2.0,0,0,2.0,1,0,0,1\n"
           "20260507,20260331,2026,202603,XYZ,OTRA,S5,E,9.0,0,0,9.0,1,0,0,1\n").encode()
    saidi = leer_saidi(csv)
    assert saidi["mes"].iloc[0] == pd.Timestamp("2026-03-01") and "saidi_dis" in saidi.columns
    mapa = pd.DataFrame({"empresa_coes": ["Enosa", "Luz del Sur S.A.A."], "area": ["norte", "centro"]})
    por_area = saidi_por_area(saidi, mapa).iloc[0]
    assert por_area["norte"] == 3.0 and por_area["centro"] == 2.0 and por_area["sin_area"] == 1


def test_eventos_y_fallas_en_curso(tmp_path):
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.append([None])
    hoja.append(["CONSULTA DE EVENTOS"])
    hoja.append(["FECHA DESDE: ", "01/01/2017"])
    hoja.append(["Empresa", "Ubicación", "Familia", "Equipo", "Inicio", "Final", "Descripción"])
    hoja.append(["REP", "S.E. Chiclayo", "LINEA", "L-2238", dt.datetime(2017, 3, 2, 10, 0),
                 dt.datetime(2017, 3, 2, 11, 0), "Desconexión"])
    hoja.append(["ENOSA", "S.E. Piura", "TRANSFORMADOR", "T1", "02/03/2017 10:30", "02/03/2017 12:00", "Falla"])
    libro.save(tmp_path / "2017.xlsx")
    eventos = leer_eventos(tmp_path / "2017.xlsx")
    assert len(eventos) == 2 and eventos["inicio"].iloc[1] == pd.Timestamp("2017-03-02 10:30")
    en_curso = fallas_en_curso(pd.to_datetime(["2017-03-02 09:00", "2017-03-02 10:45", "2017-03-02 11:30",
                                               "2017-03-02 12:00"]), eventos)
    assert en_curso.tolist() == [0, 2, 1, 0]
