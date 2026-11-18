# Resultado H15 · réplica parcial del screener: 15 acciones, vender cuando dejan de aparecer (criterios de `docs/V24_H15_SCREENER.md`, sin modificarlos)

Fichero: `results/v24/v24_screener_44206558852.json` · commit `7dc97a2` · S&P 500 point-in-time con deslistadas (~504 miembros con precio por día) · periodo **2015-01-01 a 2026-10-31** (S1 2015-2020, S2 2021-2026) · coste 0,10 % por lado · 10 semillas.
Filtros reproducidos: rentabilidades de 1, 3, 6 y 12 meses (> +1 %, +10 %, 0 %, +1 %), cierre sobre las medias de 20, 50 y 200 sesiones, a menos del 15 % del máximo anual, precio > 5 $, volumen medio > 500.000 y sin dividendos en 252 sesiones.
**No reproducidos:** crecimiento de ventas, BPA, sectores (no comprobables con datos de cada fecha); universo S&P 500 en vez de las empresas pequeñas que devuelve el screener real.

## Resultado
| | CAGR 2015-2026 | S1 2015-2020 | S2 2021-2026 | Caída máx. media | Sharpe medio |
|---|---|---|---|---|---|
| **Screener parcial** (15 posiciones, salir al dejar de aparecer; media de 10 semillas) | **−0,25 %** (rango −0,99 a +0,76) | +0,09 % | −0,31 % | −35,0 % | 0,05 |
| Solo tendencia (cierre > SMA200), misma mecánica | 7,98 % | 8,47 % | 7,76 % | −29,1 % | 0,53 |
| Azar mensual (15 valores líquidos recompuestos cada 21 sesiones) | 9,47 % | 8,23 % | 11,09 % | −41,0 % | 0,56 |
| Igualponderada de todos los miembros | 11,39 % | 10,73 % | 12,39 % | −40,0 % | 0,68 |
| **SPY** | **13,50 %** | 12,69 % | 14,63 % | −33,7 % | 0,81 |

- Cumplen el screener parcial, de media, **12,2 valores por día** (frente a 283 con solo tendencia), de modo que la cartera tiene de media **9,6 posiciones** y casi no llega a 15.
- Mecánica media por semilla: **4.275 compras y 4.259 ventas en 11,8 años** (unas 360 compras al año), frente a 537 compras de "solo tendencia": con filtros tan estrictos (precio sobre las tres medias, +1 % en el último mes, etc.) un pequeño retroceso expulsa al valor del screener, se vende y se vuelve a entrar en otro: **rotación muy alta**.
  Con posiciones de 1/15 y 0,10 % por lado, ese ir y venir cuesta del orden de un 4-5 % anual solo en comisiones.

## Criterios
| Criterio | Resultado |
|---|---|
| R1. Supera a SPY (CAGR, IC de la diferencia mensual > 0 al 99,67 %, Sharpe) | **No**: −0,25 % frente a 13,50 %; diferencia mensual media −1,09 %, IC [−2,10 % ; −0,02 %] (significativamente peor) |
| R2. Mejor que "solo tendencia" y que el azar en cada tramo | **No** |
| **H15 supera al S&P 500** | **No** |

## Veredicto registrado
La réplica parcial del screener, con la mecánica "15 acciones y vender cuando dejan de aparecer", **no aporta nada sobre una simple tendencia ni sobre el azar y es significativamente peor que SPY** en el S&P 500 en 2015-2026.

## Lectura y límites
- El problema principal parece la **salida "cuando deja de aparecer"** con filtros tan sensibles: genera una rotación enorme y recompra continua cerca de máximos, no la señal de entrada. Una prueba con costes cero (no registrada) permitiría separar ambos efectos.
- No prueba el screener completo: faltan los filtros de crecimiento de ventas, BPA y sectores, y las empresas pequeñas fuera del S&P 500. **Un resultado negativo aquí no demuestra que el screener real no funcione**, solo que esta parte técnica, tal como se ha replicado, no sirve en este universo.
- La vía para probar el screener completo es **seguirlo hacia delante** (guardar la lista cada día y calcular la estrategia sobre los datos que vayan llegando).
