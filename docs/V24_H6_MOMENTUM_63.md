# H6 · momentum de 3 meses, entra el top 15 y permanece hasta salir del top 45 · registro previo

Fecha de registro: 2026-11-09, **antes de ejecutar H6**. Las secciones 1-5 no se editan; cualquier cambio va como enmienda fechada al final.
Origen: petición del usuario ("momentum 3 meses hasta que sale del 45"). Es la versión mínima de V24, **sin** volatilidad objetivo, protección progresiva ni salida por extensión.

## 1. Reglas
- Universo: S&P 500 point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`).
- Puntuación: rentabilidad de las últimas 63 sesiones (`C[t]/C[t-63]-1`), sin omitir el último mes. Mayor es mejor. **Ranking diario.**
- Entran las acciones del **top 15**; una posición permanece **hasta salir del top 45**; máximo 15 posiciones; peso igual (1/15 cada una, con efectivo si hay menos de 15), reajuste diario a pesos objetivo.
- Sin volatilidad objetivo, sin protección, sin salida por extensión (EMA20 + 6 ATR), sin espera tras salida. Sin apalancamiento. Órdenes a la apertura siguiente.
- Costes: slippage 5 pb por lado + 0,005 $/acción; 100.000 $, fraccionarias.

## 2. Periodos (ambos independientes entre sí) y bloqueo
- **Periodo A: 2010-01-01 a 2020-12-31** (entrenamiento 2010-16 y validación 2017-20). **Periodo B: 1997-01-01 a 2009-12-31** (confirmación independiente; calentamiento desde 1996).
- La prueba final 2021-2026 **no se carga** y solo se abre si H6 pasa los criterios y el usuario lo confirma.

## 3. Controles
SPY comprado y mantenido; 10 semillas de ranking aleatorio (se redibuja cada 21 sesiones) con las mismas reglas de cartera (top 15 / permanencia hasta top 45, sin protecciones), en cada periodo.

## 4. Criterios (fijados antes)
Corrección de Bonferroni con **k = 6** hipótesis probadas en esta fase (H1-H5 y H6): nivel de confianza 1 − 0,05/6 = 99,17 % en el periodo A.
- **A1.** En el periodo A: CAGR de H6 > mediana de CAGR de sus placebos, en 2010-16 **y** en 2017-20 por separado.
- **A2.** En el periodo A: IC al 99,17 % (remuestreo por meses, 5.000) de la media de la diferencia de rentabilidades mensuales H6 − media de placebos, con límite inferior > 0.
- **B1.** En el periodo B: CAGR de H6 > mediana de placebos, en 1997-2002 **y** en 2003-2009.
- **B2.** En el periodo B: IC al 95 % de la misma diferencia con límite inferior > 0 (replicación de una sola hipótesis ya definida).
- **H6 es candidata** si cumple A1, A2, B1 y B2. **Supera al índice** si además, en ambos periodos, Sharpe ≥ SPY o (Calmar ≥ SPY y CAGR ≥ 80 % del de SPY).
- Si no es candidata: conclusión "no hay ventaja demostrable"; no se prueban variantes (ventanas de 126/252 sesiones, otros tops, filtros).

## 5. Qué NO se hará
Cambiar la ventana de 63 sesiones, los límites 15/45, añadir o quitar protecciones, elegir el periodo después de ver resultados, mirar 2021-2026.
