# Replicación independiente de H2 (baja volatilidad) en 1997-2009 · registro previo

Fecha de registro: 2026-11-09, **antes de cargar o ejecutar nada de este periodo**. Motivo: H2 mostró un patrón llamativo en 2010-2020 pero no fue
estadísticamente significativa (`docs/V24_VEREDICTO_H1_H4.md`). 1997-2009 es un periodo anterior e independiente del que originó la hipótesis.

## 1. Hipótesis (sin cambios respecto a H2)
Misma definición, mismo universo (S&P 500 point-in-time con deslistadas, `snapshot-2026-11`), misma cartera (15 valores, entran top 15 por menor
volatilidad de 63 sesiones, permanecen hasta salir del top 45, ranking cada 21 sesiones, peso igual, sin protección/volatilidad objetivo/extensión),
mismos costes (5 pb de slippage por lado + 0,005 $/acción), 100.000 $, fraccionarias. **No se cambia ningún parámetro.**

## 2. Datos y bloqueo
- Se cargan precios de 1996-01-01 a **2009-12-31** (calentamiento en 1996; evaluación desde 1997-01-01). No se carga nada posterior.
- La prueba final 2021-2026 sigue bloqueada. 2010-2020 ya se vio y no se reutiliza como confirmación.
- Control de cordura del universo: media de miembros con precio por día ≥ 400 (el cargador rechaza lo contrario).

## 3. Controles
SPY comprado y mantenido; 10 semillas de ranking aleatorio mensual (mismas reglas de cartera, sin filtro de mercado).

## 4. Criterios (fijados antes)
Subperiodos: **P1 = 1997-2002**, **P2 = 2003-2009**, **Todo = 1997-2009**.
- **R1.** CAGR de H2 > mediana de CAGR de los placebos, en P1 y en P2 por separado.
- **R2.** IC del 95 % (remuestreo por meses, 5.000 muestras) de la media de la diferencia de rentabilidades mensuales H2 − media de placebos en 1997-2009 con límite inferior > 0
  (una sola hipótesis, k = 1).
- **R3 (superar al índice).** En 1997-2009: Sharpe de H2 ≥ Sharpe de SPY, **o** (Calmar ≥ Calmar de SPY y CAGR ≥ 80 % del de SPY).
- **Replica** si R1 y R2. **Replica y supera al índice** si además R3.
- Si no replica: H2 se descarta como idea con ventaja demostrable y no se prueban variantes.
- Si replica: H2 pasa a candidata combinada (1997-2020). El desbloqueo de la prueba final 2021-2026 requiere confirmación explícita del usuario y se hará una sola vez.

## 5. Qué NO se hará
Cambiar ventana de volatilidad, número de posiciones o umbrales; elegir el subperiodo después de ver resultados; añadir hipótesis; mirar 2021-2026.
