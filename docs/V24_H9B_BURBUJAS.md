# H9b en la burbuja punto com y en las correcciones tecnológicas de 2015-2026 · registro previo

Fecha de registro: 2026-11-20, **antes de ejecutar**. Secciones 1-6 no se editan; cambios como enmienda fechada al final.

## 0. Naturaleza
**Análisis exploratorio por subperiodos** de las operaciones ya definidas de H9b (comprar caídas del 15-35 % desde el máximo de 60 sesiones, cierre > SMA200, stop 12 %, salida sobre SMA20 o 20 sesiones; `docs/V24_H9B_CAIDAS_SP500.md`). **No hay parámetros nuevos ni hipótesis nueva que cuente en Bonferroni**; los contrastes no están corregidos por multiplicidad y se leen como indicativos, no como evidencia.

## 1. Datos
`sp500data` `snapshot-2026-11` (S&P 500 point-in-time con deslistadas), 1996-01-01 a 2026-10-30 (último dato del snapshot; no incluye las caídas de noviembre). Se ejecuta con `V24_REGIMEN=2015` porque el usuario abrió 2021-2026.

## 2. Ventanas (por fecha de entrada; fijadas ahora a partir de fechas públicas de picos y suelos del Nasdaq)
- **Punto com:** D0 burbuja alcista 1998-10-09 a 2000-03-24; D1 caída 2000-03-25 a 2002-10-09; D2 recuperación 2002-10-10 a 2004-12-31.
- **Correcciones recientes:** C2018 2018-08-30 a 2018-12-24; C2020 2020-02-20 a 2020-03-23; C2022 2021-11-22 a 2022-12-28; C2026 2026-10-07 a 2026-10-30 (solo los datos disponibles).
- **Estado del mercado en la señal** (caída de SPY desde su máximo de 252 sesiones al cierre de la señal): >−5 %, −5 a −10 %, −10 a −20 %, < −20 %; por separado en 1998-2004 y en 2015-2026. Los tramos incluyen su límite inferior (−10 % cae en "−5 a −10 %"; −5 % cae en ">−5 %").
- **Tecnológicas** (SIC de la SEC, cobertura incompleta: 35,6 % de deslistadas): tecnológicas clasificadas frente al resto/sin clasificar, descriptivo y sesgado.

## 3. Medidas
Por ventana: nº de operaciones, esperanza en R (media), % ganadoras, IC 95 % por remuestreo de meses de entrada, esperanza del **placebo** (entradas aleatorias entre valores líquidos y miembros, mismas salidas, 10 semillas; mediana de las medias) y diferencia. Equivalencia aproximada: 1 R ≈ 12 % del importe.

## 4. Lectura (fijada antes)
- Ventana con N < 100: "no concluyente"; 100 ≤ N < 300: "indicativo"; N ≥ 300: evaluable.
- "Señal de ventaja" en una ventana si la diferencia con el placebo es positiva y el IC 95 % por meses de la diferencia de medias de R (operaciones − placebo agrupado) excluye 0, **sin corregir por multiplicidad**.
- Ningún resultado de este análisis cambia la conclusión de H9b ni abre variantes.

## 5. Limitaciones declaradas
Operaciones independientes (sin cartera ni capital limitado); las ventanas cortas tienen pocas operaciones y se solapan en el tiempo (correlación entre operaciones); 2000-2002 y 2018-2026 son pocos episodios; clasificación tecnológica sesgada; el Nasdaq no es el universo (solo valores del S&P 500); costes 0,10 % por lado.

## 6. Qué NO se hará
Cambiar umbrales de H9b, mover ventanas tras ver los resultados, elegir ventanas "mejores", declarar el análisis como evidencia de ventaja.
