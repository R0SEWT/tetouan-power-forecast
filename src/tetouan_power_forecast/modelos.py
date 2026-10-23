"""Envoltorio para que un regresor prediga el cambio del consumo en vez de su nivel."""

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin, clone


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
