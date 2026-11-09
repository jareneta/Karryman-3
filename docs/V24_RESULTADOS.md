# Karryman V24 · resultados reproducibles (rama `karryman-v24`)

**Investigación. Nada de esto es una estrategia validada ni una rentabilidad esperada.** Universo: S&P 500 point-in-time con
deslistadas (`sp500data`, release `snapshot-2026-11`, SHA-256 en cada JSON), 2010-2026, precios ajustados por dividendos y splits.
Motor: `v24_engine.py` (29 pruebas de auditoría), cargador: `v24_backtest.py`. Tramos fijos sin optimizar: entrenamiento 2010-16,
validación 2017-20, prueba 2021-26. Efectivo sin rendimiento; slippage 5 pb por lado; comisión por acción 0,005 $ más el mínimo indicado
(**hipótesis**, no la tarifa real de IBKR).

Control de cordura del universo: 502,8 miembros con precio por día (499-509); cartera igualponderada de miembros 13,11 % anual, caída −40,02 %.
SPY (mismos datos): 14,70 % anual, caída −33,70 %.

Cómo reproducir: Actions → "Karryman V24 backtest" → modo `backtest`, `source=sp500data`, y los parámetros de cada tabla.

## A. 100.000 $, fraccionarias, sin comisión mínima ni importe mínimo
Fichero: `results/v24/v24_results_42667169398.json` · commit `9647c98` · run 42667169398.

| Modelo | CAGR | Caída máx. | Sharpe | Órdenes | Exposición media | CAGR entren./valid./prueba |
|---|---|---|---|---|---|---|
| V24 base (sin protección) | 5,93 % | −28,9 % | 0,46 | 64.774 | 73,6 % | 7,9 / 1,9 / 5,7 |
| Freno fijo −8 %/50 % | 5,43 % | −24,5 % | 0,49 | 65.536 | 59,1 % | 5,3 / 3,3 / 6,3 |
| Progresiva | 5,35 % | −22,0 % | 0,53 | 65.761 | 51,5 % | 5,7 / 2,5 / 6,4 |
| Progresiva + banda 10 % | 5,23 % | −21,5 % | 0,52 | 13.915 | 51,9 % | 5,4 / 2,7 / 6,1 |
| Progresiva + MA100 del patrimonio | 4,11 % | −21,5 % | 0,49 | 65.906 | 38,8 % | 4,3 / 1,3 / 5,8 |
| Progresiva, ranking mensual | 5,62 % | −24,9 % | 0,52 | 64.393 | 55,2 % | 6,2 / 5,0 / 4,8 |
| Control: V24 base, ranking mensual | 7,78 % | −33,5 % | 0,58 | 63.511 | 73,1 % | 9,5 / 7,9 / 5,4 |
| Control: ranking aleatorio mensual, semilla 1 | 10,70 % | −21,8 % | 0,81 | 63.620 | 87,4 % | 12,7 / 7,9 / 9,4 |
| Control: ranking aleatorio mensual, semilla 2 | 8,60 % | −22,6 % | 0,67 | 63.451 | 87,5 % | 8,1 / 8,5 / 8,9 |
| Control: ranking aleatorio mensual, semilla 3 | 6,15 % | −24,1 % | 0,50 | 63.639 | 87,4 % | 6,0 / 12,6 / 1,1 |

Sensibilidad a la comisión mínima (progresiva + banda 10 %): 0,35 $ → 5,10 % · 0,50 $ → 5,04 % · 1,00 $ → 4,62 %.

**Lectura:** la señal de momentum de 63 sesiones no se distingue de un ranking aleatorio en este universo (7,8 % frente a 6,2-10,7 %),
y ninguna variante se acerca a SPY ni a la cartera igualponderada. La banda del 10 % reduce las órdenes un 79 % sin coste apreciable
en CAGR (5,35 → 5,23 %). La protección progresiva reduce la caída máxima a costa de CAGR.

## B. 3.000 $, acciones enteras, orden mínima 100 $, comisión mínima 1 $
Fichero: `results/v24/v24_results_42668516998.json` · commit `bb7497c` · run 42668516998.

| Modelo | CAGR | Caída máx. | Órdenes | Comisiones totales |
|---|---|---|---|---|
| V24 base | −2,72 % | −60,7 % | 3.399 | 3.398 $ |
| Freno fijo | 0,35 % | −32,4 % | 2.604 | 2.601 $ |
| Progresiva (= con banda 10 %) | 0,25 % | −26,8 % | 2.299 | 2.297 $ |
| Progresiva + MA100 | −0,28 % | −25,6 % | 1.396 | 1.394 $ |
| Progresiva, ranking mensual | −0,07 % | −15,3 % | 1.338 | 1.334 $ |
| Control: V24 base, ranking mensual | 2,76 % | −22,2 % | 2.877 | 2.871 $ |
| Control: aleatorio mensual (3 semillas) | −2,7 / −3,3 / −3,6 % | −49 a −55 % | 3.0-4.0 mil | ~3.000-4.000 $ |

Sensibilidad (progresiva + banda 10 %, orden mínima 100 $): comisión mínima 0,35 $ → 2,68 % · 0,50 $ → 2,56 % · 1,00 $ → 0,25 %.
Anti-bloqueo: última orden 2026-10-28, mayor pausa 50 días, efectivo final 3.028 $ sobre patrimonio final 3.134 $.

**Lectura:** con 3.000 $ y 1 $ por orden, las comisiones totales igualan o superan el capital: con tan poco capital la operativa diaria
es inviable. Con 0,35 $ el resultado mejora de 0,25 % a 2,68 %. Estas cifras son muy ruidosas (pocas posiciones enteras); no se deben
interpretar diferencias entre modelos de unas décimas.

## C. Lo que NO se ha hecho (y por tanto no se puede afirmar)
- Intervalos de confianza, walk-forward y análisis de sensibilidad de parámetros: pendientes. Los controles aleatorios son solo 3 semillas.
- Auditoría de precios: los datos son de un tercero, sin licencia clara; 84 series con saltos diarios >40 % no revisadas.
- Las salidas por quiebra o fusión se liquidan al último cierre conocido (optimista en casos como SVB o Signature).
- El efectivo no rinde; con rendimiento del efectivo, las variantes con menor exposición mejorarían algo.
- Universo limitado al S&P 500. No se han usado datos de IBKR. No hay órdenes reales.
- Los resultados inválidos anteriores están en `results/v24/invalidos/` (ver su README).

## D. Conclusión de trabajo
Con estas reglas exactas y este universo no hay evidencia de que V24 aporte ventaja frente a selección aleatoria ni frente al índice.
Antes de seguir ajustando parámetros conviene: (1) revisar si la señal (momentum de 63 sesiones sin salto de 1 mes) es la adecuada,
(2) repetir con otras semillas de control y otros universos, (3) contrastar una muestra de precios con una fuente independiente.
