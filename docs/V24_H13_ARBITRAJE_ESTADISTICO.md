# H13 · arbitraje estadístico diario: reversión a corto plazo, larga-corta y neutral al mercado (inspirado en Simons) · registro previo

Fecha de registro: 2026-11-13, **antes de ejecutar H13**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.

## 0. Alcance y advertencia
Renaissance Technologies (Jim Simons) es conocida por estrategias estadísticas de muy corto plazo, largas y cortas, neutrales al mercado y apalancadas, con datos e infraestructura propios. **Eso no es reproducible aquí** (sin alta frecuencia ni datos propios).
H13 prueba solo una versión pública y diaria de la idea con datos que sí tenemos. Un resultado negativo no dice nada sobre Renaissance; solo sobre esta versión. Vender en corto requiere cuenta de margen y préstamo de acciones (coste y riesgo adicionales).

## 1. Estrategia
- **Universo:** miembros del S&P 500 cada día (point-in-time, con deslistadas; `sp500data`, `snapshot-2026-11`) con precio ≥ 5 $ y mediana de 60 sesiones de volumen en dólares ≥ 5 M$.
- **Señal (reversión de 5 sesiones):** s(t) = −(Cierre(t) / Cierre(t−5) − 1), calculada con el cierre de la sesión *t*. Cuanto mayor, más "comprable" (más ha caído).
- **Cartera cada día:** largo en el **decil superior** de s, corto en el **decil inferior**, peso igual dentro de cada lado, **dólar-neutral** (1 de nominal largo y 1 corto). Órdenes a la apertura de *t+1*; cada posición rinde de la apertura de *t+1* a la de *t+2* y la cartera se reajusta diariamente.
- **Costes:** 0,10 % por lado sobre el nominal operado (rotación diaria) + coste de préstamo de las posiciones cortas del 1 %/año (hipótesis conservadora). Sin rendimiento sobre el efectivo. Valores sin precio al día siguiente (deslistados) aportan rentabilidad 0 y salen de la cartera.
- La rentabilidad se expresa **por cada 1 de nominal largo** (sin apalancamiento adicional sobre esa base).

## 2. Datos, periodos y bloqueo
**Periodo A: 2010-01-01 a 2020-12-31** (entrenamiento 2010-16, validación 2017-20) y **periodo B: 1997-01-01 a 2009-12-31** (P1 1997-02, P2 2003-09; calentamiento desde 1996). **Prueba final 2021-2026 bloqueada.**

## 3. Controles
- **Placebo de señal obsoleta:** la misma cartera, pero con la señal calculada con datos de 20 sesiones antes (s(t−20)) y de 40 sesiones antes (s(t−40)). Misma rotación y mismo universo, sin información actual.
- SPY (para correlación, beta y comparación de rentabilidad).

## 4. Criterios (fijados antes)
Trece hipótesis probadas en esta fase (Bonferroni k = 13: nivel 99,62 % en el periodo A; 95 % en el B).
- **J1 (esperanza neta positiva).** En cada periodo, la media de las rentabilidades mensuales **netas** de H13 tiene IC con límite inferior > 0.
- **J2 (es la señal).** En cada tramo (2010-16, 2017-20, 1997-02, 2003-09), el Sharpe neto de H13 es mayor que el de cada placebo (obsoleto-20 y obsoleto-40).
- **H13 tiene esperanza matemática positiva** si cumple J1 y J2 en **ambos** periodos.
- **H13 "supera al S&P 500"** si además, en cada periodo, su CAGR neto (sobre 1 de nominal largo) > CAGR de SPY **y** su Sharpe ≥ el de SPY.
- Si no cumple J1 y J2: "no hay esperanza positiva demostrada en esta versión"; sin variantes.
- La prueba final 2021-2026 solo se abriría una vez y con confirmación explícita del usuario.

## 5. Sensibilidades (se informan, no deciden)
Horizonte de 1 y de 21 sesiones; costes de 0,05 % y 0,20 % por lado; solo el lado largo (neto de costes) frente a SPY; correlación y beta con SPY.

## 6. Limitaciones declaradas
Precios ajustados de un tercero; coste de préstamo único y constante (en la práctica varía y algunos valores no son prestables); ejecución a la apertura sin deslizamiento adicional; sin impuestos; riesgo de recompra forzada no modelado; S&P 500 grandes y líquidas, donde la reversión es más débil que en valores pequeños.

## 7. Qué NO se hará
Cambiar el horizonte (5 sesiones), el decil, los costes o el universo tras ver resultados; elegir una sensibilidad como principal; elegir periodos a posteriori; mirar 2021-2026 sin confirmación.
