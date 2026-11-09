# Veredicto H6 · momentum de 63 sesiones, top 15 hasta salir del top 45 (criterios de `docs/V24_H6_MOMENTUM_63.md`, sin modificarlos)

Fichero: `results/v24/v24_h6_42716246583.json` · commit `ddfbe28` · S&P 500 point-in-time con deslistadas (~500 miembros con precio por día en ambos periodos) ·
datos hasta 2020-12-31 (prueba final 2021-2026 **no cargada**) · ranking diario, 15 posiciones, sin protecciones, slippage 5 pb por lado + 0,005 $/acción, 100.000 $, fraccionarias.

| | CAGR | Caída máx. | Sharpe |
|---|---|---|---|
| **Periodo A 2010-2020** · H6 (entrenamiento 11,11 % · validación 2,36 %) | 7,92 % | −43,6 % | 0,47 |
| Placebos (10 semillas), mediana (entrenamiento 10,86 % · validación 8,73 %) | 10,42 % | | |
| SPY | 13,72 % | −33,7 % | 0,83 |
| **Periodo B 1997-2009** · H6 (1997-02 −0,64 % · 2003-09 7,44 %) | 3,93 % | −65,2 % | 0,28 |
| Placebos, mediana (1997-02 4,05 % · 2003-09 5,55 %) | 5,25 % | | |
| SPY | 4,91 % | −55,2 % | 0,33 |

| Criterio | Periodo A (IC 99,17 %) | Periodo B (IC 95 %) |
|---|---|---|
| CAGR de H6 > mediana de placebos en **ambos** tramos | **No** (gana en 2010-16, pierde en 2017-20) | **No** (pierde en 1997-02, gana en 2003-09) |
| IC de la diferencia mensual H6 − placebos, límite inferior > 0 | **No**: [−0,89 % ; +0,59 %], media −0,13 %/mes | **No**: [−0,82 % ; +0,76 %], media −0,05 %/mes |
| Supera al índice (Sharpe ≥ SPY…) | No | No |

## Veredicto registrado
**H6 no es candidata.** No hay ventaja demostrable del momentum de 63 sesiones (top 15 hasta salir del top 45) en el S&P 500, ni en 2010-2020 ni en 1997-2009.
No se prueban variantes y la prueba final 2021-2026 no se desbloquea.

## Lectura
- En ninguno de los dos periodos H6 rinde más que elegir 15 valores al azar con las mismas reglas; la diferencia media mensual es ligeramente negativa y su intervalo incluye 0.
- La versión pura tiene **caídas máximas mayores que SPY** (−43,6 % y −65,2 % frente a −33,7 % y −55,2 %) y está siempre invertida: sin protecciones, el riesgo no se compensa con rentabilidad.
- El resultado es inestable por tramos (gana en uno, pierde en otro), típico de una señal sin ventaja estable.
- Esta conclusión es coherente con las ejecuciones anteriores del motor corregido (variantes de V24 con protección) y con H1-H5 y la replicación de H2.

## Limitaciones
Solo S&P 500; 15 valores (varianza alta); 10 semillas de placebo; datos de un tercero sin licencia clara; costes hipotéticos; efectivo sin rendimiento; seis hipótesis probadas en total (Bonferroni aplicado en el periodo A).
Un resultado no significativo no demuestra que no exista ventaja, solo que con esta evidencia no se puede afirmar.
