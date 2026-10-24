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
  <a href="docs/negocio.md">Negocio</a> ·
  <a href="https://colab.research.google.com/github/R0SEWT/tetouan-power-forecast/blob/develop/notebooks/01_datos_preparacion.ipynb">Abrir en Colab</a>
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

Tetuán (Marruecos) recibe la electricidad a través de Amendis, que la distribuye desde tres
subestaciones. Si la demanda de una subestación supera su capacidad, la red se sobrecarga. El centro
de control ve el consumo en tiempo real, pero solo cuando ya ocurrió.

Pronosticamos el consumo de **cada una de las tres zonas** con **una hora de anticipación** (6
periodos de 10 minutos), usando solo lo que se conoce al momento de predecir: el consumo y el clima
hasta ese instante, y el calendario. Una hora deja margen para transferir carga o preparar una
maniobra antes del pico.

| Zona | Comportamiento | Papel |
|---|---|---|
| Zona 1 | 45 % de la demanda, la más estable | Caso principal |
| Zona 3 | Costera y de veraneo, picos de verano | Prueba de estrés |
| Zona 2 | Ritmo laboral, cae domingos y feriados | Contraste |

**Criterio de éxito:** equivocarse menos que la mejor de tres referencias ingenuas (lo mismo que ahora,
lo mismo que ayer o lo mismo que la semana pasada a esa hora), también en las horas pico. El detalle
está en [`docs/negocio.md`](docs/negocio.md) y la evidencia, en [`docs/investigacion.md`](docs/investigacion.md).

<p align="right">(<a href="#inicio">volver arriba</a>)</p>

<a id="avance"></a>

## Avance

| Fase CRISP-DM | Dónde | Estado |
|---|---|---|
| 1. Comprensión del negocio | [`docs/negocio.md`](docs/negocio.md) y [`docs/investigacion.md`](docs/investigacion.md) | Hecha |
| 2. Comprensión de los datos | [`01_datos_preparacion`](notebooks/01_datos_preparacion.ipynb) y [`docs/datos.md`](docs/datos.md) | Hecha |
| 3. Preparación de los datos | [`01_datos_preparacion`](notebooks/01_datos_preparacion.ipynb) y el medallón | Hecha para la Zona 1; el gold de las tres zonas ya existe |
| 4. Modelado | `02_modelado_evaluacion` | Pendiente |
| 5. Evaluación | `02_modelado_evaluacion` | Pendiente |
| 6. Despliegue | app en Streamlit | Pendiente |

La preparación deja una partición cronológica 70/15/15, rezagos de las tres zonas, calendario con
codificación cíclica, validación cruzada temporal, información mutua, ablación por grupos de
variables y una revisión de *leakage*. Las referencias ingenuas que hay que superar en cada zona están
en [`docs/investigacion.md`](docs/investigacion.md#3-qué-tan-difícil-es-cada-zona-las-referencias-ingenuas).

<p align="right">(<a href="#inicio">volver arriba</a>)</p>

<a id="como-esta-hecho"></a>

## Cómo está hecho

```
UCI 849 ──► bronze ──► silver (auditado) ──► gold t+6, una tabla por zona      [Google Drive]
                           │                       │
                           ▼                       ▼
                  01 · datos y preparación    02 · modelado y evaluación
                  (firma de carga, clima,     (varios modelos, CV temporal,
                   días especiales)            contra las 3 referencias ingenuas)
                                                   │
                  src/tetouan_power_forecast       ▼
                  (medallón, perfiles,        app en Streamlit
                   variables, modelos,        (inputs, predicción, gráficos)
                   evaluación; con tests)
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
| `notebooks/` | `00_medallon` prepara los datos de Tetuán en Drive y `00b_ceuta`, los de Ceuta (validación externa); después, un notebook por tramo de CRISP-DM, numerados en orden. |
| `src/tetouan_power_forecast/` | Código que comparten los notebooks y la app: el pipeline de datos (`medallon`), la construcción del dataset t+6 (`datos`), la firma de carga y las referencias ingenuas (`perfiles`), las métricas (`metricas`), las variables del objetivo en razón (`variables`), los modelos en razón y en cambio y la validación cruzada del modelo global (`modelos`) y la evaluación contra las referencias (`evaluacion`). |
| `tests/` | Pruebas de `src/` con pytest. |
| `docs/negocio.md` | Comprensión del negocio: decisión, objetivos, papel de cada zona, criterios de éxito, riesgos y plan. |
| `docs/investigacion.md` | Qué zona es cuál, qué tan difícil es cada una y cómo pronostica la industria, con fuentes. |
| `docs/estado-del-arte.md` | Los trabajos que usan este dataset: horizonte, partición, fugas y referencias ingenuas, y cómo se posiciona el proyecto. |
| `docs/datos.md` | Procedencia, diccionario de variables y las capas del pipeline. |
| `docs/historico.md` | Cómo sortear que solo hay un año de histórico: opciones, evaluación honesta y amenazas a la validez. |
| `experimentos/historico/` | Los scripts que respaldan las cifras de `docs/historico.md`. |
| `experimentos/ceuta/` | Validación externa en Ceuta: cuánto histórico hace falta para pronosticar un verano. Se corre en Colab con `notebooks/00b_ceuta.ipynb`. |
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
