# Karryman V24 · estado de la investigación (en pausa desde 2026-11-09)

Rama de trabajo: `karryman-v24` (no fusionada en `main`). Investigación únicamente: sin conexión a IBKR ni órdenes reales.

## Conclusión
Con un motor auditado (`v24_engine.py`, 39+ pruebas), un universo S&P 500 point-in-time con deslistadas y controles aleatorios, **ninguna idea probada muestra ventaja demostrable**
sobre el índice ni sobre la selección aleatoria: V24 y sus variantes (`docs/V24_RESULTADOS.md`), H1-H4 (`V24_VEREDICTO_H1_H4.md`), replicación de H2 (`V24_VEREDICTO_REPLICA_H2.md`),
H5 sistema de `plan.html` (`V24_VEREDICTO_H5.md`) y H6 momentum 63 (`V24_VEREDICTO_H6.md`). Las cifras de 29-31 % de la investigación anterior no se reproducen.
La prueba final 2021-2026 **nunca se ha cargado ni mirado**.

## Pendiente (no iniciado; decisiones del usuario)
- **Universo fuera del S&P 500:** Tiingo (capa gratuita: 50 peticiones/hora, `V24_DATOS.md` §4-5). Requiere plan de pago, muestra reducida o descarga paulatina a almacenamiento privado.
  Antes de probar: registrar hipótesis y criterios (patrón de `V24_HIPOTESIS.md`), con la prueba final bloqueada.
- Aclarar la licencia de `Johnbrick123/sp500-data` (sin licencia; procedencia CRSP/Yahoo contradictoria) y contrastar una muestra de precios con otra fuente (p. ej. IBKR).
- Revisar las 84 series con saltos diarios >40 % (posibles splits sin ajustar).
- Intervalos de confianza adicionales y walk-forward si se retoma V24 u otra idea.

## Cómo retomar
Actions → "Karryman V24 backtest" (modos `tests`, `backtest`, `fuentes`, `hipotesis`, `replica_h2`, `h5`, `h6`, `tiingo`, `tiingo_limites`). Cada resultado se guarda en `results/v24/` con commit y huella SHA-256 de los datos.

## Secretos del repositorio
`TIINGO_API_KEY` está creado (solo lo usan los modos `tiingo` y `tiingo_limites`). Si no se va a usar, puede borrarse en Settings → Secrets and variables → Actions.
