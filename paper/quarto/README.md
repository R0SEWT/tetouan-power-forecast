# El short paper en Quarto

| Archivo | Qué es |
|---|---|
| `short-paper.qmd` | El contenido completo de `../short-paper.md`, con secciones numeradas por Quarto, referencias cruzadas a tablas y figuras y citas a `referencias.bib`. Los **autores** se completan solo aquí, en el YAML del inicio |
| `_quarto.yml` | Lo común a todos los formatos y la vista previa en HTML |
| `_quarto-<perfil>.yml` | Un estilo por perfil, solo formato: `generico` (artículo A4, el de por defecto), `ieee` (IEEEtran de conferencia, dos columnas), `lncs` (Springer LNCS, una columna) y `elsevier` (elsarticle en modo preprint, una columna) |
| `estilos/` | Lo propio de cada estilo: los CSL oficiales de las referencias (`csl/`), el bloque de autores de IEEE y LNCS, los preámbulos y el filtro común que convierte las tablas en flotantes (a lo ancho de la página en IEEE) |
| `_extensions/` | La extensión `quarto-journals/elsevier` (la única de los tres estilos con una extensión de Quarto mantenida) |
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
quarto render short-paper.qmd --to pdf                                         # genérico
quarto render short-paper.qmd --profile ieee --to pdf --output ieee.pdf
quarto render short-paper.qmd --profile lncs --to pdf --output springer-lncs.pdf
quarto render short-paper.qmd --profile elsevier --to elsevier-pdf --output elsevier.pdf
```

Sin LaTeX en la máquina, el workflow `.github/workflows/paper.yml` compila los tres estilos en cada push que toque
esta carpeta y sube los PDF como artefacto (`gh run download <id> -n paper-pdf`).

Las salidas (`*.html`, `*.tex`, `*_files/`) no se versionan.

## Cambiar de estilo

Cada estilo es un perfil: para elegir uno basta con usar su `--profile`, o volverlo el de por defecto en
`profile: default:` de `_quarto.yml`. Para sumar otro estilo se agrega un `_quarto-<perfil>.yml` (con una extensión,
`quarto add <usuario/repo>` y su formato `<nombre>-pdf:`) y su nombre al grupo de perfiles.

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
