# El paper del TB1

| Archivo | Qué es |
|---|---|
| `paper.md` / `paper.docx` | El informe técnico completo (unas 13,400 palabras), con la fuente de cada cifra en notas al pie. El guion de la exposición y la guía de defensa (`docs/`) citan sus secciones. |
| `quarto/` | **El short paper de entrega**, en estilo IEEE (Quarto, IEEEtran a dos columnas, 8 páginas), con las figuras rehechas para imprimir y la bibliografía verificada. El PDF lo compila GitHub Actions. Ver `quarto/README.md`. |
| `figuras/` | Las figuras del informe técnico (`fig5` a `fig9`, citadas en `paper.md`) y las cuatro de la primera versión del short paper (`fig1` a `fig4`, exportadas tal cual de los notebooks 01 a 04; esa versión en Markdown se retiró y sigue en el historial de git). Las figuras del short paper de entrega están en `quarto/figuras/`. |

El `.docx` del informe técnico se regenera con pandoc (vía `pypandoc-binary`, sin instalar nada en el sistema):

```bash
uv run --no-project --with pypandoc-binary python -c "import pypandoc; pypandoc.convert_file('paper/paper.md','docx',outputfile='paper/paper.docx',extra_args=['--columns=400','--resource-path=paper'])"
```

