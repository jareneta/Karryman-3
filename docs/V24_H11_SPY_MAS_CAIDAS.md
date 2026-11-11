# H11 · S&P 500 como base + comprar caídas como complemento · registro previo

Fecha de registro: 2026-11-11, **antes de ejecutar H11**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.

## 0. Motivación
De las diez hipótesis anteriores solo **H9b (comprar caídas en el S&P 500)** mostró ventaja por operación frente al azar en dos periodos independientes (`docs/V24_VEREDICTO_H9B.md`: +0,05 R y +0,085 R). Como cartera aislada rendía poco (2,4 % y 3,7 % anual) porque está casi siempre en efectivo, sin rendimiento.
La pregunta de H11 es si esa ventaja, **sumada a una base que siempre está invertida en el mercado**, produce un rendimiento mayor que el del S&P 500.

## 1. Estrategia (primaria; sin parámetros nuevos)
- **Base:** todo el capital no asignado a operaciones está invertido en **SPY** (rendimiento diario de SPY; sin coste por mover efectivo hacia/desde SPY, limitación declarada).
- **Complemento:** exactamente las reglas de H9b (`docs/V24_H9B_CAIDAS_SP500.md`): cruce a una caída del 15-35 % desde el máximo de cierre de 60 sesiones previas, cierre > SMA200, miembro del S&P 500 ese día, precio ≥ 5 $ y volumen medio de 50 sesiones ≥ 500.000;
  entrada a la apertura siguiente; stop por cierre 12 % bajo la entrada; salida al cerrar sobre la SMA20 o a las 20 sesiones. Tamaño: 1 % de riesgo por operación (R = 12 % de la entrada), 6 % de riesgo abierto total, 20 % de peso máximo; coste 0,10 % por lado.
- Sin apalancamiento. Las operaciones se financian con el efectivo (la parte de la base en SPY).

## 2. Datos, periodos y bloqueo
Universo S&P 500 point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`). **Periodo A: 2010-01-01 a 2020-12-31** (entrenamiento 2010-16, validación 2017-20) y **periodo B: 1997-01-01 a 2009-12-31**. **Prueba final 2021-2026 bloqueada.**
Posiciones abiertas cuando un valor deja de cotizar: cierre al último precio disponible. SPY se toma de los mismos datos (precio ajustado).

## 3. Controles
- **SPY comprado y mantenido** (referencia: la cartera sin complemento es exactamente SPY).
- **Placebo del complemento:** entradas en fechas aleatorias entre valores líquidos y miembros, con el mismo stop del 12 %, las mismas salidas y el mismo tamaño, también con el resto en SPY; 10 semillas. Aísla si el exceso sobre SPY viene de la señal de caída o solo de operar.

## 4. Criterios (fijados antes)
Once hipótesis probadas en esta fase (Bonferroni k = 11: nivel 99,55 % en el periodo A; 95 % en el B).
- **E1 (supera al S&P 500).** En cada periodo, CAGR de H11 > CAGR de SPY **y** el IC de la media de la diferencia de rentabilidades mensuales (H11 − SPY) tiene límite inferior > 0 (A al 99,55 %; B al 95 %).
- **E2 (es la señal, no el azar).** CAGR de H11 > mediana de CAGR de las 10 carteras placebo (con SPY), en cada tramo (2010-16, 2017-20, 1997-02, 2003-09).
- **E3 (riesgo).** En cada periodo: Sharpe de H11 ≥ Sharpe de SPY y caída máxima de H11 no peor que la de SPY.
- **H11 "supera al S&P 500"** si cumple E1, E2 y E3 en **ambos** periodos. En ese caso la prueba final 2021-2026 se abriría **una sola vez y solo con confirmación explícita del usuario**.
- Si no cumple: conclusión "no hay evidencia de que supere al S&P 500"; sin variantes.

## 5. Sensibilidades declaradas (se informan, **no deciden**)
Costes de 0,20 % y 0,30 % por lado en el complemento; riesgo por operación del 2 % y del 3 % (con tope de riesgo total de 12 % y 18 %). Si H11 cumple los criterios con costes de 0,10 % pero pierde el exceso con 0,20 %, se advierte expresamente en el veredicto.

## 6. Limitaciones declaradas
Usa SPY (un ETF) como base de la cartera; no incluye costes por mover efectivo hacia/desde SPY ni impuestos; el exceso, si existe, procede de un complemento de ventaja pequeña por operación; empresas grandes; datos de un tercero sin licencia clara; once hipótesis probadas en total.

## 7. Qué NO se hará
Cambiar el tamaño, los umbrales de caída o las salidas tras ver resultados; elegir la sensibilidad "mejor" como primaria; elegir periodos a posteriori; mirar 2021-2026 sin confirmación.
