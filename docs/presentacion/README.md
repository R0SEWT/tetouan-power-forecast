# Exposición final (TB1)

La presentación de los 20 minutos de la exposición final, hecha a partir del guion
([`../guion-exposicion.md`](../guion-exposicion.md)): las mismas diapositivas, el mismo reparto entre los
Expositores 1 a 5 y, en las notas del orador, lo que dice cada uno con su tiempo.

- [`slides/`](slides/README.md): el deck en Quarto, reveal.js y D3. `bash slides/render.sh --pdf` deja un HTML que
  funciona sin red y su PDF.
- **Publicado en <https://mds-rosewt.netlify.app/tb1/>**, con su PDF y una portada del curso en
  <https://mds-rosewt.netlify.app/>. Cuando el catálogo [uni.rosewt.dev](https://github.com/R0SEWT/uni) monte el
  sitio, la dirección será <https://uni.rosewt.dev/mds/tb1/>. `bash publicar.sh` renderiza el deck y lo vuelve a
  publicar en el sitio de Netlify `mds-rosewt`; `sitio/index.html` es la portada del curso.

Ninguna cifra está escrita a mano: salen de las tablas que escribieron los notebooks (`data/reportes/`) y, las pocas
que solo están en el informe técnico, de `paper/paper.md`, con su sección (ver `slides/datos.py`).

**Antes de exponer:** completar los nombres en [`slides/equipo.yml`](slides/equipo.yml) (cada diapositiva dice
quién habla, abajo a la izquierda) y que cada expositor revise sus diapositivas y sus notas.
