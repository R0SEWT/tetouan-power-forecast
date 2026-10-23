<a id="inicio"></a>

<div align="center">

<h1>tetouan-power-forecast</h1>

<p>
  <strong>Pronóstico del consumo eléctrico de Tetuán con una hora de anticipación</strong>,<br>
  de la pregunta de negocio a una app que predice, siguiendo CRISP-DM.
</p>

<p>
  Trabajo grupal (TB1) del curso <em>Metodología para Data Science</em> (UPC 1ACC0240, ciclo 2026-2)
</p>

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="scikit-learn" src="https://img.shields.io/badge/scikit--learn-1.5+-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white">
  <img alt="CI" src="https://img.shields.io/github/actions/workflow/status/R0SEWT/tetouan-power-forecast/ci.yml?branch=develop&style=for-the-badge&label=ruff%20%2B%20pytest">
</p>

<p>
  <a href="#avance">Avance</a> ·
  <a href="#empezar">Empezar</a> ·
  <a href="#convenciones">Convenciones</a> ·
  <a href="https://colab.research.google.com/github/R0SEWT/tetouan-power-forecast/blob/main/notebooks/01_negocio_datos_preparacion.ipynb">Abrir en Colab</a>
</p>

</div>

<details>
  <summary>Contenido</summary>
  <ol>
    <li><a href="#que-es">Qué es</a></li>
    <li><a href="#avance">Avance</a></li>
    <li><a href="#como-esta-hecho">Cómo está hecho</a></li>
    <li><a href="#empezar">Empezar</a></li>
    <li><a href="#mapa">Mapa del repo</a></li>
    <li><a href="#convenciones">Convenciones</a></li>
    <li><a href="#datos">Datos</a></li>
    <li><a href="#equipo">Equipo</a></li>
  </ol>
</details>

<a id="que-es"></a>

## Qué es

La red eléctrica de Tetuán (Marruecos) se reparte en tres zonas de distribución. El operador
tiene que equilibrar en todo momento la energía que entrega con la que consume la ciudad: si la
demanda supera lo previsto, la red se sobrecarga; si se sobreestima, se compra o genera energía
que nadie usa.

Estimamos el consumo de la **Zona 1** con **una hora de anticipación** (6 periodos de 10
minutos), usando solo lo que se conoce en el momento de predecir: el consumo y el clima hasta
ese instante, y el calendario. Una hora alcanza para ajustar la generación antes de un pico; diez
minutos, no.

**Criterio de éxito:** el modelo tiene que equivocarse menos que el *baseline* de persistencia,
que supone que dentro de una hora se consumirá lo mismo que ahora. Si no lo supera, no aporta
valor.

<p align="right">(<a href="#inicio">volver arriba</a>)</p>

<a id="avance"></a>

## Avance

| Fase CRISP-DM | Dónde | Estado |
|---|---|---|
| 1. Comprensión del negocio | [`01_negocio_datos_preparacion`](notebooks/01_negocio_datos_preparacion.ipynb) | Hecha |
| 2. Comprensión de los datos | [`01_negocio_datos_preparacion`](notebooks/01_negocio_datos_preparacion.ipynb) | Hecha |
| 3. Preparación de los datos | [`01_negocio_datos_preparacion`](notebooks/01_negocio_datos_preparacion.ipynb) | Hecha |
| 4. Modelado | `02_modelado_evaluacion` | Pendiente |
| 5. Evaluación | `02_modelado_evaluacion` | Pendiente |
| 6. Despliegue | app en Streamlit | Pendiente |

La preparación deja una partición cronológica 70/15/15, rezagos de las tres zonas, calendario con
codificación cíclica, validación cruzada temporal, información mutua, ablación por grupos de
variables y una revisión de *leakage*.

| Referencia a superar | MAE | RMSE | MAPE |
|---|---:|---:|---:|
| Persistencia, validación | 2,073 kW | 2,904 kW | 6.24 % |
| Persistencia, prueba | 1,821 kW | 2,504 kW | 6.29 % |

<p align="right">(<a href="#inicio">volver arriba</a>)</p>

<a id="como-esta-hecho"></a>

## Cómo está hecho

```
UCI 849 (ucimlrepo) ──► 01 · negocio, datos, preparación ──► dataset t+6 (rezagos + calendario)
                                                                     │
                                                                     ▼
                         src/tetouan_power_forecast ◄──── 02 · modelado y evaluación
                         (métricas compartidas,             (varios modelos, CV temporal,
                          con tests)                         comparación con persistencia)
                                   │                                 │
                                   ▼                                 ▼
                         app en Streamlit ◄─────────────── modelo final
                         (inputs, predicción, gráficos)
```

<p align="right">(<a href="#inicio">volver arriba</a>)</p>

<a id="empezar"></a>

## Empezar

**En Colab.** Los datos viven en Google Drive y se procesan en Colab. Corre primero
[`00_medallon`](https://colab.research.google.com/github/R0SEWT/tetouan-power-forecast/blob/develop/notebooks/00_medallon.ipynb):
monta tu Drive y deja ahí las capas bronze, silver y gold. Los demás notebooks leen el gold desde el
Drive. Si un notebook usa el código de `src/`, la primera celda lo instala:

```python
!pip install -q git+https://github.com/R0SEWT/tetouan-power-forecast@develop
```

Para guardar cambios desde Colab, primero crea tu rama en GitHub (selector de ramas › escribe el
nombre › *Create branch*) y luego usa *Archivo › Guardar una copia en GitHub* eligiendo esa rama.

**En local**, con [uv](https://docs.astral.sh/uv/):

```bash
uv sync --extra dev
uv run tetouan all      # datos: bronze → silver (auditado) → gold, en data/
uv run pytest -q
uv run ruff check .
uv run jupyter lab
```

La primera corrida tarda unos minutos porque UCI sirve el CSV lento; después, cada capa se reutiliza.
Detalle de las capas y de la procedencia en [`docs/datos.md`](docs/datos.md).

<p align="right">(<a href="#inicio">volver arriba</a>)</p>

<a id="mapa"></a>

## Mapa del repo

| Ruta | Qué hay |
|------|---------|
| `notebooks/` | `00_medallon` prepara los datos en Drive; después, un notebook por tramo de CRISP-DM, numerados en orden. |
| `src/tetouan_power_forecast/` | Código que comparten los notebooks y la app: el pipeline de datos (`medallon`), la construcción del dataset t+6 (`datos`) y las métricas (`metricas`). |
| `tests/` | Pruebas de `src/` con pytest. |
| `docs/datos.md` | Procedencia, diccionario de variables, las tres zonas y las capas del pipeline. |
| `.github/` | CI (ruff + pytest en cada push a `main` o `develop` y en cada PR), plantilla de PR y Dependabot. |
| `data/` | Copia local de las capas (las compartidas están en Google Drive). No se versiona. |

<p align="right">(<a href="#inicio">volver arriba</a>)</p>

<a id="convenciones"></a>

## Convenciones

- **Git Flow**: nada entra directo a `develop` ni a `main`. Una rama por unidad de trabajo
  (`feature/modelado`, `feature/app`, …), PR hacia `develop` y una fusión a `main` por entregable,
  con tag (`tb1-avance`, `tb1-final`).
- **Un notebook, una persona a la vez**: git no sabe combinar dos versiones de un `.ipynb` editadas
  en paralelo. Si dos personas avanzan a la vez, cada una trabaja en su propio notebook.
- **Lo repetido va a `src/`**: si dos notebooks (o un notebook y la app) usan la misma función,
  vive en `src/` y tiene su test.
- **Ninguna cifra a mano**: las tablas y figuras del paper salen de los notebooks, no se copian a mano.
- **Los datos no se versionan**: el pipeline los baja de UCI y guarda su procedencia (sha256 incluido).

<p align="right">(<a href="#inicio">volver arriba</a>)</p>

<a id="datos"></a>

## Datos

[*Power Consumption of Tetouan City*](https://archive.ics.uci.edu/dataset/849/power+consumption+of+tetouan+city),
del UCI Machine Learning Repository (ID 849): registros cada 10 minutos de todo 2017, con el clima
de la ciudad y el consumo de sus tres zonas. Licencia
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

> Salam, A., & El Hibaoui, A. (2018). *Power Consumption of Tetouan City* [Dataset]. UCI Machine
> Learning Repository. https://doi.org/10.24432/C5B034

<p align="right">(<a href="#inicio">volver arriba</a>)</p>

<a id="equipo"></a>

## Equipo

<div align="center">
<table>
  <tr>
    <td align="center" width="170">
      <a href="https://github.com/R0SEWT">
        <img src="https://avatars.githubusercontent.com/u/102562850?v=4" width="88" alt="Rody Vilchez"><br>
        <b>Rody Vilchez</b><br><sub>@R0SEWT</sub>
      </a>
    </td>
  </tr>
</table>
</div>

<p align="center"><sub>Grupo 3 · Metodología para Data Science · UPC · Ciclo 2026-2</sub></p>

<p align="right">(<a href="#inicio">volver arriba</a>)</p>
