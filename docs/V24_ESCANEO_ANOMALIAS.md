# Escaneo de anomalías estadísticas en el universo S&P 500 point-in-time · registro previo

Fecha de registro: 2026-11-16, **antes de ejecutar el escaneo**. Las secciones 1-6 no se editan; los cambios van como enmienda fechada al final.

## 0. Objetivo y advertencia
Buscar de forma sistemática patrones o anomalías estadísticas (variables que predigan las rentabilidades futuras) en el universo que estudiamos. **Probar muchas variables genera falsos positivos por azar**; por eso se declara el tamaño de la familia, se controla la tasa de falsos descubrimientos, se exige replicación en un periodo independiente y se mide el efecto neto de costes.
Es un escaneo **exploratorio**: sus supervivientes solo pueden convertirse en hipótesis que se registrarán y probarán aparte, con la prueba final 2021-2026 como único contraste nuevo.

## 1. Familia A: señales de sección cruzada (acciones del S&P 500)
Universo: miembros del S&P 500 cada día (point-in-time con deslistadas; `sp500data`, `snapshot-2026-11`), con precio ≥ 5 $ y mediana de 60 sesiones de volumen en dólares ≥ 5 M$.
**50 variables** calculadas solo con datos hasta el cierre de la sesión *t* (lista cerrada, no se amplía):
- Rentabilidad pasada: 1, 2, 3, 5, 10, 21, 63, 126 y 252 sesiones; 126−21 y 252−21 (omitiendo el último mes). (11)
- Volatilidad y riesgo: volatilidad realizada de 10, 21 y 63 sesiones; rango medio verdadero relativo (ATR14/cierre); volatilidad a la baja de 63; asimetría de 63; máxima y mínima rentabilidad diaria de 21 sesiones; beta de 126 sesiones frente al índice de la muestra; volatilidad idiosincrática de 63. (10)
- Niveles de precio: distancia al máximo y al mínimo de 252 sesiones; al máximo de 20 y de 50; cierre/SMA10, /SMA20, /SMA50, /SMA200; SMA50/SMA200; logaritmo del precio. (11)
- Volumen y liquidez: volumen del día / media de 50; volumen medio de 5 / media de 50; logaritmo del volumen en dólares; ilicuidez de Amihud (63); pendiente del OBV de 21. (5)
- Velas y patrones: hueco de apertura (apertura/cierre previo); rentabilidad intradía (cierre/apertura); posición del cierre en el rango (media de 1 y de 5 sesiones); rango de 7 sesiones mínimo (NR7); día interior; número de sesiones consecutivas al alza/baja. (8)
- Compuestas: reversión de 5 sesiones × volatilidad de 21; momentum 126−21 × (1 − volatilidad de 63 en percentil). (2)
- Total: 11 + 10 + 11 + 5 + 8 + 2 = **47** (se registran 47 y no 50; el número exacto de pruebas lo fija esta lista).
**Horizontes de rentabilidad futura:** 1, 5 y 21 sesiones, medidas de la apertura de *t+1* a la apertura de *t+1+h* (con cierre al último precio disponible si el valor deja de cotizar). Familia A = **47 × 3 = 141 pruebas por periodo**.

## 2. Familia B: calendario sobre el índice (S&P 500, `^GSPC` con dividendo aproximado del 2 %/año no incluido en los retornos de contraste)
- Día de la semana (5), mes del año (12), último día hábil del mes y primeros 3 del mes siguiente (1 contraste), víspera de festivo (1), "Halloween" (noviembre-abril frente a mayo-octubre) (1). **20 pruebas.**
- Cada contraste compara la rentabilidad diaria media dentro del grupo con la del resto.
- Periodos: **C1 1950-1979, C2 1980-1999, C3 2000-2020**.

## 3. Periodos (familia A) y bloqueo
**A 2010-01-01 a 2020-12-31** y **B 1997-01-01 a 2009-12-31** (calentamiento desde 1996). **Prueba final 2021-2026 bloqueada** (no se carga). Familia B: datos hasta 2020-12-31.

## 4. Estadísticos y reglas de decisión (fijados antes)
- **Familia A:** por fecha, correlación de rangos (IC de Spearman) entre la variable y la rentabilidad futura; se muestrea **cada h sesiones** (sin solapamiento) y se contrasta la media del IC con un estadístico *t* de una muestra (p bilateral por aproximación normal).
  Corrección **Benjamini-Hochberg al 5 %** dentro de cada periodo sobre las 141 pruebas.
- **Una variable-horizonte es "anomalía candidata" si:** (1) es significativa tras BH en el periodo A; (2) en el periodo B tiene el **mismo signo** y p < 0,05 sin corregir (replicación independiente); (3) |IC medio| ≥ 0,01 en ambos periodos; y
  (4) el diferencial neto decil superior − decil inferior (orientado por el signo del IC; rebalanceo completo cada h sesiones, coste 0,10 % por lado y por pata = 0,40 % por rebalanceo) es **> 0 en ambos periodos**.
- **Familia B:** *t* de dos muestras por grupo; BH al 5 % sobre las 20 pruebas en C1; candidata si además mantiene el signo con p < 0,05 en C2 y en C3.
- Se informa también el número esperado de falsos positivos (5 % de las pruebas) y el de significativas sin corregir, para dimensionar el efecto del azar.

## 5. Qué ocurre con las candidatas
No son estrategias ni se operan. Cada una requeriría una hipótesis nueva con reglas de cartera y criterios registrados, probada con la prueba final 2021-2026 abierta una única vez y con confirmación explícita del usuario.
Si no hay candidatas, la conclusión es "no se encontraron anomalías explotables neto de costes en este universo y periodos".

## 6. Qué NO se hará
Añadir variables o horizontes después de ver resultados, cambiar umbrales (BH 5 %, |IC| ≥ 0,01, p < 0,05), elegir periodos a posteriori, presentar una variable no replicada o no neta de costes como anomalía, mirar 2021-2026.
