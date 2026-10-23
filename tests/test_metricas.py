import pytest

from tetouan_power_forecast import metricas


def test_prediccion_perfecta_no_tiene_error():
    assert metricas([30_000, 32_000], [30_000, 32_000]) == (0, 0, 0)


def test_valores_conocidos():
    # Errores de 1 000 y 3 000 kW sobre consumos de 20 000 kW
    mae, rmse, mape = metricas([20_000, 20_000], [21_000, 17_000])
    assert mae == pytest.approx(2_000)
    assert rmse == pytest.approx((5_000_000) ** 0.5)
    assert mape == pytest.approx(10)


def test_acepta_series_de_pandas():
    pd = pytest.importorskip("pandas")
    mae, _, _ = metricas(pd.Series([10.0, 20.0]), pd.Series([12.0, 18.0]))
    assert mae == pytest.approx(2)
