# El paper del TB1

| Archivo | Qué es |
|---|---|
| `short-paper.md` / `short-paper.docx` | **La versión de entrega**: ocho secciones del enunciado, unas 4,300 palabras, 6 tablas y 4 figuras. Las fuentes de cada cifra van en comentarios HTML, que no salen en el `.docx`. |
| `paper.md` / `paper.docx` | El informe técnico completo (unas 13,400 palabras), con la fuente de cada cifra en notas al pie. El guion de la exposición y la guía de defensa (`docs/`) citan sus secciones. |
| `quarto/` | El short paper en Quarto: el mismo contenido con el formato aislado en `_quarto.yml`, la bibliografía en BibTeX verificada y las figuras. Ver `quarto/README.md`. |
| `figuras/` | Las cuatro figuras del short paper, exportadas tal cual de los notebooks ejecutados (sin recalcular): `fig1` de `01_sein_datos_preparacion` (celda 16), `fig2` de `02_sein_modelado_evaluacion` (celda 31, segunda figura), `fig3` de `03_sein_prueba_2026` (celda 16) y `fig4` de `04_sein_modelos_fundacionales` (celda 19, rama `feature/modelos-fundacionales`). |

Los `.docx` se regeneran con pandoc (vía `pypandoc-binary`, sin instalar nada en el sistema):

```bash
uv run --no-project --with pypandoc-binary python -c "import pypandoc; pypandoc.convert_file('paper/short-paper.md','docx',outputfile='paper/short-paper.docx',extra_args=['--columns=400','--resource-path=paper'])"
```

Pendientes del Aula: extensión, plantilla, normas de cita, nombre del archivo y fecha de entrega; apellidos de los
integrantes.
