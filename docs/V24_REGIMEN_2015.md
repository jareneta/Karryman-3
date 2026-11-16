# Protocolo: repetir los backtests en el régimen 2015 → actualidad · registro previo

Fecha de registro: 2026-11-16, **antes de ejecutar nada de este protocolo**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.

## 0. Origen y consecuencias
El usuario plantea la teoría de que **desde 2015 la manera de entender y operar el mercado es distinta** por la tecnología actual, y pide pasar los backtests solo en 2015 → actualidad (datos hasta 2026-10-30).
- **Esto abre 2021-2026**, el tramo que se había mantenido bloqueado como prueba final, **para todas las hipótesis a la vez**, por decisión expresa del usuario. A partir de aquí no queda ningún periodo histórico sin mirar; solo quedará el futuro.
- La teoría del cambio de régimen es **una hipótesis del usuario formulada antes de ver resultados por régimen**, no derivada de resultados. No se interpreta nada causal sobre la tecnología.

## 1. Qué se repite
Todas las pruebas con acciones y con índice ya registradas, **con sus reglas y criterios originales, sin ningún cambio de parámetros**:
V24 y variantes (`docs/V24_RESULTADOS.md`), H1-H4 (`V24_HIPOTESIS.md`), H5 (`V24_H5_PLAN_HTML.md`), H6 (`V24_H6_MOMENTUM_63.md`), H7 (`V24_H7_MINERVINI.md`), H8 (`V24_H8_KELL.md`), H9b (`V24_H9B_CAIDAS_SP500.md`), H10 (`V24_H10_ONEIL.md`),
H11 (`V24_H11_SPY_MAS_CAIDAS.md`), H12 (`V24_H12_INDICE_APALANCADO.md`), H13 (`V24_H13_ARBITRAJE_ESTADISTICO.md`) y H14 (`V24_H14_LIQUIDEZ_FED.md`). No se repite el escaneo de anomalías ni la replicación de H2 (periodo 1997-2009).

## 2. Datos y tramos
Universo S&P 500 point-in-time con deslistadas (`sp500data`, `snapshot-2026-11`, precios hasta 2026-10-30); índices desde `^GSPC`/`^IRX`. Se usa historial anterior a 2015 **solo para calentar indicadores**.
Evaluación en **un único periodo N = 2015-01-01 a 2026-10-31**, dividido en dos tramos: **S1 2015-2020** y **S2 2021-2026**. (S1 coincide con el tramo final de 2010-2020, ya visto; **S2 no se había visto con estas hipótesis**: es la parte con más valor de contraste.)

## 3. Criterios (los de cada hipótesis, adaptados solo en la forma, no en el fondo)
- Cada hipótesis se evalúa **una vez, en el periodo N**, con los **mismos criterios que tenía su periodo A**: IC con **Bonferroni k = 14** (nivel 99,64 %), y los criterios por tramo (los dos tramos S1 y S2 hacen de "entrenamiento" y "validación").
- Se mantienen los controles originales (placebos con 10 semillas, SPY, entradas aleatorias, señales obsoletas, etc.) y los costes originales.
- **"Candidata" o "supera al S&P 500"** solo si cumple los criterios exigidos en la hipótesis original, dentro de N y en **ambos tramos** (S1 y S2).
- Se informa también, de forma **descriptiva y sin decidir nada**, la comparación del resultado en N frente a los periodos anteriores (2010-2020 y 1997-2009) para contrastar con datos la teoría del usuario sobre un cambio de régimen.

## 4. Qué NO se hará
Cambiar parámetros, umbrales o reglas de ninguna hipótesis; elegir otro periodo o tramos después de ver resultados; presentar como validado algo que no cumpla los criterios en los dos tramos; usar el periodo 2021-2026 para reajustar una hipótesis y volver a probarla en él.

## 5. Limitaciones declaradas
Muestra de unos 11-12 años (menos potencia; sistemas poco activos pueden quedar "inconclusivos" por pocas operaciones); N incluye la caída de 2020 y el mercado bajista de 2022; el solapamiento con 2010-2020 en S1 reduce la independencia entre resultados;
catorce hipótesis probadas en total; datos de un tercero sin licencia clara.

## 6. Entregables
Para cada hipótesis, el resultado en N, S1 y S2 y su veredicto, más una tabla comparativa con los periodos anteriores, en `docs/V24_RESULTADOS_2015.md`, con los ficheros en `results/v24/`.
