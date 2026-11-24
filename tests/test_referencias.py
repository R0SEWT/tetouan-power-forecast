import numpy as np
import pandas as pd
import pytest

from tetouan_power_forecast.referencias import referencias

PASO = pd.Timedelta(minutes=30)


def test_delta_de_origen_fijo_no_lee_datos_futuros():
    indice = pd.date_range("2025-01-01", periods=50 * 48, freq=PASO)
    serie = pd.Series(np.arange(len(indice), dtype=float) + 100, index=indice)
    origen = indice[-150]
    objetivos = [origen + pd.Timedelta(hours=5), origen + pd.Timedelta(hours=26)]
    resultado = referencias(serie, [origen, origen], objetivos, PASO)
    pd.testing.assert_frame_equal(
        resultado, referencias(serie.loc[:origen], [origen, origen], objetivos, PASO),
    )
    dato = objetivos[1] - pd.Timedelta(days=2)
    hace_dos_dias = origen - pd.Timedelta(days=2)
    assert resultado.iloc[1]["delta_diario"] == serie[origen] + serie[dato] - serie[hace_dos_dias]


def test_rezago_busca_fecha_exacta_y_no_el_renglon_anterior():
    indice = pd.date_range("2025-01-01", periods=50 * 48, freq=PASO)
    serie = pd.Series(100.0, index=indice)
    origen = indice[-3]
    objetivo = origen + PASO
    serie = serie.drop(objetivo - pd.Timedelta(days=1))
    resultado = referencias(serie, [origen], [objetivo], PASO).iloc[0]
    assert np.isnan(resultado["delta_diario"])
    assert resultado["delta_semanal"] == 100


def test_referencias_rechazan_claves_duplicadas():
    indice = pd.date_range("2025-01-01", periods=50 * 48, freq=PASO)
    serie = pd.Series(100.0, index=indice)
    with pytest.raises(ValueError, match="pares únicos"):
        referencias(serie, [indice[-2]] * 2, [indice[-1]] * 2, PASO)
