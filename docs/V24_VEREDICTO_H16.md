# Veredicto H16 · regla de exposición al mercado

Ejecución: runs 44794264650 (régimen 2015) y 44794268980 (legacy), commit 58b89ef; resultados en `results/v24/v24_exposure_*.json`. Registro previo: `docs/V24_H16_EXPOSICION_MERCADO.md`. No replica el método de Albert Albareda (se desconoce).

## Resultado: **no cumple ningún criterio** (R1, R2 y R3 fallan en todos los periodos)

| Periodo | Regla CAGR / caída máx. / Sharpe | SPY | Mezcla constante (misma exposición media) | p placebo |
|---|---|---|---|---|
| 2015-2026 | 6,1 % / −21,4 % / 0,62 | 13,5 % / −33,7 % / 0,81 | 10,6 % / −27,0 % / 0,81 | 0,63 |
| 2010-2020 | 5,8 % / −20,0 % / 0,59 | 13,7 % / −33,7 % / 0,83 | 11,1 % / −27,7 % / 0,83 | 0,81 |
| 1997-2009 | 2,9 % / −40,3 % / 0,31 | 4,9 % / −55,2 % / 0,33 | 3,7 % / −38,3 % / 0,33 | 0,24 |

- Exposición media 63-80 %. Recortó la caída máxima en la mayoría de ventanas, pero perdió 7-8 puntos de CAGR anual frente a SPY en 2010-2026.
- **El momento de entrar y salir no aporta**: en todos los periodos queda por debajo de simplemente tener la misma exposición media fija (Sharpe 0,62 vs 0,81), y los placebos desplazados rinden igual o mejor (p = 0,24-0,81). La reducción de riesgo se explica por estar menos invertido, no por acertar el momento.
- Exceso mensual medio frente a SPY negativo (−0,6 %), IC no excluye 0 en 1997-2009 y roza el 0 en las demás.
- Muchas entradas/salidas (señales de 50 sesiones y amplitud 50) generan whipsaw; el coste de 0,20 % empeora más el resultado.

## Sensibilidades (no deciden; descriptivas)
La tendencia lenta sola (SPY > SMA200) dio 8,3 %/−24,9 % en 2015-2026 y 7,0 %/−24,7 % en 1997-2009 (SPY 4,9 %/−55 %); la volatilidad sola dio 11,3 %/−22,0 % en 2015-2026. Son elecciones posteriores al resultado entre 9 variantes: no se pueden tomar como hallazgo, solo como hipótesis candidata (coherente con H12, donde el filtro SMA200 reducía caídas sin subir rentabilidad). Habría que registrarla como H17 antes de afirmar nada.

## Conclusión
No hay evidencia de que esta regla genérica de exposición supere al S&P 500 ni de que el momento de salir aporte valor más allá de reducir exposición. Limitaciones: umbrales arbitrarios, efectivo al 0 % (con 2 %: 6,6 % en 2015-2026, sin cambiar la conclusión), pocas caídas independientes, no es el método de Albareda.
