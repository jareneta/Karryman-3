# H8 · sistema tipo Oliver Kell (Wedge Pop + EMA Crossback) · registro previo

Fecha de registro: 2026-11-09, **antes de ejecutar H8**. Las secciones 1-5 no se editan; los cambios van como enmienda fechada al final.
**Aviso:** son definiciones mecánicas fijadas por mí a partir de la descripción pública de sus patrones (ciclo de precio con medias exponenciales de 10 y 20 sesiones). No son una réplica exacta ni su lectura discrecional de gráficos;
si su método real difiere, esta prueba no lo valida ni lo refuta. Sin entradas por "Base n Break" ni salidas por "Exhaustion Extension" (no se pueden definir objetivamente sin parámetros arbitrarios).

## 1. Reglas
**Filtro común (F), con datos hasta el cierre:** precio ≥ 5 $ y volumen medio de 50 sesiones ≥ 500.000; cierre > MA50 > MA200; MA200 hoy > hace 20 sesiones; rango RS ≥ 70 (percentil IBD entre valores líquidos miembros ese día);
solo cuentan los días en que el valor es miembro del universo.

**Wedge Pop (WP)** en la sesión *i*:
1. Compresión: (máximo de los máximos − mínimo de los mínimos de las 5 sesiones previas *i−5…i−1*) / Cierre[*i−1*] ≤ 0,10.
2. EMA10 y EMA20 convergidas en *i−1*: |EMA10/EMA20 − 1| ≤ 0,02.
3. Cierre[*i−1*] ≤ máximo(EMA10, EMA20)[*i−1*] y Cierre[*i*] > EMA10[*i*] y > EMA20[*i*].
4. Volumen[*i*] ≥ 1,2 × media de 50 sesiones previas.
5. Cierre[*i*] > Apertura[*i*] y cierre en la mitad superior del rango del día.
Stop = mínimo de la sesión *i*.

**EMA Crossback (EC)** en la sesión *i*:
1. EMA20[*i*] > EMA20[*i−5*].
2. Máximo de las 15 últimas sesiones (incluida *i*) ≥ 0,98 × máximo de las 50 sesiones previas.
3. Mínimo(Mín[*i−2…i*]) ≤ 1,01 × EMA20[*i*] (toque de la media 20).
4. Cierre[*i−1*] ≤ EMA10[*i−1*], Cierre[*i*] > EMA10[*i*], Cierre[*i*] > Apertura[*i*] y Cierre[*i*] > Máximo[*i−1*].
Stop = mínimo de las sesiones *i−2…i*.

**Entrada:** orden a la apertura de *i+1* si WP o EC (y F) en *i*; no se entra si la apertura supera el cierre de la señal más de un 5 % ni si el riesgo (entrada − stop) > 10 %.
**Salidas:** stop por cierre; a **+3R se vende 1/3** y el stop del resto sube a breakeven; después el resto sale con un **cierre diario bajo la EMA20** (ejecución en la apertura siguiente). Sin filtro de mercado.
**Cartera:** 1 % de riesgo por operación, 6 % de riesgo abierto total, 20 % de peso máximo; coste 0,10 % por lado; sin apalancamiento.

## 2. Datos, periodos y bloqueo
Universo S&P 500 point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`). **Periodo A: 2010-01-01 a 2020-12-31** (entrenamiento 2010-16, validación 2017-20) y **periodo B: 1997-01-01 a 2009-12-31** (calentamiento desde 1996).
**Prueba final 2021-2026 bloqueada** (no se carga). Posiciones abiertas cuando un valor deja de cotizar: cierre al último precio disponible.
**Limitaciones declaradas:** empresas grandes (Kell opera sobre todo acciones de crecimiento más pequeñas); sin fundamentales ni lectura discrecional.

## 3. Controles
SPY; **placebo de entrada aleatoria** (fechas aleatorias entre valores líquidos y miembros, **mismo stop signal-based no disponible → se usa el mínimo de 10 sesiones previas** y las mismas salidas), 10 semillas, para operaciones y carteras, en cada periodo.
*(Nota: el control reutiliza el stop genérico del motor porque una entrada aleatoria no tiene señal propia; es una limitación del control, que puede favorecer algo a H8 si su stop es más ajustado.)*

## 4. Criterios (fijados antes)
Ocho hipótesis probadas en total en esta fase (Bonferroni k = 8: nivel 99,375 % en el periodo A; 95 % en el B).
- **N.** ≥ 300 operaciones por periodo, si no "inconclusivo".
- **Q1.** Esperanza en R > 0 con IC 95 % inferior > 0 en el periodo completo, y media > 0 en cada tramo.
- **Q2.** Diferencia H8 − placebo agrupado con IC inferior > 0 (periodo A al 99,375 %; periodo B al 95 %).
- **Q3 (cartera).** CAGR de H8 > mediana de CAGR de las 10 carteras placebo en cada tramo de cada periodo.
- **Candidata** si cumple N, Q1 y Q2 en **ambos** periodos. **Supera al índice** si además cumple Q3 y, en cada periodo, Sharpe ≥ SPY o (Calmar ≥ SPY y CAGR ≥ 80 % del de SPY).
- Si no es candidata: "no hay ventaja demostrable"; sin variantes (umbrales, partes, stops, salidas).

## 5. Qué NO se hará
Cambiar umbrales (0,10; 0,02; 1,2×; 1,01; 15/50 sesiones; +3R; EMA20), añadir salida por agotamiento o base-and-break después de ver resultados, elegir periodos a posteriori, mirar 2021-2026.
