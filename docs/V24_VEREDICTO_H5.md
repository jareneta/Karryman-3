# Veredicto H5 · sistema de `plan.html` (criterios de `docs/V24_H5_PLAN_HTML.md`, sin modificarlos)

Fichero: `results/v24/v24_h5_42710217527.json` · commit `7978a90` · S&P 500 point-in-time con deslistadas (media de 502 miembros con precio por día, 824 series) ·
datos hasta 2020-12-31 (prueba final 2021-2026 **no cargada**) · coste 0,10 % por lado.

## Por operación (esperanza en múltiplos de R)
| | Operaciones | Esperanza (IC 95 %) | % aciertos |
|---|---|---|---|
| H5 · entrenamiento 2010-16 | 4.372 | 1,53 R (1,40 a 1,66) | 40,1 % |
| H5 · validación 2017-20 | 2.063 | 0,28 R (0,18 a 0,39) | 33,4 % |
| **H5 · 2010-20** | **6.435** | **1,13 R (1,03 a 1,23)** | 38,0 % |
| Placebo (entrada en fecha aleatoria, mismos stops y salidas) · 2010-20 | 91.340 | 1,03 R (0,97 a 1,08) | 34,7 % |
| Placebo · entrenamiento / validación | | 1,43 R / 0,32 R | |

Diferencia H5 − placebo (2010-20): **+0,10 R, IC 95 % [−0,01 ; +0,22]** → incluye 0.

## Cartera (1 % de riesgo por operación, 6 % de riesgo total, 20 % de peso máximo)
| 2010-2020 | CAGR | Caída máx. | Sharpe | Calmar |
|---|---|---|---|---|
| H5 | 7,94 % | −12,3 % | 0,96 | 0,65 |
| SPY | 13,72 % | −33,7 % | 0,83 | 0,41 |
| Carteras placebo (10 semillas): mediana de CAGR | 7,89 % (rango 5,35-11,32) | | | |

CAGR por tramo: H5 7,44 % (entrenamiento) y 8,74 % (validación) frente a medianas placebo de 7,46 % y 9,45 %. La cartera solo ejecutó **49 operaciones** en 11 años
(con 1 % de riesgo por operación, tope del 6 % y runners que se mantienen mucho tiempo, la cartera está poco invertida).

## Criterios
| Criterio | Resultado |
|---|---|
| ≥ 300 operaciones | Sí (6.435) |
| Q1. Esperanza en R > 0 con IC inferior > 0; positiva en entrenamiento y en validación | **Sí** |
| Q2. IC 95 % de (H5 − placebo) con límite inferior > 0 | **No** (−0,008) |
| Q3. Sharpe ≥ SPY, o Calmar ≥ SPY con CAGR ≥ 80 % | Sí (por Sharpe 0,96 ≥ 0,83) |
| Q4. CAGR de cartera > mediana placebo en entrenamiento **y** validación | **No** |
| **Candidata** (Q1 y Q2) | **No** |
| Supera al índice | **No** |

## Veredicto registrado
**H5 no es candidata: no hay ventaja demostrable de la señal de entrada** en este universo y periodo. No se prueban variantes y la prueba final 2021-2026 no se desbloquea.

## Lectura
- La esperanza por operación es positiva, pero **también lo es con entradas en fechas aleatorias** (1,03 R) con las mismas salidas. Lo que genera esa esperanza es la gestión de salidas
  (stop pequeño, parcial en +4R, runner hasta la media de 50 semanas) en un mercado que subió mucho entre 2010 y 2020, no la señal de rotura con volumen: la ventaja de la señal es de +0,10 R y no es estadísticamente distinguible de 0.
- En validación (2017-2020) la esperanza cae a 0,28 R y queda por debajo del placebo (0,32 R).
- La cartera tiene buena relación riesgo/retorno aparente (Sharpe 0,96, caída −12 %), pero porque está poco invertida, y su CAGR (7,9 %) queda muy por debajo del de SPY (13,7 %) y es igual al de la cartera aleatoria.

## Limitaciones
Solo empresas del S&P 500 (no small/mid caps de crecimiento); filtro de fundamentales no evaluado (no comprobable con datos de la fecha); 2010-2020 fue un mercado alcista largo; el placebo no aplica el filtro técnico de tendencia
(solo liquidez y membresía), por lo que la comparación mide la señal completa (filtro + rotura + volumen) frente a entrar al azar; cierres de posiciones al último precio disponible en deslistadas; datos de un tercero sin licencia clara.
Un resultado no significativo no demuestra que no exista ventaja, solo que con esta evidencia no se puede afirmar.
