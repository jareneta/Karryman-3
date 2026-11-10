# H10 · sistema tipo William O'Neil (CAN SLIM, parte técnica) · registro previo

Fecha de registro: 2026-11-10, **antes de ejecutar H10**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.
**Aviso:** son reglas mecánicas fijadas por mí a partir de la descripción pública de CAN SLIM. No son una réplica exacta ni su lectura discrecional de gráficos.
Quedan **fuera** de la prueba **C** y **A** (beneficios trimestrales y anuales) e **I** (patrocinio institucional): no se pueden comprobar con datos de la fecha en este conjunto. Se prueban **N, S, L y M** más su gestión de ventas.

## 1. Reglas
- **L (líder):** rango de fuerza relativa ≥ 80 (percentil IBD: 40 % rentabilidad 3 meses + 20 % cada una de 6, 9 y 12 meses, entre los valores líquidos miembros ese día); cierre > MA50 > MA200 con MA200 subiendo; cierre dentro del 15 % del máximo de 252 sesiones; precio ≥ 5 $ y volumen medio de 50 sesiones ≥ 500.000.
- **N (nuevo máximo desde una base):** el motor de bases (`entry='base'`): subida previa ≥ 30 %, rotura del máximo de la base (cierre > máximo y la sesión anterior no), estrechez del lado derecho ≤ 12 %,
  y una de dos: **base ≥ 7 semanas (35 sesiones) con profundidad ≤ 33 %** (taza con asa o doble suelo) **o base ≥ 5 semanas con profundidad ≤ 15 %** (base plana).
- **S (oferta y demanda):** volumen del día de la rotura ≥ 1,5 × la media de 50 sesiones.
- **M (mercado):** solo se compra si el cierre de SPY > su media de 50 sesiones. Sin compras si no.
- **Entrada:** apertura de la sesión siguiente a la rotura; sin entrada si el cierre o la apertura superan el pivote más de un 5 %.
- **Stop (7-8 % de O'Neil):** **fijo un 8 % bajo el precio de entrada** (no el mínimo de la base), por cierre.
- **Ventas:** (a) **beneficio:** se vende todo cuando el máximo del día alcanza **+25 %** sobre la entrada; (b) **regla de las 8 semanas:** si el máximo alcanza **+20 % dentro de las 15 primeras sesiones**, no se vende en +25 % y se mantiene hasta la sesión 40 (8 semanas), con el stop del 8 % vigente, saliendo entonces a la apertura siguiente.
  Sin salidas por clímax ni por cierre bajo la MA50 (no definibles sin parámetros adicionales).
- **Cartera:** 1 % de riesgo por operación (R = 8 % de la entrada), 6 % de riesgo abierto total, 20 % de peso máximo; coste 0,10 % por lado; sin apalancamiento.

## 2. Datos, periodos y bloqueo
Universo S&P 500 point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`). **Periodo A: 2010-01-01 a 2020-12-31** (entrenamiento 2010-16, validación 2017-20) y **periodo B: 1997-01-01 a 2009-12-31** (calentamiento desde 1996).
**Prueba final 2021-2026 bloqueada.** Posiciones abiertas cuando un valor deja de cotizar: cierre al último precio disponible.
**Limitaciones declaradas:** empresas grandes (O'Neil busca líderes de crecimiento, a menudo más pequeños); sin fundamentales ni patrocinio institucional; rango RS solo entre miembros del S&P 500.

## 3. Controles
SPY; **placebo de entrada aleatoria** entre valores líquidos y miembros (sin filtros de tendencia, rango ni mercado; mismas salidas y mismo stop fijo del 8 %, incluida la regla de las 8 semanas), 10 semillas, para operaciones y carteras, en cada periodo.
La comparación mide por tanto el conjunto de filtros N, S, L y M frente a entrar al azar.

## 4. Criterios (fijados antes)
Diez hipótesis probadas en esta fase (Bonferroni k = 10: nivel 99,5 % en el periodo A; 95 % en el B).
- **N.** ≥ 300 operaciones por periodo, si no "inconclusivo".
- **Q1.** Esperanza en R > 0 con IC 95 % inferior > 0 en el periodo completo, y media > 0 en cada tramo.
- **Q2.** Diferencia H10 − placebo con IC inferior > 0 (A al 99,5 %; B al 95 %).
- **Q3.** CAGR de la cartera > mediana de las 10 carteras placebo en cada tramo.
- **Candidata** si cumple N, Q1 y Q2 en **ambos** periodos. **Supera al índice** si además cumple Q3 y, en cada periodo, Sharpe ≥ SPY o (Calmar ≥ SPY y CAGR ≥ 80 % del de SPY).
- Si no es candidata: "no hay ventaja demostrable"; sin variantes (umbrales de RS, volumen, +25 %, +20 %/15 sesiones, 40 sesiones, 8 %).

## 5. Qué NO se hará
Cambiar los umbrales, añadir salidas por clímax o MA50, elegir periodos a posteriori, mirar 2021-2026.

## 6. Pendiente relacionado (no parte de H10)
La prueba de sensibilidad a costes de H9b sigue pendiente y no se mezcla con esta hipótesis.
