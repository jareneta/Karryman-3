# Veredicto H8 · sistema tipo Oliver Kell (criterios de `docs/V24_H8_KELL.md`, sin modificarlos)

Fichero: `results/v24/v24_kell_42721544955.json` · commit `78b2249` · S&P 500 point-in-time con deslistadas (~500 miembros con precio por día) · prueba final 2021-2026 **no cargada** · coste 0,10 % por lado.
Señales: Wedge Pop y EMA Crossback con filtro común (cierre > MA50 > MA200, MA200 subiendo, RS ≥ 70). Salidas: +3R vende 1/3 y breakeven; resto con cierre diario bajo la EMA20.
Placebo: entradas en fechas aleatorias entre valores líquidos y miembros, con el stop del mínimo de 10 sesiones y las mismas salidas, 10 semillas.

## Por operación (esperanza en múltiplos de R)
| | Operaciones | H8 (IC 95 %) | Placebo | Diferencia (IC) |
|---|---|---|---|---|
| **Periodo A 2010-2020** | 12.353 | 0,19 R (0,14 a 0,24); entren. 0,15 R, valid. 0,26 R | 0,33 R | **−0,14 R, IC 99,375 % [−0,21 ; −0,07]** |
| **Periodo B 1997-2009** | 8.339 | 0,07 R (0,02 a 0,13); 1997-02 **−0,12 R**, 2003-09 0,17 R | 0,17 R | **−0,10 R, IC 95 % [−0,16 ; −0,04]** |

## Cartera (1 % de riesgo por operación, 6 % total, 20 % de peso máximo)
| | CAGR | Caída máx. | Sharpe | Mediana CAGR placebo | SPY (CAGR / caída / Sharpe) |
|---|---|---|---|---|---|
| A 2010-2020 | 6,2 % (entren. 9,3 %, valid. 0,9 %) | −19,5 % | 0,56 | 8,72 % (11,05 % / 5,69 %) | 13,72 % / −33,7 % / 0,83 |
| B 1997-2009 | −1,2 % (1997-02 −4,5 %, 2003-09 1,5 %) | −51,9 % | 0,00 | 1,42 % (−0,07 % / 3,46 %) | 4,91 % / −55,2 % / 0,33 |

## Criterios
| Criterio | Periodo A | Periodo B |
|---|---|---|
| N ≥ 300 operaciones | Sí | Sí |
| Q1. Esperanza > 0 con IC inferior > 0 y positiva en cada tramo | Sí | **No** (1997-02 negativa) |
| **Q2. Diferencia vs placebo con IC inferior > 0** | **No** (la diferencia es **negativa** y significativa) | **No** (negativa y significativa) |
| Q3. CAGR de cartera > mediana placebo en cada tramo | No | No |
| Riesgo/retorno vs SPY | No | No |

## Veredicto registrado
**H8 no es candidata.** Las señales mecánicas Wedge Pop y EMA Crossback rinden **menos** que entrar en fechas aleatorias con las mismas salidas, de forma significativa en los dos periodos. No se prueban variantes y la prueba final 2021-2026 no se desbloquea.

## Lectura
- No es solo que no haya ventaja: en esta implementación la señal **resta** valor frente al azar (diferencia de −0,14 R y −0,10 R, con intervalos enteramente por debajo de cero).
- Posibles razones (no contrastadas): los stops muy ajustados de las señales (mínimo del día o de 3 sesiones) producen más salidas prematuras (36-37 % de aciertos frente a ~40 % del placebo) y una salida bajo la EMA20 corta pronto los recorridos largos.
  El placebo usa un stop más amplio (mínimo de 10 sesiones), de modo que la comparación mide también ese diseño, no solo la señal de entrada; esto ya se declaró en el registro.
- Esta conclusión es sobre mi aproximación mecánica y sobre empresas del S&P 500; no refuta el método discrecional de Kell ni su operativa sobre acciones de crecimiento más pequeñas.

## Resumen de las 8 hipótesis registradas
H1 momentum 12-1, H2 baja volatilidad (sin replicar), H3 momentum con filtro, H4 igualponderada con filtro, H5 sistema de `plan.html`, H6 momentum 63, H7 tipo Minervini (diferencia positiva en ambos periodos, sin cumplir Q2 corregido en 2010-2020) y H8 tipo Kell: **ninguna es candidata**.
