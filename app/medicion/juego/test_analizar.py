"""Pruebas de la codificación del playtest sintético: ``pytest -q app/medicion/juego``."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analizar as a

PANTALLA = {
    "vistas": [{
        "archivo": "vista-1.png",
        "controles": [
            {"etiqueta": "Confianza", "tipo": "a", "zona": "#navPantallas"},
            {"etiqueta": "Detalle", "tipo": "a", "zona": "#navPantallas"},
            {"etiqueta": "2026-11-12", "tipo": "input:date", "valor": "2026-11-12", "zona": "cuando"},
            {"etiqueta": "+2 °C", "tipo": "button:button", "zona": "#escenarios"},
        ],
        "textos": [{"t": "El Niño costero (calentamiento del mar frente a la costa): extraordinario",
                    "zona": "regimen"}],
    }],
}
REGLA_T4 = {"aciertos": ["^confianza$", "diagnostico"], "aceptables": ["^detalle$"]}


def test_numeros_con_coma_o_punto_de_miles_y_decimales():
    assert a.numeros("4,456 MW y 4.456 MW") == [4456.0, 4456.0]
    assert a.numeros("71,9 MW; 1.66 %; 4 588") == [71.9, 1.66, 4588.0]
    assert a.numeros("1,234.5") == [1234.5]


def test_calza_con_tolerancia_segun_magnitud():
    assert a.calza("unos 4,784 MW", [4784.4])
    assert a.calza("se equivoca 72 MW", [71.9])
    assert a.calza("1,7 %", [1.66])
    assert not a.calza("4,800 MW", [4784.4])


def test_primer_clic_acierto_aceptable_falsa_affordance_y_no_sabe():
    assert a.calificar_clic("Confianza", PANTALLA, REGLA_T4)["resultado"] == "acierto"
    assert a.calificar_clic("«Detalle»", PANTALLA, REGLA_T4)["resultado"] == "aceptable"
    chip = a.calificar_clic("El Niño costero (calentamiento del mar frente a la costa)", PANTALLA, REGLA_T4)
    assert chip["resultado"] == "no_es_control" and chip["zona"] == "regimen"
    assert a.calificar_clic("no sé", PANTALLA, REGLA_T4)["resultado"] == "no_sabe"


def test_una_fecha_citada_se_ubica_en_su_campo():
    lugar = a.ubicar("11/12/2026", PANTALLA)
    assert lugar["tipo"] == "control" and lugar["zona"] == "cuando"


def test_boton_de_mas_dos_grados():
    assert a.calificar_clic("+2 °C", PANTALLA, {"aciertos": [a.CLIC_2C]})["resultado"] == "acierto"


def test_embudo_acumula_los_pasos():
    base = {"comprende": True, "lectura_cifra": True, "momento_ok": True, "volveria": "si",
            "clics": {t: {"resultado": "acierto"} for t in ("t1", "t2", "t3", "t4")}}
    pierde = {**base, "lectura_cifra": False}
    filas = a.embudo([base, pierde])
    assert [f["quedan"] for f in filas] == [2, 2, 1, 1, 1, 1]


def test_terminos_canonicos():
    assert a.termino("megavatios (MW)") == "MW / megavatios"
    assert a.termino("Rango del 80 %") == "rango del N %"


def test_la_etiqueta_de_un_campo_cuenta_como_el_campo():
    pantalla = {"vistas": [{
        "archivo": "vista-1.png",
        "controles": [{"etiqueta": "2026-11-12", "tipo": "input:date", "zona": "cuando"},
                      {"etiqueta": "07:00", "tipo": "input:time", "zona": "cuando"}],
        "textos": [{"t": "Ver otro día", "zona": "cuando"}, {"t": "A las", "zona": "cuando"}],
    }]}
    regla = {"aciertos": ["ver otro dia"], "aceptables": ["\\ba las\\b"]}
    assert a.calificar_clic("Ver otro día", pantalla, regla)["resultado"] == "acierto"
    assert "input:time" in a.ubicar("A las", pantalla)["etiqueta"]
