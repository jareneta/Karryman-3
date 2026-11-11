# Veredicto H11 · SPY como base + comprar caídas como complemento (criterios de `docs/V24_H11_SPY_MAS_CAIDAS.md`, sin modificarlos)

Fichero: `results/v24/v24_overlay_42999850701.json` · commit `11addf1` · S&P 500 point-in-time con deslistadas · prueba final 2021-2026 **no cargada**.
Cartera: lo no asignado a operaciones está en SPY; complemento = reglas de H9b (1 % de riesgo por operación, 6 % total, 20 % de peso máximo; coste 0,10 % por lado).

| | CAGR | Caída máx. | Sharpe |
|---|---|---|---|
| **A 2010-2020** · H11 (entren. 9,36 %, valid. 19,97 %) | 13,17 % | −31,4 % | 0,71 |
| SPY (entren. 12,49 %, valid. 15,71 %) | 13,72 % | −33,7 % | 0,83 |
| Placebo (entradas aleatorias + SPY), mediana (entren. 5,38 %, valid. 6,67 %) | 5,92 % | | |
| **B 1997-2009** · H11 (1997-02 7,26 %, 2003-09 5,37 %) | 6,52 % | −62,5 % | 0,38 |
| SPY (4,32 % / 4,94 %) | 4,91 % | −55,2 % | 0,33 |
| Placebo + SPY, mediana (−1,54 % / 2,46 %) | 0,18 % | | |

| Criterio | Periodo A | Periodo B |
|---|---|---|
| E1. CAGR > SPY **y** IC de la diferencia mensual con límite inferior > 0 | **No**: −0,55 pp; diferencia mensual media +0,03 %, IC 99,55 % [−0,51 % ; +0,54 %] | **No**: +1,61 pp, pero diferencia mensual media +0,16 %, IC 95 % [−0,24 % ; +0,56 %] incluye 0 |
| E2. Mejor que las carteras placebo (con SPY) en cada tramo | **Sí** | **Sí** |
| E3. Sharpe ≥ SPY y caída máxima no peor | **No** (Sharpe 0,71 < 0,83) | **No** (caída −62,5 % peor que −55,2 %) |

## Veredicto registrado
**H11 no supera al S&P 500.** No cumple E1 ni E3 en ninguno de los dos periodos; sí cumple E2 (la señal de caída aporta frente a entradas aleatorias). No se prueban variantes y la prueba final 2021-2026 no se desbloquea.

## Sensibilidades (no deciden)
| Exceso de CAGR sobre SPY | 2010-2020 | 1997-2009 |
|---|---|---|
| Base (coste 0,10 % por lado) | −0,55 pp | +1,61 pp |
| Coste 0,20 % por lado | −2,38 pp | −1,07 pp |
| Coste 0,30 % por lado | −4,29 pp | −3,54 pp |
| Riesgo 2 % por operación | −2,56 pp | −0,55 pp |
| Riesgo 3 % por operación | −2,93 pp | −2,49 pp |

Con costes de 0,20 % por lado o más, el complemento resta rentabilidad frente a SPY en ambos periodos; más riesgo por operación tampoco ayuda.

## Lectura
- La ventaja por operación de H9b es real frente al azar (E2), pero **muy pequeña**: lo que se gana en cada caída se compensa con el coste de operar y con el rendimiento de SPY al que se renuncia mientras se está en la operación. El neto frente a comprar y mantener SPY **no es distinguible de cero**.
- Los costes dominan el resultado: con 0,20 % por lado el complemento ya pierde contra SPY en los dos periodos.
- En 1997-2009 el exceso positivo (+1,6 pp) no es estadísticamente significativo y la caída máxima fue peor que la de SPY.

## Limitaciones
SPY (un ETF) como base; sin costes de mover efectivo hacia/desde SPY ni impuestos; empresas grandes; datos de un tercero sin licencia clara; once hipótesis probadas en total.
