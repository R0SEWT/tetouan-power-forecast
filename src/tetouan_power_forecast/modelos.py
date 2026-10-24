"""Envoltorios para que un regresor prediga el cambio o la razón del consumo en vez de su nivel."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.model_selection import TimeSeriesSplit

from tetouan_power_forecast.metricas import HORIZONTE
from tetouan_power_forecast.variables import ESCALA


class ModeloDelta(RegressorMixin, BaseEstimator):
    """Entrena `estimador` sobre y − X[columna_base] y suma esa columna al predecir.

    Con columna_base = "Zone1_t", el modelo aprende cuánto cambiará el consumo en una hora a
    partir del consumo actual. Así, un modelo de árboles puede predecir niveles que no vio en el
    entrenamiento (por ejemplo, los picos del verano), porque solo tiene que acertar el cambio.
    """

    def __init__(self, estimador, columna_base="Zone1_t"):
        self.estimador = estimador
        self.columna_base = columna_base

    def fit(self, X, y, **fit_params):
        self.estimador_ = clone(self.estimador).fit(X, np.asarray(y) - self._base(X), **fit_params)
        if hasattr(self.estimador_, "feature_names_in_"):
            self.feature_names_in_ = self.estimador_.feature_names_in_
        return self

    def predict(self, X):
        return self._base(X) + self.estimador_.predict(X)

    def _base(self, X):
        return np.asarray(X[self.columna_base], dtype=float)


class ModeloRazon(RegressorMixin, BaseEstimator):
    """Entrena `estimador` sobre y / X[columna_escala] y multiplica por esa columna al predecir.

    Con la media de 24 h como escala, el modelo aprende la forma del consumo respecto del último día,
    no su nivel. `estimador` no ve la columna de escala, y el envoltorio recibe y devuelve kW: se ajusta
    y se evalúa con las métricas de siempre, por ejemplo el MAE de una búsqueda de hiperparámetros.
    """

    def __init__(self, estimador, columna_escala=ESCALA):
        self.estimador = estimador
        self.columna_escala = columna_escala

    def fit(self, X, y, **fit_params):
        variables, escala = self._separar(X)
        self.estimador_ = clone(self.estimador).fit(variables, np.asarray(y) / escala, **fit_params)
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        return self

    def predict(self, X):
        variables, escala = self._separar(X)
        return escala * self.estimador_.predict(variables)

    def _separar(self, X):
        return X.drop(columns=self.columna_escala), np.asarray(X[self.columna_escala], dtype=float)


class CVPorFecha:
    """`TimeSeriesSplit` sobre las fechas únicas, para varias series apiladas (el modelo global).

    Todas las filas de una fecha caen del mismo lado, y entre entrenamiento y evaluación quedan `gap`
    fechas sin usar. Las fechas se pasan como `groups`.
    """

    def __init__(self, n_splits=5, gap=HORIZONTE):
        self.n_splits = n_splits
        self.gap = gap

    def split(self, X, y=None, groups=None):
        fechas = pd.Series(np.asarray(groups))
        unicas = np.sort(fechas.unique())
        for tr, te in TimeSeriesSplit(n_splits=self.n_splits, gap=self.gap).split(unicas):
            yield (np.flatnonzero(fechas.isin(unicas[tr]).to_numpy()),
                   np.flatnonzero(fechas.isin(unicas[te]).to_numpy()))

    def get_n_splits(self, X=None, y=None, groups=None):
        return self.n_splits
