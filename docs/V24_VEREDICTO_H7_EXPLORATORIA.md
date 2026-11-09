# Resultado de la H7 exploratoria en acciones que cotizan hoy (`docs/V24_H7_EXPLORATORIA.md`)

**Exploratoria, con sesgo de supervivencia declarado; no cuenta para la candidatura de H7.**
Fichero: `results/v24/v24_h7_explor_42719500662.json` · commit `d891a9a` · datos de Yahoo hasta 2020-12-30 (2021-2026 no cargado).
De las ~3.100 acciones solicitadas (muestra aleatoria de acciones comunes que cotizan hoy, semilla 42) **1.013 series** tenían historial suficiente en 2007-2020 y se usaron. Reglas de H7 sin cambios; coste 0,10 % por lado.

## Resultados
| | Operaciones | Esperanza (IC 95 %) | Placebo (entradas aleatorias, mismo stop y salidas) |
|---|---|---|---|
| Entrenamiento 2010-16 | 158 | 0,48 R (0,12 a 0,87) | 0,42 R |
| Validación 2017-20 | 111 | 0,72 R (0,32 a 1,13) | 0,35 R |
| **2010-2020** | **269** | **0,58 R (0,31 a 0,85)** | **0,39 R** |

Diferencia H7 − placebo: **+0,19 R, IC 95 % [−0,08 ; +0,47]** (incluye 0). Media positiva en ambos tramos.

| Cartera (1 %/6 %/20 %) 2010-2020 | CAGR | Caída máx. | Sharpe |
|---|---|---|---|
| H7 | 7,45 % (entren. 6,37 %, valid. 9,15 %) | −12,2 % | 1,01 |
| SPY | 13,66 % | −33,7 % | 0,83 |
| Carteras placebo, mediana de CAGR | 6,76 % (entren. 8,66 %, valid. 8,09 %) | | |

97 operaciones de cartera en 11 años (poco invertida).

## Lectura (según las reglas fijadas antes)
- **Diagnóstico de sesgo:** la esperanza de las entradas aleatorias aquí (0,389 R) es casi igual a la del S&P 500 point-in-time (0,383 R); en esta métrica **no se observa una inflación apreciable por supervivencia**
  (con la salvedad de que la muestra son 1.013 supervivientes con historial completo del periodo).
- **Señal favorable: NO.** El IC de la diferencia incluye 0 → según la regla registrada es **señal desfavorable: se archiva la línea** de probar H7 en este universo.
- Con 269 operaciones no se alcanza el mínimo de 300 que se exigía en la prueba formal de H7; es otro motivo para no sacar conclusiones.
- La diferencia media (+0,19 R) es del mismo orden que en el S&P 500 (+0,22 R en 2010-2020 y +0,29 R en 1997-2009), pero **no significativa** en ninguno de los tres casos con estos tamaños muestrales; se registra como dato, no como hallazgo.
  Combinar los resultados para "rescatar" H7 no está permitido por las reglas registradas.
- La cartera con las reglas de riesgo de la app queda por debajo de SPY y por debajo de las carteras aleatorias en entrenamiento.

## Limitaciones
Solo supervivientes con historial en 2007-2020 (1.013 series); sin empresas deslistadas; precios de Yahoo ajustados; sin fundamentales; costes hipotéticos; datos de un solo periodo.
