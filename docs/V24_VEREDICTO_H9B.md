# Veredicto H9b · comprar caídas en el S&P 500 (criterios de `docs/V24_H9B_CAIDAS_SP500.md`, sin modificarlos)

Fichero: `results/v24/v24_dip_42788188319.json` · commit `212b793` · S&P 500 point-in-time con deslistadas (~500 miembros con precio por día) · prueba final 2021-2026 **no cargada** · coste 0,10 % por lado.
Señal: cruce a una caída del 15-35 % desde el máximo de cierre de 60 sesiones, sobre la SMA200. Salidas: cierre > SMA20, 20 sesiones, o stop del 12 % bajo la entrada. Placebo: entradas aleatorias con las mismas salidas y el mismo stop (10 semillas).

## Por operación (esperanza en múltiplos de R, con R = 12 % de la entrada)
| | Operaciones | H9b (IC 95 %) | Aciertos | Placebo | Diferencia (IC) |
|---|---|---|---|---|---|
| **Periodo A 2010-2020** | 2.652 | **0,060 R** (0,036 a 0,084); entren. 0,076 R, valid. 0,029 R | 67,7 % | 0,009 R (57,3 % aciertos) | **+0,050 R, IC 99,44 % [+0,018 ; +0,083]** |
| **Periodo B 1997-2009** | 4.261 | **0,084 R** (0,063 a 0,105); 1997-02 0,080 R, 2003-09 0,089 R | 69,0 % | −0,001 R (57,0 %) | **+0,085 R, IC 95 % [+0,063 ; +0,106]** |

## Cartera (1 % de riesgo por operación, 6 % total, 20 % de peso máximo)
| | CAGR | Caída máx. | Sharpe | Mediana CAGR placebo | SPY (CAGR / caída / Sharpe) |
|---|---|---|---|---|---|
| A 2010-2020 | 2,38 % (entren. 0,25 %, valid. 6,15 %) | −27,8 % | 0,25 | 0,59 % (0,89 % / 0,06 %) | 13,72 % / −33,7 % / 0,83 |
| B 1997-2009 | 3,65 % (1997-02 4,63 %, 2003-09 2,69 %) | −38,8 % | 0,33 | −1,62 % (−2,77 % / 0,72 %) | 4,91 % / −55,2 % / 0,33 |

## Criterios
| Criterio | Periodo A | Periodo B |
|---|---|---|
| N ≥ 300 operaciones | Sí (2.652) | Sí (4.261) |
| Q1. Esperanza > 0 con IC inferior > 0 y positiva en cada tramo | **Sí** | **Sí** |
| **Q2. Diferencia vs placebo con IC inferior > 0** | **Sí** (+0,018 al 99,44 %) | **Sí** (+0,063 al 95 %) |
| Q3. CAGR de cartera > mediana placebo en cada tramo | **No** (entrenamiento 0,25 % < 0,89 %) | Sí |
| Riesgo/retorno vs SPY | No | Sí |

## Veredicto registrado
**H9b es CANDIDATA** (cumple N, Q1 y Q2 en ambos periodos independientes, incluida la burbuja tecnológica y 2008). **No supera al índice** (falla Q3 y riesgo/retorno en el periodo A).
Es la primera de las nueve hipótesis registradas que cumple los criterios de candidatura. La prueba final 2021-2026 **sigue bloqueada** y solo se abrirá, una única vez, con confirmación explícita del usuario.

## Lectura
- **La ventaja existe frente al azar, pero es pequeña:** ~0,06-0,08 R por operación (con R = 12 % de la entrada, del orden de un +0,7-1 % por operación tras costes del 0,10 % por lado) y 68-69 % de aciertos frente al 57 % del placebo.
- **Como cartera con las reglas de riesgo de la app no aprovecha esa ventaja:** CAGR de 2,4 % (2010-2020) y 3,7 % (1997-2009), porque las operaciones duran pocos días y con 1 % de riesgo y stop del 12 % la cartera está casi siempre en efectivo.
  Una implementación que despliegue más capital sería otra hipótesis, a registrar antes de probarla.
- **Sensibilidad a costes:** con una ventaja de ~0,7 % por operación, costes y deslizamientos reales mayores del 0,10 % por lado podrían eliminarla. Aún no se ha medido (propuesta: prueba de sensibilidad a 0,20 % y 0,30 % por lado sobre los periodos ya abiertos).
- **Posible sesgo optimista residual:** valores que dejan de cotizar con la posición abierta se cierran al último precio disponible; en quiebras bruscas puede ser optimista.
- **Desglose tecnológico (descriptivo, sesgado por la clasificación incompleta de deslistadas):** tecnológicas clasificadas 0,044 R (A, IC −0,02 a 0,11; 411 operaciones) y 0,103 R (B; 640) frente a 0,063 R y 0,081 R del resto: sin diferencia clara.
  No es una prueba sobre tecnológicas.

## Limitaciones
Solo S&P 500 (empresas grandes y líquidas); coste hipotético; datos de un tercero sin licencia clara y sin auditoría independiente; nueve hipótesis probadas en total (Bonferroni aplicado al periodo A);
efectivo sin rendimiento; el resultado por operación es modesto y no se ha medido la robustez frente a costes mayores.
