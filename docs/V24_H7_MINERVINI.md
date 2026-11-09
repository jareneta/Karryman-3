# H7 · sistema tipo Minervini (Trend Template + VCP + stop corto) · registro previo

Fecha de registro: 2026-11-09, **antes de ejecutar H7**. Las secciones 1-5 no se editan; los cambios van como enmienda fechada al final.
**Aviso:** son reglas operativas que fijo yo a partir de la descripción pública del Trend Template y del método SEPA (no una réplica exacta ni la lectura subjetiva de gráficos
de Minervini). Si el sistema real difiere, esta prueba no lo valida ni lo refuta.

## 1. Reglas
- **Trend Template (filtro diario, todo con datos hasta el cierre):** cierre > MA150 y > MA200; MA150 > MA200; MA200 subiendo (hoy > hace 20 sesiones); MA50 > MA150 y > MA200; cierre > MA50;
  cierre ≥ 30 % sobre el mínimo de 252 sesiones; cierre dentro del 25 % del máximo de 252 sesiones; **rango de fuerza relativa ≥ 70** (percentil tipo IBD: 40 % rentabilidad 3 meses + 20 % cada una de 6, 9 y 12 meses,
  calculado entre los valores líquidos del universo ese día); precio ≥ 5 $ y volumen medio de 50 sesiones ≥ 500.000.
- **Entrada (VCP aproximada con las definiciones del motor `entry='base'`):** base de al menos 5 semanas, profundidad ≤ 35 %, subida previa ≥ 30 %, estrechez del lado derecho ≤ 12 % (rango de las 10 últimas sesiones / cierre),
  rotura del máximo de la base (cierre > máximo y la sesión anterior no) con volumen ≥ 1,4 × la media de 50 sesiones; no se compra si el cierre o la apertura siguiente superan el pivote más de un 5 %. Orden a la apertura siguiente.
- **Stop:** el más ajustado entre el mínimo de 10 sesiones y un **8 % bajo el precio de entrada**. R = entrada − stop. Sin entrada si el riesgo > 12 %.
- **Salidas:** al llegar a +3R se vende 1/3 y el stop del resto sube a breakeven; el resto sale con un **cierre diario bajo la MA50**. Sin clímax y sin filtro de mercado.
- **Cartera:** 1 % de riesgo por operación, 6 % de riesgo abierto total, 20 % de peso máximo; coste 0,10 % por lado; sin apalancamiento.
- **Fuera del alcance (no comprobable con datos de la fecha):** criterios de fundamentales de SEPA (aceleración de beneficios y ventas, etc.) y lectura discrecional del gráfico.

## 2. Datos, periodos y bloqueo
- Universo: S&P 500 point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`); solo cuentan los días en que el valor era miembro. **Limitación:** son empresas grandes; Minervini opera sobre todo small/mid caps de crecimiento.
  El rango de fuerza relativa se calcula entre los miembros del S&P 500, no entre todo el mercado.
- **Periodo A: 2010-01-01 a 2020-12-31** (entrenamiento 2010-16, validación 2017-20) y **periodo B: 1997-01-01 a 2009-12-31** (confirmación independiente, calentamiento desde 1996).
- **Prueba final 2021-2026 bloqueada** (no se carga); solo se abrirá si H7 es candidata y el usuario lo confirma.
- Posiciones abiertas cuando un valor deja de cotizar: cierre al último precio disponible.

## 3. Controles
SPY; **placebo de entrada aleatoria** (fechas aleatorias entre valores líquidos y miembros, **mismo stop (8 %/10 sesiones) y mismas salidas**), 10 semillas, para operaciones y para carteras, en cada periodo.

## 4. Criterios (fijados antes)
Siete hipótesis probadas en total en esta fase (Bonferroni k = 7: nivel 99,29 % en el periodo A).
- **N.** Al menos 300 operaciones por periodo; si no, el periodo es "inconclusivo".
- **Q1.** Esperanza en R > 0 con IC 95 % inferior > 0 en todo el periodo, y media > 0 en cada uno de sus dos tramos.
- **Q2.** Diferencia de esperanza H7 − placebo agrupado con IC inferior > 0 (periodo A al 99,29 %; periodo B al 95 %).
- **Q3 (cartera).** CAGR de H7 > mediana de CAGR de las 10 carteras placebo en cada tramo de cada periodo.
- **H7 es candidata** si cumple N, Q1 y Q2 en **ambos** periodos. **Supera al índice** si además cumple Q3 y, en el periodo completo de cada uno, Sharpe ≥ SPY o (Calmar ≥ SPY y CAGR ≥ 80 % del de SPY).
- Si no es candidata: conclusión "no hay ventaja demostrable"; no se prueban variantes (otros umbrales, stops, salidas, filtros de mercado).

## 5. Qué NO se hará
Cambiar umbrales (30 %, 25 %, RS 70, 8 %, +3R, MA50), añadir filtros, elegir periodos después de ver resultados, mirar 2021-2026.
