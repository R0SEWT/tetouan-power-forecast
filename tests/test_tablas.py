import pandas as pd
import pytest

from tetouan_power_forecast import tablas


@pytest.fixture
def crudas():
    """Copia en texto de todas las tablas, para romperlas a propósito sin tocar los CSV."""
    return {nombre: tablas._leer_crudo(nombre) for nombre in tablas.TABLAS}


def test_las_tablas_del_paquete_son_validas():
    tablas.validar()


@pytest.mark.parametrize("nombre", tablas.TABLAS)
def test_cargar_devuelve_las_columnas_esperadas(nombre):
    df = tablas.cargar(nombre)
    assert list(df.columns) == tablas.COLUMNAS[nombre]
    assert len(df) > 0


def test_cargar_acepta_la_extension_y_rechaza_nombres_desconocidos():
    assert len(tablas.cargar("ciudades_era5.csv")) == len(tablas.cargar("ciudades_era5"))
    with pytest.raises(KeyError):
        tablas.cargar("no_existe")


def test_cargar_convierte_fechas_y_numeros():
    fer = tablas.cargar("feriados_pe_2015_2026")
    assert pd.api.types.is_datetime64_any_dtype(fer["fecha"])
    assert fer["fecha"].dt.year.between(2015, 2026).all()
    ciu = tablas.cargar("ciudades_era5")
    assert ciu["peso_en_area"].dtype == "float64"
    assert ciu["poblacion_censo_2017"].dtype == "int64"


def test_los_25_departamentos_tienen_area():
    dep = tablas.cargar("departamentos_area")
    assert len(dep) == 25 and dep["departamento"].is_unique
    assert set(dep["area"]) == {"norte", "centro", "sur"}
    area = dict(zip(dep["departamento"], dep["area"]))
    assert area["Lima"] == area["Callao"] == "centro"
    assert area["Piura"] == area["La Libertad"] == "norte"
    assert area["Arequipa"] == area["Cusco"] == "sur"


def test_asignaciones_que_pide_el_proyecto():
    emp = tablas.cargar("empresa_area")
    area = dict(zip(emp["empresa_original"].map(tablas.normalizar), emp["area"]))
    coes = dict(zip(emp["empresa_original"].map(tablas.normalizar), emp["empresa_coes"]))
    # Edelnor, Enel Distribución y Pluz son la misma empresa, en Lima Norte (Centro)
    assert coes["EDELNOR"] == coes["ENEL DISTRIBUCION PERU"] == coes["PLUZ ENERGIA PERU SAA"]
    assert area["EDELNOR"] == area["LUZ DEL SUR"] == "centro"
    for nombre in ("HIDRANDINA", "ELECTRONORTE SA", "ELECTRONOROESTE SA"):
        assert area[nombre] == "norte"
    for nombre in ("ELECTRO SUR ESTE", "ELECTRO PUNO", "SEAL", "ELECTROSUR SA"):
        assert area[nombre] == "sur"
    assert area["RED DE ENERGIA DEL PERU SA"] == "sein"


def test_sein_solo_para_transmisoras():
    emp = tablas.cargar("empresa_area")
    assert set(emp.loc[emp["area"] == "sein", "tipo"]) == {"transmisora"}


def test_ciudades_de_la_spec():
    ciu = tablas.cargar("ciudades_era5")
    assert set(ciu.loc[ciu["area"] == "norte", "ciudad"]) == {"Piura", "Chiclayo", "Trujillo"}
    assert set(ciu.loc[ciu["area"] == "centro", "ciudad"]) == {"Lima"}
    assert "Cusco" not in set(ciu["ciudad"])
    lima = ciu.set_index("ciudad").loc["Lima"]
    assert (lima["lat"], lima["lon"]) == (-12.046, -77.043)


def test_normalizar_unifica_mayusculas_tildes_y_puntos():
    assert tablas.normalizar("Pluz Energía Perú S.A.A..") == "PLUZ ENERGIA PERU SAA"
    assert tablas.normalizar("  enel   distribución ") == "ENEL DISTRIBUCION"


# --- cada regla detecta su falla ---


def _hay(err, texto):
    return any(texto in e for e in err)


def test_regla_departamento_repetido_o_faltante(crudas):
    dep = crudas["departamentos_area"]
    crudas["departamentos_area"] = pd.concat([dep, dep.iloc[[0]]], ignore_index=True)
    assert _hay(tablas.errores(crudas), "repetidos")
    crudas["departamentos_area"] = dep.iloc[1:]
    assert _hay(tablas.errores(crudas), "se esperan los 25")


def test_regla_area_no_permitida(crudas):
    crudas["departamentos_area"].loc[0, "area"] = "oriente"
    assert _hay(tablas.errores(crudas), "area no permitida")


def test_regla_sein_en_empresa_que_no_es_transmisora(crudas):
    emp = crudas["empresa_area"]
    emp.loc[emp["tipo"] == "distribuidora", "area"] = "sein"
    assert _hay(tablas.errores(crudas), "empresa_area: area no permitida")


def test_regla_filas_duplicadas(crudas):
    sub = crudas["subestacion_departamento_area"]
    crudas["subestacion_departamento_area"] = pd.concat([sub, sub.iloc[[3]]], ignore_index=True)
    assert _hay(tablas.errores(crudas), "filas duplicadas")


def test_regla_fecha_invalida_y_repetida(crudas):
    fer = crudas["feriados_pe_2015_2026"]
    crudas["feriados_pe_2015_2026"] = pd.concat([fer, fer.iloc[[0]].assign(nombre="otro")])
    assert _hay(tablas.errores(crudas), "(fecha, tipo, ambito) repetidos")
    fer.loc[0, "fecha"] = "2023-02-30"
    crudas["feriados_pe_2015_2026"] = fer
    assert _hay(tablas.errores(crudas), "fechas inválidas")


def test_regla_pesos_por_area(crudas):
    crudas["ciudades_era5"].loc[0, "peso_en_area"] = "0.9"
    assert _hay(tablas.errores(crudas), "no suman 1")


def test_regla_fuente_vacia(crudas):
    crudas["cuarentena_pe_2020"].loc[0, "fuente"] = " "
    assert _hay(tablas.errores(crudas), "sin fuente")


def test_regla_fases_de_cuarentena_en_orden(crudas):
    q = crudas["cuarentena_pe_2020"]
    q.loc[1, "desde"] = q.loc[0, "desde"]
    assert _hay(tablas.errores(crudas), "se solapan")


def test_tabla_sin_una_columna_da_el_error_de_esquema_y_no_un_keyerror(crudas, monkeypatch):
    crudas["departamentos_area"] = crudas["departamentos_area"].drop(columns="departamento")
    crudas["sin_asignar"] = crudas["sin_asignar"].drop(columns="empresa_original")  # la regla cruzada
    monkeypatch.setattr(tablas, "_leer_crudo", crudas.__getitem__)
    with pytest.raises(ValueError) as error:
        tablas.validar()
    mensaje = str(error.value)
    assert "departamentos_area: columnas ['area', 'fuente', 'confianza'] != ['departamento'," in mensaje
    assert "sin_asignar: columnas ['fuente', 'motivo'] != ['empresa_original'," in mensaje
    assert "se esperan los 25" not in mensaje  # sus reglas propias no corren sobre la tabla rota
