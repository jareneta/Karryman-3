# Veredicto H7 · sistema tipo Minervini (criterios de `docs/V24_H7_MINERVINI.md`, sin modificarlos)

Fichero: `results/v24/v24_h7_42717934863.json` · commit `e088064` · S&P 500 point-in-time con deslistadas (~500 miembros con precio por día) · prueba final 2021-2026 **no cargada** ·
coste 0,10 % por lado · placebo: entradas en fechas aleatorias con el mismo stop (8 %/10 sesiones) y las mismas salidas, 10 semillas.

## Por operación (esperanza en múltiplos de R)
| | Operaciones | H7 | Placebo | Diferencia (IC) |
|---|---|---|---|---|
| **Periodo A 2010-2020** | 519 | **0,60 R** (IC 95 %: 0,42 a 0,79); entrenamiento 0,67 R, validación 0,47 R | 0,38 R | **+0,22 R, IC 99,29 % [−0,03 ; +0,48]** |
| **Periodo B 1997-2009** | 398 | **0,48 R** (IC 95 %: 0,26 a 0,70); 1997-02 0,27 R, 2003-09 0,58 R | 0,18 R | **+0,29 R, IC 95 % [+0,07 ; +0,52]** |

## Cartera (1 % de riesgo por operación, 6 % total, 20 % de peso máximo)
| | CAGR | Caída máx. | Sharpe | Mediana CAGR placebo | SPY (CAGR / caída / Sharpe) |
|---|---|---|---|---|---|
| A 2010-2020 | 4,98 % (entren. 4,78 %, valid. 5,24 %) | −11,5 % | 0,63 | 8,96 % (10,70 % / 9,05 %) | 13,72 % / −33,7 % / 0,83 |
| B 1997-2009 | 4,67 % (1997-02 2,90 %, 2003-09 6,13 %) | −19,8 % | 0,57 | 2,65 % (1,98 % / 3,27 %) | 4,91 % / −55,2 % / 0,33 |

La cartera ejecutó solo 123 (A) y 126 (B) operaciones: con stop del 8 %, 1 % de riesgo por operación y tope del 6 % de riesgo total, queda poco invertida.

## Criterios
| Criterio | Periodo A | Periodo B |
|---|---|---|
| N ≥ 300 operaciones | Sí (519) | Sí (398) |
| Q1. Esperanza > 0 con IC inferior > 0 y positiva en cada tramo | Sí | Sí (1997-02: IC incluye 0 pero la media es positiva; el criterio se cumple por el IC del total) |
| **Q2. Diferencia vs placebo con IC inferior > 0** | **No** (−0,03 al 99,29 %) | **Sí** (+0,07 al 95 %) |
| Q3. CAGR de cartera > mediana placebo en cada tramo | No | Sí |
| Riesgo/retorno vs SPY (Sharpe ≥ SPY o…) | No | Sí |

## Veredicto registrado
**H7 no es candidata**: exigía pasar N, Q1 y Q2 en **ambos** periodos y no pasó Q2 en el periodo A (por un margen estrecho: el límite inferior es −0,03 R con la corrección de Bonferroni de k = 7).
No se prueban variantes, no se baja el nivel de confianza para rescatarla y la prueba final 2021-2026 no se desbloquea.

## Lectura (sin cambiar el veredicto)
- A diferencia de H1-H6, aquí la **diferencia frente al placebo es positiva en los dos periodos independientes** (+0,22 R y +0,29 R) y significativa en 1997-2009. Es el único sistema probado con ese patrón. Es un indicio, no una demostración:
  la regla registrada exigía significación en ambos periodos con la corrección por pruebas múltiples.
- La señal parece añadir algo por operación (Trend Template + base estrecha + stop corto + salida por MA50), pero **la cartera con tus reglas de riesgo rinde poco** (5 % anual en 2010-2020 frente al 13,7 % de SPY) porque casi nunca está invertida.
  En 1997-2009, con un índice muy malo, sí superó a SPY con caídas mucho menores.
- Dos explicaciones posibles que no se pueden separar con estos datos: ventaja real en la señal o dependencia del régimen de mercado.

## Limitaciones
Aproximación mecánica del método (sin fundamentales ni lectura discrecional de gráficos); universo de grandes empresas, no small/mid caps de crecimiento; rango RS calculado solo entre miembros del S&P 500; coste y ejecución hipotéticos; datos de un tercero sin licencia clara;
siete hipótesis probadas en esta fase. Un resultado no significativo con la corrección exigida no demuestra que no exista ventaja.

## Siguiente paso posible (solo con acuerdo explícito)
Una nueva prueba independiente, registrada antes: el mismo H7 **sin cambios** en un universo distinto (acciones fuera del S&P 500, que requiere datos de Tiingo con plan de pago o una muestra reducida) y/o desbloquear 2021-2026 si el usuario decide asumir que H7 se trate como candidata a título excepcional (no recomendado: contradice la regla registrada).
