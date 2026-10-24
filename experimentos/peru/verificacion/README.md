# Verificación de los datos del Perú

Los scripts con los que se revisaron las fuentes y su calidad para el caso peruano. Respaldan las cifras de
[`docs/peru/energia.md`](../../../docs/peru/energia.md) y [`docs/peru/nino.md`](../../../docs/peru/nino.md).

Se guardan tal como corrieron, como evidencia, y por eso quedan fuera de ruff. Reciben por argumento la carpeta
con las muestras descargadas, que no se versiona. La ingesta del proyecto los reescribe en `src/` con pruebas, en
la fase 0 de la [spec](../../../docs/superpowers/specs/2026-10-23-demanda-sein-areas-design.md).

| Carpeta | Qué revisa |
|---|---|
| `energia/` | Demanda del SEIN y por barras, IEOD, costos marginales, eventos y SAIDI/SAIFI del COES y de Osinergmin; búsquedas en datosabiertos.gob.pe |
| `nino/` | ICEN, ONI, RONI y Niño 1+2: huecos, revisiones y coherencia; clima de ERA5 y NASA POWER; rezago de publicación; búsquedas en OpenAlex |
