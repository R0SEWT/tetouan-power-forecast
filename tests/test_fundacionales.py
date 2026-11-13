import numpy as np
import pandas as pd
import pytest

from tetouan_power_forecast.fundacionales import (
    ELEGIDO,
    NOMBRE_ELEGIDO,
    TRAMOS,
    alinear,
    cargar_pronosticos,
    cobertura,
    combinar_modelos,
    comparar,
    peso_combinacion,
    separar_nombre,
)
from tetouan_power_forecast.variables_sein import AREAS, HORIZONTES, REFERENCIAS


def _escenario(tmp_path, ruido_modelo=1.0, ruido_elegido=5.0, dias=20):
    """Reportes y pronósticos sintéticos: el modelo "bueno" se equivoca menos que el elegido."""
    rng = np.random.default_rng(0)
    reportes, carpeta = tmp_path / "reportes", tmp_path / "fundacionales"
    carpeta.mkdir()
    partes = []
    for tramo, prefijo in TRAMOS.items():
        fechas = pd.date_range(f"{tramo}-01-01", periods=48 * dias, freq="30min")
        (reportes / prefijo).parent.mkdir(parents=True, exist_ok=True)
        for area in AREAS:
            pron = {"DateTime": fechas, "area": area}
            for h, paso in HORIZONTES.items():
                real = 1000 + 100 * np.sin(np.arange(len(fechas)) * 2 * np.pi / 48) + rng.normal(0, 1, len(fechas))
                base = pd.DataFrame({"DateTime": fechas, "real": real, ELEGIDO: real + rng.normal(0, ruido_elegido, len(fechas))})
                for r in REFERENCIAS:
                    base[r] = real + rng.normal(0, 20, len(fechas))
                base.to_csv(reportes / f"{prefijo}_{h}_{area.lower()}.csv", index=False)
                pron[f"pred_{paso}"] = real + rng.normal(0, ruido_modelo, len(fechas))
                pron[f"q10_{paso}"], pron[f"q90_{paso}"] = real - 10, real + 10
            partes.append(pd.DataFrame(pron))
    pd.concat(partes).to_parquet(carpeta / "bueno_c2048.parquet")
    pd.concat(partes).to_parquet(carpeta / "bueno_c2048_train.parquet")
    return reportes, carpeta


def test_cargar_pronosticos_ignora_los_de_entrenamiento(tmp_path):
    _, carpeta = _escenario(tmp_path, dias=2)
    assert list(cargar_pronosticos(carpeta)) == ["bueno_c2048"]


def test_comparar_mide_en_las_mismas_filas_y_distingue_al_mejor(tmp_path):
    reportes, carpeta = _escenario(tmp_path)
    comparacion, combinacion, mensual = comparar(reportes, cargar_pronosticos(carpeta), n=200)
    assert len(comparacion) == 2 * 2 * 3 * 2  # años × horizontes × áreas × (elegido + modelo)
    bueno = comparacion[comparacion["Modelo"] == "bueno_c2048"]
    elegido = comparacion[comparacion["Modelo"] == NOMBRE_ELEGIDO]
    assert (bueno["MAE (MW)"].to_numpy() < elegido["MAE (MW)"].to_numpy()).all()
    assert (bueno["IC 95 % alto"] < 0).all()  # la mejora se distingue de cero
    assert (bueno["Cobertura 10–90 (%)"] > 99).all()
    assert (bueno["Periodos"] == elegido["Periodos"].to_numpy()).all()
    assert set(mensual["Mes"]) == {"2025-01", "2026-01"}
    # el peso se fija en 2025 y se reutiliza en 2026
    pesos = combinacion.pivot_table(index=["Horizonte", "Área"], columns="Año", values="Peso del modelo")
    assert (pesos["2025"] == pesos["2026"]).all() and (pesos["2025"] > 0.5).all()
    assert (combinacion["MAE (MW)"] <= bueno["MAE (MW)"].to_numpy() + 0.2).all()


def test_alinear_falla_si_falta_un_origen():
    base = pd.DataFrame({"DateTime": pd.date_range("2025-01-01", periods=3, freq="30min"), "real": 1.0})
    pron = pd.DataFrame({"DateTime": base["DateTime"][:2], "area": "NORTE", "pred_2": 1.0, "q10_2": 0.0, "q90_2": 2.0})
    with pytest.raises(ValueError, match="faltan 1"):
        alinear(base, pron, "NORTE", 2)


def test_peso_combinacion_en_los_extremos():
    real = np.arange(10.0)
    assert peso_combinacion(real, real, real + 5) == 1.0
    assert peso_combinacion(real, real + 5, real) == 0.0
    assert peso_combinacion(real, real + 1, real - 1) == 0.5


def test_cobertura_sin_intervalo_es_nan():
    assert np.isnan(cobertura([1.0, 2.0], [np.nan, np.nan], [np.nan, np.nan]))
    assert cobertura([1.0, 5.0], [0.0, 0.0], [2.0, 2.0]) == 50.0


def test_separar_nombre():
    assert separar_nombre("simons_c2048") == ("simons", 2048)
    assert separar_nombre("chronos2ft_a_c8192") == ("chronos2ft_a", 8192)
    assert separar_nombre("otro") == ("otro", None)


def test_combinar_modelos_fija_el_peso_en_2025_y_conserva_el_formato(tmp_path):
    reportes, carpeta = _escenario(tmp_path, dias=10)
    bueno = cargar_pronosticos(carpeta)["bueno_c2048"]
    malo = bueno.assign(pred_2=bueno["pred_2"] + 50, pred_48=bueno["pred_48"] + 50)
    mezcla, pesos = combinar_modelos(reportes, bueno, malo)
    assert (pesos["Peso del primero"] == 1.0).all() and len(pesos) == len(HORIZONTES) * len(AREAS)
    assert list(mezcla.columns) == ["DateTime", "area", "pred_2", "q10_2", "q90_2", "pred_48", "q10_48", "q90_48"]
    assert len(mezcla) == len(bueno)
    np.testing.assert_allclose(mezcla["pred_48"], bueno["pred_48"])
    mitad, pesos = combinar_modelos(reportes, bueno.assign(pred_2=bueno["pred_2"] + 3), bueno.assign(pred_2=bueno["pred_2"] - 3))
    assert (pesos.loc[pesos["Horizonte"] == "1h", "Peso del primero"] == 0.5).all()
    np.testing.assert_allclose(mitad["pred_2"], bueno["pred_2"])
