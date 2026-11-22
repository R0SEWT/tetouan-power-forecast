# El short paper en Quarto (estilo IEEE)

| Archivo | Qué es |
|---|---|
| `short-paper.qmd` | El paper: el texto, las tablas, las citas y el resumen ejecutivo (en el YAML, como `abstract`). Los **autores** se completan solo aquí, en el YAML del inicio |
| `_quarto.yml` | El formato: IEEE de conferencia (IEEEtran, dos columnas, Times) para el PDF y una vista previa en HTML |
| `estilos/` | Lo propio de IEEE: el bloque de autores (`title.tex` y `autores.lua`: un bloque por autor en filas de tres y la afiliación común debajo), el preámbulo (`preambulo.tex`), el filtro que convierte las tablas en flotantes a lo ancho de la página (`tablas.lua`) y el CSL oficial de las referencias (`ieee.csl`) |
| `referencias.bib` | La bibliografía. Cada DOI se resolvió en doi.org y cada URL se abrió el 22-nov-2026; las excepciones van comentadas en el archivo |
| `figuras/` | Las cinco figuras, a una columna (8.9 cm), con letra de 8 pt y la paleta Okabe-Ito, en PDF (las del paper) y PNG (las de la vista previa). Las dibuja `figuras/generar.py` a partir de las tablas que ya escribieron los notebooks, sin recalcular ningún modelo |

No hay una extensión de Quarto mantenida para IEEE (las que existen no se actualizan desde 2023-2025 y no resuelven
las tablas a dos columnas, porque pandoc las escribe como `longtable`), así que el estilo va con la clase IEEEtran y
las tres piezas de `estilos/`.

## Compilar

Sin LaTeX en la máquina, el workflow `.github/workflows/paper.yml` compila el PDF en cada push que toque esta
carpeta y lo sube como artefacto (`gh run download <id> -n short-paper-ieee`).

En local, la vista previa no necesita LaTeX (Quarto trae pandoc); el PDF necesita TinyTeX, que se instala una vez:

```bash
cd paper/quarto
quarto render short-paper.qmd --to html   # short-paper.html, un solo archivo con las figuras dentro
quarto install tinytex                    # una sola vez
quarto render short-paper.qmd --to pdf    # short-paper.pdf
```

Las figuras se rehacen, si cambian los datos, con la carpeta de datos del proyecto:

```bash
TETOUAN_DATA=/ruta/a/los/datos uv run python paper/quarto/figuras/generar.py
```

Las salidas (`*.html`, `*.tex`, `*.pdf` de la raíz de esta carpeta, `*_files/`) no se versionan.

## Diferencias con `../short-paper.md`

El PDF tiene 6-8 páginas de IEEE con las referencias: el texto se acortó y lo que salió quedó en el informe técnico
(`../paper.md`) y en el repositorio, que el paper cita. El detalle de qué se recortó y dónde quedó está en la
descripción del PR. Además:

- El título del paper cumple la sección «título» del enunciado y el resumen ejecutivo es el resumen del paper.
- Frases nuevas: el enlace a la app publicada (<https://curva.rosewt.dev>), SHAP con su figura, la temperatura
  pronosticada y el rango adaptativo que corren en paralelo (PR #53 y #55) y el Entregable 8.
- Cifras al día: la cuarentena de 2020 y su rebote, −32 y +51 %, salen de la misma serie de la figura 1 (el short
  paper redondeaba a −30 y +40 %).
- Correcciones: la referencia de Wei (2023) tenía otro título (el DOI correcto es el de `docs/estado-del-arte.md`).
