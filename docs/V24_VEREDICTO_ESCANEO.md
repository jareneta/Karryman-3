# Resultado del escaneo de anomalías (criterios de `docs/V24_ESCANEO_ANOMALIAS.md`, sin modificarlos)

Ficheros: `results/v24/v24_scan_43871590046.json` y `results/v24/v24_calendar_43871590046.json` · commit `bfb66c7` · S&P 500 point-in-time con deslistadas (~500 miembros con precio por día) · datos hasta 2020-12-31 (2021-2026 **no usado**).

## Familia A: 45 variables × 3 horizontes = 135 pruebas por periodo (sección cruzada)
| | Resultado |
|---|---|
| Significativas en 2010-2020 sin corregir (p < 0,05) | **22** (se esperaban ~6,8 solo por azar) |
| Significativas tras Benjamini-Hochberg al 5 % | **0** |
| Que además replican en 1997-2009 | 0 |
| **Anomalías candidatas finales** | **0** |

- **Las 22 significativas sin corregir están todas en el horizonte de 1 sesión** (0 en 5 y en 21 sesiones). Las más fuertes: momentum de 12 meses omitiendo el último mes (r252m21: IC +0,014, t = 3,5, p = 0,0004, justo por encima del umbral corregido de ~0,0004),
  momentum de 6 meses omitiendo el último mes × baja volatilidad, momentum de 12 meses, volatilidad idiosincrática (signo negativo) y SMA50/SMA200. En 1997-2009 los mismos signos se repiten con p < 0,01.
- **Económicamente irrelevantes:** el diferencial bruto decil superior − inferior es de ~+0,01 % a +0,02 % por sesión y un rebalanceo completo cuesta ~0,40 % (0,10 % por lado y pata). El neto es negativo (≈ −0,4 % por rebalanceo) para todas ellas.
- **Persistencia de signo:** 95 de las 135 pruebas tienen el mismo signo en ambos periodos (70 %, por encima del 50 % esperado por azar) y 58 son significativas sin corregir en 1997-2009, más que en 2010-2020: la capacidad de predicción de estas variables es mayor en el periodo antiguo.
- **Neto positivo en ambos periodos:** solo 6 de 135, ninguna significativa. Mejor neto en 2010-2020: +0,35 % por rebalanceo mensual (logaritmo del precio a 21 sesiones), sin significación tras corregir.
- Limitación: para variables binarias (`nr7`, `inside`) el diferencial por deciles no está definido (empates), por lo que no pueden superar el criterio de efecto neto; su contraste de IC sí se informa.

## Familia B: 20 contrastes de calendario sobre el índice
| | Resultado |
|---|---|
| Significativos en 1950-1979 tras BH al 5 % | **6** (lunes −0,20 %/día, miércoles +0,08 %, viernes +0,11 %, cambio de mes +0,14 %, víspera de festivo +0,27 %, noviembre-abril +0,05 %) |
| Que replican con el mismo signo y p < 0,05 en 1980-1999 **y** 2000-2020 | **0** |
| **Candidatas finales** | **0** |

Los efectos de calendario clásicos existen en la muestra más antigua pero **se debilitan y desaparecen en las posteriores** (por ejemplo, el cambio de mes pasa de +0,14 % a +0,10 % (p = 0,005) a +0,04 % (p = 0,33); la víspera de festivo, de +0,27 % a +0,08 % y +0,05 %, no significativos).

## Veredicto registrado
**No se encontraron anomalías explotables neto de costes en este universo y periodos.** Ninguna variable ni patrón de calendario supera los criterios (control de falsos descubrimientos, replicación independiente, efecto mínimo y diferencial neto positivo). No se registran hipótesis derivadas y la prueba final 2021-2026 no se abre.

## Lectura
- Con 135 + 20 pruebas, el azar produce varias "anomalías" sin corregir; el control de falsos descubrimientos las elimina.
- Lo que sí se detecta estadísticamente (momentum a 1 día, baja volatilidad idiosincrática) tiene un tamaño de efecto demasiado pequeño para sobrevivir a unos costes realistas. Coincide con las conclusiones de las hipótesis H1-H14: hay información en los precios, pero no es explotable con costes personales.
- Los efectos de calendario se han arbitrado con el tiempo.

## Limitaciones
Solo S&P 500 de gran capitalización y liquidez (donde las anomalías suelen ser más débiles que en valores pequeños); 45 variables y 3 horizontes fijos; costes hipotéticos y rebalanceo completo (una versión con menos rotación podría tener menor coste); sin fundamentales; datos de un tercero sin licencia clara.
