# Pronóstico del consumo eléctrico de Tetuán a una hora

Trabajo grupal (TB1) del curso **Metodología para Data Science** (1ACC0240) de la UPC,
ciclo 2026-2, Grupo 3.

Estimamos el consumo eléctrico de la **Zona 1** de Tetuán (Marruecos) con **una hora de
anticipación** (6 periodos de 10 minutos), siguiendo CRISP-DM. Con ese margen, el operador de
la red puede ajustar la generación o redistribuir carga antes de que llegue un pico. El modelo
solo aporta valor si se equivoca menos que el *baseline* de persistencia, que supone que
dentro de una hora se consumirá lo mismo que ahora.

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/R0SEWT/tetouan-power-forecast/blob/main/notebooks/01_negocio_datos_preparacion.ipynb)

## Avance

| Fase CRISP-DM | Dónde | Estado |
|---|---|---|
| 1. Comprensión del negocio | `notebooks/01_negocio_datos_preparacion.ipynb` | Hecha |
| 2. Comprensión de los datos | `notebooks/01_negocio_datos_preparacion.ipynb` | Hecha |
| 3. Preparación de los datos | `notebooks/01_negocio_datos_preparacion.ipynb` | Hecha: partición cronológica 70/15/15, baseline, validación cruzada temporal, información mutua, ablación y revisión de *leakage* |
| 4. Modelado | — | Pendiente |
| 5. Evaluación | — | Pendiente |
| 6. Despliegue (app en Streamlit) | — | Pendiente |

El baseline que hay que superar tiene un MAE de **2,073 kW en validación** y de **1,821 kW en
prueba**.

## Datos

[*Power Consumption of Tetouan City*](https://archive.ics.uci.edu/dataset/849/power+consumption+of+tetouan+city),
del UCI Machine Learning Repository (ID 849). Tiene registros cada 10 minutos de todo 2017,
con el clima de la ciudad y el consumo de sus tres zonas de distribución. Se publica con
licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

El notebook descarga los datos con `ucimlrepo`, así que no se guardan en el repo.

> Salam, A., & El Hibaoui, A. (2018). *Power Consumption of Tetouan City* [Dataset]. UCI
> Machine Learning Repository. https://doi.org/10.24432/C5B034

## Cómo trabajar

**En Colab.** Abre el notebook con el botón de arriba. Para guardar tus cambios usa
*Archivo › Guardar una copia en GitHub*, elige este repositorio y deja la misma ruta. Para
eso necesitas acceso de colaborador; pídelo en el grupo.

**Un notebook, una persona a la vez.** Git no sabe combinar dos versiones de un `.ipynb`
editadas en paralelo. Avisa en el grupo antes de editar uno, o trabaja tu parte en un
notebook nuevo (por ejemplo, `02_modelado_evaluacion.ipynb`).

**En local:**

```bash
pip install -r requirements.txt
jupyter lab
```

## Estructura

```text
notebooks/
  01_negocio_datos_preparacion.ipynb   fases 1 a 3 de CRISP-DM
requirements.txt                       librerías que usan los notebooks
```

Después vendrán el notebook de modelado y evaluación, la app en Streamlit y el short paper.
