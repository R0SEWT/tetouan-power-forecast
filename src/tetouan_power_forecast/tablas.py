"""Tablas de referencia del SEIN: áreas del COES, empresas, subestaciones, ciudades, feriados.

Los CSV viven en el subdirectorio ``tablas/`` del paquete y se leen con ``importlib.resources``,
así que funcionan igual desde el repo que desde el wheel instalado. El detalle de cada tabla (de
dónde salió, qué queda ambiguo y su cobertura) está en ``docs/peru/tablas.md``.

Uso::

    from tetouan_power_forecast import tablas
    deptos = tablas.cargar("departamentos_area")
    tablas.validar()  # lanza ValueError si alguna regla falla
"""

from __future__ import annotations

import re
import unicodedata
from importlib import resources

import pandas as pd

AREAS = frozenset({"norte", "centro", "sur"})
CONFIANZAS = frozenset({"alta", "media", "baja"})
TIPOS_EMPRESA = frozenset({"distribuidora", "generadora", "transmisora", "usuario_libre"})
TIPOS_DIA = frozenset({"feriado", "no_laborable"})
AMBITOS = frozenset({"nacional", "sector_publico", "regional"})
DEPARTAMENTOS = frozenset({
    "Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca", "Callao", "Cusco",
    "Huancavelica", "Huánuco", "Ica", "Junín", "La Libertad", "Lambayeque", "Lima", "Loreto",
    "Madre de Dios", "Moquegua", "Pasco", "Piura", "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali",
})

COLUMNAS = {
    "departamentos_area": ["departamento", "area", "fuente", "confianza"],
    "subarea_area": ["subarea", "area", "departamentos", "fuente", "confianza"],
    "empresa_area": [
        "empresa_coes", "empresa_original", "tipo", "area", "departamento_principal", "fuente",
        "confianza",
    ],
    "sin_asignar": ["empresa_original", "fuente", "motivo"],
    "subestacion_departamento_area": [
        "subestacion", "departamento", "area", "kv", "fuente", "confianza",
    ],
    "ciudades_era5": [
        "ciudad", "area", "lat", "lon", "altitud_m", "poblacion_censo_2017", "peso_en_area", "fuente",
    ],
    "feriados_pe_2015_2026": ["fecha", "nombre", "tipo", "ambito", "fuente"],
    "cuarentena_pe_2020": ["desde", "hasta", "fase", "descripcion", "fuente"],
}
TABLAS = tuple(COLUMNAS)

_NUMERICAS = {
    "subestacion_departamento_area": {"kv": "float"},
    "ciudades_era5": {
        "lat": "float", "lon": "float", "altitud_m": "int", "poblacion_censo_2017": "int",
        "peso_en_area": "float",
    },
}
_FECHAS = {"feriados_pe_2015_2026": ["fecha"], "cuarentena_pe_2020": ["desde", "hasta"]}


def normalizar(nombre: str) -> str:
    """Clave de comparación de nombres: mayúsculas, sin tildes ni puntos, espacios simples.

    >>> normalizar("Compañía Minera  Chungar S.A.C.")
    'COMPANIA MINERA CHUNGAR SAC'
    """
    s = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode()
    s = s.upper().replace(".", "")
    return re.sub(r"\s+", " ", s).strip()


def _leer_crudo(nombre: str) -> pd.DataFrame:
    archivo = resources.files("tetouan_power_forecast").joinpath("tablas", f"{nombre}.csv")
    with archivo.open("r", encoding="utf-8") as f:
        return pd.read_csv(f, dtype=str, keep_default_na=False)


def cargar(nombre: str) -> pd.DataFrame:
    """Carga una tabla del paquete por su nombre (con o sin ``.csv``).

    Los textos vienen como ``str`` (vacío si no hay dato); las fechas como ``datetime64`` y las
    columnas numéricas (``kv``, coordenadas, población y pesos) como números.
    """
    nombre = nombre.removesuffix(".csv")
    if nombre not in COLUMNAS:
        raise KeyError(f"tabla desconocida: {nombre!r}; disponibles: {', '.join(TABLAS)}")
    df = _leer_crudo(nombre)
    for col, tipo in _NUMERICAS.get(nombre, {}).items():
        valores = pd.to_numeric(df[col].replace("", None), errors="raise")
        df[col] = valores.astype("int64") if tipo == "int" else valores.astype("float64")
    for col in _FECHAS.get(nombre, []):
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="raise")
    return df


def errores(t: dict[str, pd.DataFrame]) -> list[str]:
    """Aplica las reglas a un diccionario ``{nombre: DataFrame crudo}`` y devuelve los problemas.

    Las tablas llegan como texto (sin convertir tipos), tal como están en el CSV.
    """
    err: list[str] = []
    for nombre, df in t.items():
        if list(df.columns) != COLUMNAS[nombre]:
            err.append(f"{nombre}: columnas {list(df.columns)} != {COLUMNAS[nombre]}")
            continue
        if df.empty:
            err.append(f"{nombre}: vacía")
        if df.duplicated().any():
            err.append(f"{nombre}: {int(df.duplicated().sum())} filas duplicadas")
        if "fuente" in df and (df["fuente"].str.strip() == "").any():
            err.append(f"{nombre}: {int((df['fuente'].str.strip() == '').sum())} filas sin fuente")
        if "confianza" in df and not df["confianza"].isin(CONFIANZAS).all():
            malas = sorted(set(df["confianza"]) - CONFIANZAS)
            err.append(f"{nombre}: confianza fuera de {sorted(CONFIANZAS)}: {malas}")
        if "area" in df:
            permitidas = df["area"].isin(AREAS)
            if nombre == "empresa_area":
                permitidas |= (df["area"] == "sein") & (df["tipo"] == "transmisora")
            if not permitidas.all():
                malas = df.loc[~permitidas, "area"].unique().tolist()
                err.append(f"{nombre}: area no permitida: {malas}")
        for col in ("departamento", "departamento_principal"):
            if col in df:
                vals = set(df[col]) - {""} if col == "departamento_principal" else set(df[col])
                if vals - DEPARTAMENTOS:
                    err.append(f"{nombre}: {col} desconocido: {sorted(vals - DEPARTAMENTOS)}")
    err += _reglas_especificas(t)
    return err


def _fechas_invalidas(serie: pd.Series) -> int:
    return int(pd.to_datetime(serie, format="%Y-%m-%d", errors="coerce").isna().sum())


def _reglas_especificas(t: dict[str, pd.DataFrame]) -> list[str]:
    err: list[str] = []
    if "departamentos_area" in t:
        d = t["departamentos_area"]["departamento"]
        if d.duplicated().any():
            err.append(f"departamentos_area: repetidos {sorted(set(d[d.duplicated()]))}")
        if d.nunique() != 25 or set(d) != DEPARTAMENTOS:
            err.append(f"departamentos_area: {d.nunique()} departamentos, se esperan los 25")
    if "empresa_area" in t:
        e = t["empresa_area"]
        if not e["tipo"].isin(TIPOS_EMPRESA).all():
            err.append(f"empresa_area: tipo fuera de {sorted(TIPOS_EMPRESA)}")
        claves = e["empresa_original"].map(normalizar)
        if claves.duplicated().any():
            err.append(f"empresa_area: empresa_original repetida: {sorted(set(claves[claves.duplicated()]))}")
        if "sin_asignar" in t:
            ambas = set(claves) & set(t["sin_asignar"]["empresa_original"].map(normalizar))
            if ambas:
                err.append(f"sin_asignar: también están en empresa_area: {sorted(ambas)}")
    if "subestacion_departamento_area" in t:
        s = t["subestacion_departamento_area"]
        if s["subestacion"].duplicated().any():
            err.append("subestacion_departamento_area: subestaciones repetidas")
        kv = pd.to_numeric(s["kv"].replace("", None), errors="coerce")
        if (kv.isna() & (s["kv"] != "")).any():
            err.append("subestacion_departamento_area: kv no numérico")
    if "ciudades_era5" in t:
        c = t["ciudades_era5"]
        pesos = pd.to_numeric(c["peso_en_area"], errors="coerce")
        suma = pesos.groupby(c["area"]).sum()
        malas = suma[(suma - 1).abs() > 0.01]
        if pesos.isna().any() or len(malas):
            err.append(f"ciudades_era5: los pesos no suman 1 por área: {malas.round(4).to_dict()}")
        if set(c["area"]) != AREAS:
            err.append("ciudades_era5: falta alguna área")
    if "feriados_pe_2015_2026" in t:
        f = t["feriados_pe_2015_2026"]
        if n := _fechas_invalidas(f["fecha"]):
            err.append(f"feriados_pe_2015_2026: {n} fechas inválidas")
        if not f["tipo"].isin(TIPOS_DIA).all() or not f["ambito"].isin(AMBITOS).all():
            err.append("feriados_pe_2015_2026: tipo o ambito fuera de los valores permitidos")
        clave = f[["fecha", "tipo", "ambito"]]
        if clave.duplicated().any():
            dup = clave[clave.duplicated()].astype(str).agg("/".join, axis=1).tolist()
            err.append(f"feriados_pe_2015_2026: (fecha, tipo, ambito) repetidos: {dup}")
    if "cuarentena_pe_2020" in t:
        q = t["cuarentena_pe_2020"]
        if _fechas_invalidas(q["desde"]) or _fechas_invalidas(q["hasta"]):
            err.append("cuarentena_pe_2020: fechas inválidas")
        else:
            desde = pd.to_datetime(q["desde"])
            hasta = pd.to_datetime(q["hasta"])
            if (desde > hasta).any():
                err.append("cuarentena_pe_2020: desde > hasta")
            if (desde.iloc[1:].to_numpy() <= hasta.iloc[:-1].to_numpy()).any():
                err.append("cuarentena_pe_2020: las fases se solapan o no están en orden")
    return err


def validar() -> None:
    """Carga todas las tablas del paquete y lanza ``ValueError`` si alguna regla falla."""
    err = errores({nombre: _leer_crudo(nombre) for nombre in TABLAS})
    if err:
        raise ValueError("tablas de referencia inválidas:\n- " + "\n- ".join(err))
