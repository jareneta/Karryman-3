# H9b · comprar caídas en acciones del S&P 500 (sin filtro sectorial) · registro previo

Fecha de registro: 2026-11-10, **antes de ejecutar H9b**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.
Origen: H9 (solo tecnológicas) quedó inconclusiva porque la clasificación sectorial de las deslistadas cubre el 35,6 % (< 70 % exigido; ver `docs/V24_H9_CAIDAS_TECH.md`). H9b elimina el filtro sectorial para poder medir **comprar caídas** con datos completos y sin sesgo de supervivencia.

## 1. Universo
Miembros del S&P 500 cada día, point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`); sin filtro de sector.

## 2. Reglas (idénticas a H9 salvo el filtro sectorial)
- **Señal de caída** en la sesión *i*: el cierre está entre un 15 % y un 35 % por debajo del máximo de cierre de las 60 sesiones previas (*i−60…i−1*), era < 15 % por debajo el día anterior (evento de cruce) y el cierre > SMA200;
  precio ≥ 5 $ y volumen medio de 50 sesiones ≥ 500.000; el valor es miembro ese día.
- **Entrada:** apertura de *i+1*; sin entrada si la apertura se aleja más de un 5 % del cierre de la señal (por encima o por debajo).
- **Salidas:** stop por cierre un 12 % bajo la entrada; salida (apertura siguiente) cuando el cierre supera la SMA20, o tras 20 sesiones; sin parciales.
- **Cartera:** 1 % de riesgo por operación (R = 12 % de la entrada), 6 % de riesgo abierto total, 20 % de peso máximo; coste 0,10 % por lado; sin apalancamiento.

## 3. Datos, periodos y bloqueo
**Periodo A: 2010-01-01 a 2020-12-31** (entrenamiento 2010-16, validación 2017-20) y **periodo B: 1997-01-01 a 2009-12-31** (incluye la burbuja tecnológica y 2008). **Prueba final 2021-2026 bloqueada.**
Posiciones abiertas cuando un valor deja de cotizar: cierre al último precio disponible (optimista en quiebras).

## 4. Controles
SPY; **placebo de entrada aleatoria** entre los valores líquidos y miembros (mismas salidas y mismo stop fijo del 12 %), 10 semillas, para operaciones y carteras, en cada periodo.

## 5. Criterios (fijados antes)
Nueve hipótesis probadas en esta fase (Bonferroni k = 9: nivel 99,44 % en el periodo A; 95 % en el B).
- **N.** ≥ 300 operaciones por periodo; si no, "inconclusivo".
- **Q1.** Esperanza en R > 0 con IC 95 % inferior > 0 en el periodo completo, y media > 0 en cada tramo.
- **Q2.** Diferencia H9b − placebo con IC inferior > 0 (A al 99,44 %; B al 95 %).
- **Q3.** CAGR de la cartera > mediana de las 10 carteras placebo en cada tramo.
- **Candidata** si cumple N, Q1 y Q2 en **ambos** periodos. **Supera al índice** si además cumple Q3 y, en cada periodo, Sharpe ≥ SPY o (Calmar ≥ SPY y CAGR ≥ 80 % del de SPY).
- Si no es candidata: "no hay ventaja demostrable"; sin variantes (umbrales de caída, ventana de 60 sesiones, salidas, filtros).

## 6. Análisis descriptivo declarado (no decide nada)
Para las operaciones de H9b se reporta además la esperanza en R separando las empresas **clasificadas como tecnológicas por SIC** (`results/v24/v24_sic_42786246641.json`: 3570-3579, 3660-3679, 7370-7379) del resto,
**con el aviso de que la clasificación de deslistadas es incompleta (35,6 %) y por tanto ese desglose está sesgado a favor de supervivientes**. No cuenta para los criterios.

## 7. Qué NO se hará
Cambiar umbrales, añadir filtros, elegir periodos a posteriori, presentar el desglose tecnológico como prueba, mirar 2021-2026.
