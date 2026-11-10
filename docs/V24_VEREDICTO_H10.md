# Veredicto H10 · sistema tipo O'Neil, parte técnica de CAN SLIM (criterios de `docs/V24_H10_ONEIL.md`, sin modificarlos)

Fichero: `results/v24/v24_oneil_42917780198.json` · commit `fd088c3` · S&P 500 point-in-time con deslistadas (~500 miembros con precio por día) · prueba final 2021-2026 **no cargada** · coste 0,10 % por lado.
Señales: rango RS ≥ 80, tendencia (cierre > MA50 > MA200, MA200 subiendo, a ≤ 15 % del máximo anual), rotura de base (≥ 7 semanas y ≤ 33 % de profundidad, o ≥ 5 semanas y ≤ 15 %) con volumen ≥ 1,5×, solo con SPY > MA50.
Gestión: stop fijo 8 %, venta total en +25 %, regla de las 8 semanas (+20 % en < 15 sesiones → mantener hasta la sesión 40). Placebo: entradas aleatorias entre valores líquidos y miembros con el mismo stop y las mismas salidas (10 semillas).

## Por operación (esperanza en múltiplos de R, con R = 8 % de la entrada)
| | Operaciones | H10 (IC 95 %) | Placebo | Diferencia (IC) |
|---|---|---|---|---|
| **Periodo A 2010-2020** | **289** | 0,55 R (0,31 a 0,80); entren. 0,63 R (190), valid. 0,40 R (99; IC −0,01 a 0,80) | 0,67 R (entren. 0,85 R) | −0,12 R, IC 99,5 % [−0,44 ; +0,25] |
| **Periodo B 1997-2009** | **185** | 0,61 R (0,30 a 0,93); 1997-02 0,72 R (46), 2003-09 0,58 R (139) | 0,31 R (1997-02 −0,02 R) | +0,30 R, IC 95 % [−0,02 ; +0,62] |

## Cartera (1 % de riesgo por operación, 6 % total, 20 % de peso máximo)
| | CAGR | Caída máx. | Sharpe | Mediana CAGR placebo | SPY (CAGR / caída / Sharpe) |
|---|---|---|---|---|---|
| A 2010-2020 | 4,88 % (entren. 6,48 %, valid. 2,02 %) | −11,2 % | 0,67 | 7,87 % (7,13 % / 7,23 %) | 13,72 % / −33,7 % / 0,83 |
| B 1997-2009 | 4,81 % (1997-02 4,11 %, 2003-09 5,37 %) | −12,2 % | 0,69 | 3,88 % (6,53 % / 2,21 %) | 4,91 % / −55,2 % / 0,33 |

La cartera ejecutó solo 110 (A) y 96 (B) operaciones.

## Criterios
| Criterio | Periodo A | Periodo B |
|---|---|---|
| N ≥ 300 operaciones | **No** (289) | **No** (185) |
| Q1. Esperanza > 0 con IC inferior > 0 y positiva en cada tramo | No (validación: IC incluye 0) | Sí en estimación, pero N no se cumple |
| Q2. Diferencia vs placebo con IC inferior > 0 | **No** (negativa, no significativa) | **No** (positiva, IC incluye 0) |
| Q3. CAGR de cartera > mediana placebo en cada tramo | No | No |
| Riesgo/retorno vs SPY | No | Sí |

## Veredicto registrado
**H10 no es candidata, y la prueba es inconclusiva por tamaño de muestra** (menos de 300 operaciones en ambos periodos). No hay ventaja demostrable. No se prueban variantes (por ejemplo relajar umbrales para obtener más operaciones) y la prueba final 2021-2026 no se desbloquea.

## Lectura
- Los filtros de O'Neil (rango RS ≥ 80, base, volumen, mercado) dejan **muy pocas señales en el S&P 500**: 289 y 185 operaciones en 11 y 13 años, frente a miles en otras hipótesis.
- La diferencia con las entradas aleatorias es **negativa en 2010-2020** (el placebo con la misma gestión de ventas rinde 0,67 R, en un mercado que subió mucho) y **positiva pero no significativa en 1997-2009** (+0,30 R).
  La gestión de ventas (stop del 8 %, +25 %, 8 semanas) genera por sí sola una esperanza positiva alta en R, como ya se vio con H5.
- La cartera combina caídas máximas bajas (−11 % y −12 %) con poca inversión y un CAGR del 4-5 %; en 1997-2009 iguala a SPY con una quinta parte de la caída, pero no supera a las carteras aleatorias en 2010-2020.
- Las empresas del S&P 500 no son el universo natural del método; esta conclusión no refuta el sistema real de O'Neil.

## Limitaciones
Sin beneficios (C, A) ni patrocinio institucional (I); universo de grandes empresas; mi lectura mecánica de las bases; placebo sin filtros (mide el conjunto de filtros N, S, L, M); datos de un tercero sin licencia clara; diez hipótesis probadas en total.
