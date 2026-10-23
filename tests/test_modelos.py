import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression

from tetouan_power_forecast.modelos import ModeloDelta


def _datos():
    X = pd.DataFrame({"Zone1_t": [100.0, 400.0, 200.0, 300.0], "x": [1.0, 2.0, 3.0, 4.0]})
    y = X["Zone1_t"] + 10 * X["x"]
    return X, y


def test_con_cambio_cero_equivale_a_persistencia():
    X, y = _datos()
    modelo = ModeloDelta(DummyRegressor(strategy="constant", constant=0)).fit(X, y)
    np.testing.assert_allclose(modelo.predict(X), X["Zone1_t"])


def test_aprende_el_cambio_y_extrapola_el_nivel():
    X, y = _datos()
    modelo = ModeloDelta(LinearRegression()).fit(X, y)
    nuevo = pd.DataFrame({"Zone1_t": [10_000.0], "x": [5.0]})  # nivel nunca visto
    np.testing.assert_allclose(modelo.predict(nuevo), [10_050.0])


def test_es_clonable_para_busqueda_de_hiperparametros():
    modelo = ModeloDelta(LinearRegression(), columna_base="Zone1_t")
    copia = clone(modelo).set_params(estimador__fit_intercept=False)
    assert copia.get_params()["estimador__fit_intercept"] is False
