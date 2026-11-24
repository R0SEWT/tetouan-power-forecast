import io

import pytest
from openpyxl import Workbook

from experimentos.en_vivo.conciliar_coes import leer_pdo, rejilla


def anexo(hora_final):
    libro = Workbook()
    hoja = libro.active
    hoja.append(["Día Hora", "Demanda YUPANA", "Demanda COES"])
    for i, hora in enumerate(rejilla("2026-11-23").strftime("%H:%M"), start=1):
        hoja.append([hora_final if i == 48 else hora, 100 + i, 200 + i])
    memoria = io.BytesIO()
    libro.save(memoria)
    return memoria.getvalue()


def test_h48_del_anexo_es_el_cierre_que_figura_como_medianoche_en_el_portal():
    datos = leer_pdo(anexo("23:59"), "2026-11-23")
    assert len(datos) == 48
    assert datos.index[-1].isoformat() == "2026-11-24T00:00:00"
    assert datos.iloc[-1].to_dict() == {"pdo_yupana": 148.0, "pdo_coes": 248.0}


def test_no_acepta_otra_hora_como_cierre_del_anexo():
    with pytest.raises(ValueError, match="Rejilla inesperada"):
        leer_pdo(anexo("23:57"), "2026-11-23")
