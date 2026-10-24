import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

from tetouan_power_forecast.modelos import CVPorFecha, ModeloDelta, ModeloRazon


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


def test_razon_aprende_la_forma_y_predice_en_kw_un_nivel_nunca_visto():
    X = pd.DataFrame({"media_24h": [100.0, 200.0, 300.0, 400.0], "x": [1.0, 2.0, 3.0, 4.0]})
    y = X["media_24h"] * (1 + 0.1 * X["x"])  # la razón depende solo de x
    modelo = ModeloRazon(LinearRegression()).fit(X, y)
    assert list(modelo.estimador_.feature_names_in_) == ["x"]  # el estimador no ve la escala
    nuevo = pd.DataFrame({"media_24h": [10_000.0], "x": [5.0]})
    np.testing.assert_allclose(modelo.predict(nuevo), [15_000.0])


def test_razon_en_una_busqueda_con_validacion_temporal():
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"media_24h": rng.uniform(100, 200, 60), "x": rng.normal(size=60)})
    y = X["media_24h"] * (1 + 0.05 * X["x"])
    busqueda = GridSearchCV(ModeloRazon(Ridge()), {"estimador__alpha": [0.01, 100.0]},
                            cv=TimeSeriesSplit(n_splits=3, gap=6), scoring="neg_mean_absolute_error").fit(X, y)
    assert busqueda.best_params_ == {"estimador__alpha": 0.01}


def test_cv_por_fecha_no_parte_una_fecha_y_deja_el_hueco():
    fechas = np.repeat(pd.date_range("2017-01-01", periods=40, freq="10min"), 3)  # tres zonas apiladas
    for tr, te in CVPorFecha(n_splits=4, gap=6).split(np.zeros(len(fechas)), groups=fechas):
        assert not set(fechas[tr]) & set(fechas[te])
        assert len(tr) % 3 == 0 and len(te) % 3 == 0
        assert fechas[te].min() - fechas[tr].max() == pd.Timedelta(minutes=70)  # 6 fechas sin usar
