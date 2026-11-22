# El short paper en Quarto

| Archivo | Qué es |
|---|---|
| `short-paper.qmd` | El contenido completo de `../short-paper.md`, con secciones numeradas por Quarto, referencias cruzadas a tablas y figuras y citas a `referencias.bib`. Los **autores** se completan solo aquí, en el YAML del inicio |
| `_quarto.yml` | El formato, y solo el formato: para cambiar de estilo se edita el bloque `format:` (y `csl:`, si el estilo lo pide) |
| `referencias.bib` | La bibliografía en BibTeX. Cada DOI se resolvió en doi.org y cada URL se abrió el 22-nov-2026; las excepciones van comentadas en el archivo |
| `figuras/` | Copia de `../figuras/fig1` a `fig5`, exportadas tal cual de los notebooks (ver `../README.md`) |

## Compilar

Vista previa sin LaTeX (Quarto trae pandoc; no descarga nada):

```bash
cd paper/quarto
quarto render short-paper.qmd --to html   # short-paper.html, un solo archivo con las figuras dentro
```

El PDF necesita una distribución de LaTeX. Con TinyTeX, una sola vez y luego cada vez que se quiera el PDF:

```bash
quarto install tinytex
quarto render short-paper.qmd --to pdf
```

Las salidas (`*.html`, `*.tex`, `*_files/`) no se versionan.

## Cambiar de estilo

- **Extensión de Quarto** (por ejemplo, la plantilla de una revista o un congreso): `quarto add <usuario/repo>` dentro de
  esta carpeta y, en `_quarto.yml`, reemplazar `pdf:` por el formato que trae la extensión (`<nombre>-pdf:`).
- **Clase de LaTeX propia**: cambiar `documentclass:` y sus opciones en el bloque `pdf:`.
- **Referencias**: copiar el `.csl` del estilo a esta carpeta y descomentar `csl:`.

Lo que depende del estilo y queda por decidir al elegirlo: si «Título del proyecto» y «Resumen ejecutivo» siguen como
secciones (así los pide el enunciado) o pasan al bloque del título y al resumen de la plantilla; el ancho de las
tablas grandes (1, 3, 4 y 7) y de las figuras; el estilo de las referencias; y la extensión.

## Diferencias con `../short-paper.md`

- Frases nuevas: el enlace a la app publicada (<https://curva.rosewt.dev>), SHAP en los resultados de 2025, la
  temperatura pronosticada (PR #55) en el seguimiento en vivo y en el trabajo futuro, y el Entregable 8.
- Citas en el texto para todas las referencias de la bibliografía.
- Correcciones: la limitación 3 estaba cortada (se completó con la frase de `../paper.md`); el diagnóstico del sesgo
  decía «cuatro cosas» y listaba cinco (la quinta es de la revisión del 19-nov); la referencia de Wei (2023) tenía
  otro título (el DOI correcto es el de `docs/estado-del-arte.md`).
